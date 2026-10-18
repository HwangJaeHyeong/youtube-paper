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


def build_subtitles(tokens, out):
    groups, current = [], []
    for token in tokens:
        candidate = " ".join(t["text"] for t in current+[token])
        if current and (len(candidate) > 12 or token["line"] != current[0]["line"]):
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
        text = " ".join(t["text"] for t in group)
        effect = r"{\pos(540,1380)\fad(20,0)\fscx95\fscy95\t(0,60,\fscx100\fscy100)}"
        events.append(f"Dialogue: 0,{stamp(start)},{stamp(max(start+0.04,end))},Speech,,0,0,0,,{effect}{text}")
    out.write_text(header+"\n".join(events)+"\n", encoding="utf-8")
    return len(groups)
