"""Align transcript words and build captions from actual speech timestamps."""
from __future__ import annotations

import difflib
import re

import numpy as np


def normalized(text):
    text = text.replace("열여덟", "18").replace("이천이십육", "2026")
    return re.sub(r"[^가-힣a-zA-Z0-9]", "", text).lower()


def words_from_response(value):
    if isinstance(value, dict):
        if value.get("type") == "word_info":
            yield {
                "text": value["text"],
                "start": float(value["start_offset"].rstrip("s")),
                "end": float(value["end_offset"].rstrip("s")),
            }
        for child in value.values():
            yield from words_from_response(child)
    elif isinstance(value, list):
        for child in value:
            yield from words_from_response(child)


def align_words(data, recognized):
    actual, char_starts, char_ends = "", [], []
    for word in recognized:
        clean = normalized(word["text"])
        for j in range(len(clean)):
            char_starts.append(word["start"] + (word["end"]-word["start"])*j/len(clean))
            char_ends.append(word["start"] + (word["end"]-word["start"])*(j+1)/len(clean))
        actual += clean
    expected, tokens = "", []
    for line_index, line in enumerate(data["script"]):
        for word in line["text"].split():
            clean = normalized(word)
            tokens.append({"text": word, "line": line_index, "char_start": len(expected), "char_end": len(expected)+len(clean)})
            expected += clean
    matcher = difflib.SequenceMatcher(None, expected, actual, autojunk=False)
    if matcher.ratio() < 0.92:
        raise RuntimeError(f"Narration differs from the script: similarity={matcher.ratio():.3f}")
    starts = np.full(len(expected), np.nan)
    ends = np.full(len(expected), np.nan)
    for op, a0, a1, b0, b1 in matcher.get_opcodes():
        if op == "equal":
            starts[a0:a1] = char_starts[b0:b1]
            ends[a0:a1] = char_ends[b0:b1]
        elif op == "replace" and a1 > a0 and b1 > b0:
            starts[a0:a1] = np.linspace(char_starts[b0], char_ends[b1-1], a1-a0, endpoint=False)
            ends[a0:a1] = np.linspace(char_starts[b0], char_ends[b1-1], a1-a0+1)[1:]
    for array in (starts, ends):
        known = np.flatnonzero(~np.isnan(array))
        array[:] = np.interp(np.arange(len(array)), known, array[known])
    for token in tokens:
        token["start"] = round(float(starts[token["char_start"]]), 3)
        token["end"] = round(float(ends[token["char_end"]-1]), 3)
    return tokens, matcher.ratio()


def stamp(sec):
    centisec = round(sec*100)
    return f"{centisec//360000}:{centisec//6000%60:02d}:{centisec//100%60:02d}.{centisec%100:02d}"


# A Korean phrase usually ends on a particle or a connective ending; breaking a caption right after
# one reads naturally ("싱크대에 / 그릇이 산더미"), breaking elsewhere splits a phrase ("집안일 / 로봇의").
_BREAK = re.compile(r"(은|는|이|가|을|를|에|에서|의|도|만|와|과|랑|로|으로|고|서|며|면|데|게|지|니|요|임|함|음|봄|짐|[?!])$")


# Words that lean on the word before them ("나가는 게", "할 수", "쉽게 말해"): never start a line with one.
_GLUE = {"게", "거", "것", "수", "줄", "때", "뿐", "데", "만큼", "듯", "말해", "말하면"}


def _break_penalty(word, next_word=""):
    if next_word in _GLUE:
        return 40
    return 0 if _BREAK.search(word) else 8


def two_lines(words):
    """Split words into two lines: balanced, preferring a break after a particle/ending (step captions)."""
    if len(words) < 2:
        return " ".join(words)
    def cost(i):
        top, bottom = len(" ".join(words[:i])), len(" ".join(words[i:]))
        return abs(top - bottom) + _break_penalty(words[i - 1], words[i]) + (12 if min(top, bottom) < 4 else 0)

    cut = min(range(1, len(words)), key=cost)
    return " ".join(words[:cut]) + r"\N" + " ".join(words[cut:])


def phrase_groups(words, limit):
    """Split one script line's words into caption chunks of at most `limit` characters: even-sized
    chunks that end on a particle/ending where possible (DP over cut points)."""
    n = len(words)
    size = lambda j, i: len(" ".join(words[j:i]))  # noqa: E731
    total = size(0, n)
    target = total / max(1, -(-total // limit))  # even chunk length for the fewest chunks
    best = [0.0] + [float("inf")] * n
    prev = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(i):
            if size(j, i) > limit and i - j > 1:
                continue
            c = best[j] + (size(j, i) - target) ** 2 / 4 + (0 if i == n else _break_penalty(words[i - 1], words[i]))
            if c < best[i]:
                best[i], prev[i] = c, j
    cuts, i = [], n
    while i:
        cuts.append((prev[i], i))
        i = prev[i]
    return [words[a:b] for a, b in reversed(cuts)]


def build_subtitles(tokens, out, step=False, line_chars=10):
    """step=True: 2-line phrases that cut in and stay, no fade/scale (shortform template)."""
    limit = line_chars*2+1 if step else 12
    if step:  # chunk each script line by phrase, not by character count
        groups = []
        for line in sorted({t["line"] for t in tokens}):
            toks = [t for t in tokens if t["line"] == line]
            k = 0
            for chunk in phrase_groups([t["text"] for t in toks], limit):
                groups.append(toks[k:k + len(chunk)])
                k += len(chunk)
        tokens = []  # skip the character-count grouping below
    else:
        groups = []
    current = []
    for token in tokens:
        candidate = " ".join(t["text"] for t in current+[token])
        if current and (len(candidate) > limit or token["line"] != current[0]["line"]):
            groups.append(current)
            current = []
        current.append(token)
        if token["text"].endswith((".", "?", "!", ",")):
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Speech,Pretendard Black,78,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,5,0,5,62,62,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for i, group in enumerate(groups):
        start = max(0, group[0]["start"]-0.04)
        speech_end = group[-1]["end"]
        next_start = groups[i+1][0]["start"]-0.04 if i+1 < len(groups) else speech_end+0.12
        end = min(next_start, speech_end+0.25) if next_start-speech_end > 0.6 else next_start
        if step:
            end = next_start if i+1 < len(groups) else speech_end+0.25  # stay until the next phrase
            text = two_lines([t["text"] for t in group])
            effect = r"{\pos(540,1380)}"
        else:
            text = " ".join(t["text"] for t in group)
            effect = r"{\pos(540,1380)\fad(20,0)\fscx95\fscy95\t(0,60,\fscx100\fscy100)}"
        events.append(f"Dialogue: 0,{stamp(start)},{stamp(max(start+0.04,end))},Speech,,0,0,0,,{effect}{text}")
    out.write_text(header+"\n".join(events)+"\n", encoding="utf-8")
    return len(groups)
