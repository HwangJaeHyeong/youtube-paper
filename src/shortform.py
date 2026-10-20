"""숏폼템플릿 (templates/shortform): input/<폴더>/ 의 PDF + 데모 영상 -> 1인 쇼츠 mp4.

Prompts, voice, background, font and caption layout all live in templates/shortform/.
The demo clip plays in the figure box from the start until the paper is introduced
(first "method" line); paper figures follow. Captions are 2-line step phrases.
"""
from __future__ import annotations

import io
import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from pydub import AudioSegment

from src.config import AUDIO_DIR, PAPERS_DIR, PROJECT_ROOT, SCRIPTS_DIR, VIDEOS_DIR, VOICE_CONFIG
from src.ingest import pdf_parser
from src.script import shorts_generator
from src.video import composer, figure_cropper, figure_indexer, word_timing

log = logging.getLogger("papercast")

TEMPLATE = PROJECT_ROOT / "templates" / "shortform"
SPEAKER = "나레이터"
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
W, H = 1080, 1920


def pick_inputs(folder: Path) -> tuple[Path, Path | None]:
    """The one PDF and the (optional) one demo video in the folder, whatever they are named."""
    files = [f for f in folder.iterdir() if f.is_file()]
    pdfs = [f for f in files if f.suffix.lower() == ".pdf"]
    videos = [f for f in files if f.suffix.lower() in VIDEO_EXTS]
    if len(pdfs) != 1 or len(videos) > 1:
        raise RuntimeError(f"{folder.name}: PDF 1개 + 영상 0~1개여야 함 (PDF {len(pdfs)}, 영상 {len(videos)})")
    return pdfs[0], (videos[0] if videos else None)


def strip_punct(text: str) -> str:
    """Drop . and , except inside numbers (83.4%, 1,000)."""
    return re.sub(r"(?<!\d)[.,]|[.,](?!\d)", "", text).strip()


def _prompt(name: str) -> str:
    return re.sub(r"<!--.*?-->", "", (TEMPLATE / name).read_text(encoding="utf-8"), flags=re.S).strip()


def _register_voice() -> dict:
    voice = json.loads((TEMPLATE / "voice.json").read_text(encoding="utf-8"))
    VOICE_CONFIG[SPEAKER] = {
        "provider": voice.get("provider", "qwen"),
        "qwen_ref_audio": TEMPLATE / voice["ref_audio"],
        "qwen_ref_text": voice["ref_text"],
        "qwen_language": voice.get("language", "Korean"),
        "subtitle_color": "&H00000000",
    }
    return voice


def line_tokens(lines: list[dict], starts: list[float], ends: list[float]) -> list[dict]:
    """Word timings spread over each line's speech by character count.

    ponytail: proportional estimate, not forced alignment. Fine for 2-line step captions;
    plug in an ASR aligner (word_timing.align_words) if words drift noticeably.
    """
    tokens = []
    for i, (line, t0, t1) in enumerate(zip(lines, starts, ends)):
        words = line["text"].split()
        weights = [max(1, len(word_timing.normalized(w))) for w in words]
        total, acc = sum(weights), 0
        for w, k in zip(words, weights):
            a = t0 + (t1 - t0) * acc / total
            acc += k
            tokens.append({"text": w, "line": i, "start": round(a, 3), "end": round(t0 + (t1 - t0) * acc / total, 3)})
    return tokens


def _ref(value) -> str | None:
    v = str(value or "").strip().upper()
    if re.fullmatch(r"DEMO(#\d+)?|ILLUST(:\S+)?|OUTRO", v):
        return v
    return figure_cropper.normalize_ref(v or None)


def _visual(item: dict) -> str | None:
    """A line's or cut's screen. DEMO with an assigned clip becomes "DEMO#<clip id>"."""
    ref = _ref(item.get("visual_ref"))
    if ref == "DEMO" and item.get("demo_clip") is not None:
        return f"DEMO#{int(item['demo_clip'])}"
    if ref == "ILLUST" and item.get("illust_url"):
        return "ILLUST:" + item["illust_url"].rsplit("/", 1)[-1].upper()
    return ref


def _cuts_allowed(i: int, line: dict) -> bool:
    # the hook and "원래는 이랬음" (ILLUST) lines hold one screen (the model sometimes adds cuts anyway)
    return i != 0 and _ref(line.get("visual_ref")) != "ILLUST"


def shot_list(lines: list[dict], tokens: list[dict], starts: list[float]) -> list[tuple[float, str | None]]:
    """(time, visual) for every screen change: each line's visual_ref at its start, plus the line's
    mid-line cuts [{"at": word, "visual_ref": ...}] at the moment that word is spoken."""
    shots = []
    for i, line in enumerate(lines):
        shots.append((starts[i], _visual(line)))
        if not _cuts_allowed(i, line):
            continue
        words = [w for w in tokens if w["line"] == i][1:]  # a cut on the first word = line start
        for cut in line.get("cuts") or []:
            key = word_timing.normalized(str(cut.get("at", "")))
            hit = next((w for w in words if key and word_timing.normalized(w["text"]).startswith(key)), None)
            if hit:
                shots.append((hit["start"], _visual(cut)))
            else:
                log.warning("cut word not in line %d: %r", i, cut.get("at"))
    return sorted(shots, key=lambda s: s[0])


SFX_KINDS = ("positive", "negative", "weird", "surprise", "transition")
SFX_GAP = 1.5  # seconds between two sound effects
SFX_SNAP = 1.0  # a sound this close to a screen change moves onto it; farther ones are dropped
MAX_SECONDS = 59.5  # hard cap incl. the ending line: longer narration is sped up (pitch kept)


def sfx_events(lines: list[dict], tokens: list[dict], starts: list[float]) -> list[tuple[float, str]]:
    """(time, kind) for every sound effect: a line's "sfx" at its start, a cut's "sfx" when its word
    is spoken. kind is one of SFX_KINDS; anything else is ignored. An illustration whose mood
    ("illust_mood") differs from the previous illustration's also gets that mood's sound.
    Rule: no sound effect at the start of the video (first line, or within the first second)."""
    events, moods, last_mood = [], [], None
    for i, line in enumerate(lines):
        words = [w for w in tokens if w["line"] == i][1:]
        items = [(starts[i], line)]
        for cut in (line.get("cuts") or []) if _cuts_allowed(i, line) else []:
            key = word_timing.normalized(str(cut.get("at", "")))
            hit = next((w for w in words if key and word_timing.normalized(w["text"]).startswith(key)), None)
            if hit:
                items.append((hit["start"], cut))
        for t, item in items:
            if i and item.get("sfx") in SFX_KINDS:
                events.append((t, item["sfx"]))
            mood = item.get("illust_mood") if _ref(item.get("visual_ref")) == "ILLUST" else None
            if mood and mood != last_mood:
                moods.append((t, mood))
            last_mood = mood or last_mood
    # Rule: sounds only where the screen changes. A sound within SNAP of a change moves onto it, others go.
    changes, prev = [], None
    for t, v in shot_list(lines, tokens, starts):
        if v and v != prev:
            changes.append(t)
        prev = v or prev
    # Script sounds first, mood sounds fill in; any two sounds stay at least SFX_GAP apart.
    kept: list[tuple[float, str]] = []
    for t, kind in sorted(events) + sorted(moods):
        near = min(changes, key=lambda c: abs(c - t), default=None)
        if near is None or abs(near - t) > SFX_SNAP:
            continue
        if near >= 1.0 and all(abs(near - k[0]) >= SFX_GAP for k in kept):
            kept.append((near, kind))
    return sorted(kept)


def replace_missing_figures(lines: list[dict], available: set[str], has_demo: bool) -> None:
    """A Figure/Table the writer named that can't be shown (not in the paper, or no clean crop) becomes
    a demo moment (the matcher gives it an unused clip) or, without a demo, an illustration."""
    for i, line in enumerate(lines):
        for item in [line] + ((line.get("cuts") or []) if _cuts_allowed(i, line) else []):
            ref = _ref(item.get("visual_ref"))
            if ref and ref.startswith(("Figure", "Table")) and ref not in available:
                new = "DEMO" if has_demo else "ILLUST"
                log.info("L%d %s: 화면에 못 나옴 -> %s", i, ref, new)
                for k in _SCREEN_KEYS:
                    item.pop(k, None)
                item["visual_ref"] = new


def spoken_numbers(lines: list[dict]) -> bool:
    """Captions keep digits ("17개"), the voice reads them the Korean way ("열일곱 개" / "십칠 퍼센트"):
    lines with digits get a "tts" text (templates/shortform/tts_numbers.md). True if any line changed."""
    todo = {f"L{i}": l for i, l in enumerate(lines) if re.search(r"\d", l["text"]) and "tts" not in l}
    if not todo:
        return False
    try:
        out = _ask_json("tts_numbers.md", "\n".join(f"{k}: {l['text']}" for k, l in todo.items()), "tts")["tts"]
    except Exception as e:
        log.warning("숫자 읽기 변환 실패, 숫자 그대로 읽음: %s", e)
        return False
    for k, line in todo.items():
        spoken = strip_punct(str(out.get(k) or "")).strip()
        if spoken and not re.search(r"\d", spoken):
            line["tts"] = spoken
            log.info("숫자 읽기 %s: %s -> %s", k, line["text"], spoken)
    return True


def add_description_line(data: dict) -> bool:
    """The YouTube description's first line: one finished sentence answering the title, in 음슴체
    (templates/shortform/description.md). True if added."""
    if data.get("description_line"):
        return False
    script = "\n".join(l["text"] for l in data["script"] if l.get("visual_ref") != "OUTRO")
    title = re.sub(r"\*\*", "", (data.get("title_hook") or "").split("\n")[0])
    try:
        line = _ask_json("description.md", f"[영상 제목]\n{title}\n\n[대본]\n{script}", "line")["line"]
    except Exception as e:
        log.warning("설명란 문장 생성 실패, 예전 형식(한줄평)으로: %s", e)
        return False
    data["description_line"] = " ".join(str(line).split()).rstrip(".")
    log.info("설명란 문장: %s", data["description_line"])
    return True


def vary_screens(lines: list[dict], hold: int = 3) -> None:
    """Rules: no screen (Figure/Table crop, demo clip, picture) is shown twice, and one screen stays
    for at most `hold` script lines. A repeat, or the line after the hold runs out, becomes an
    ILLUST moment instead (the picker finds a picture for it)."""
    def key(item: dict) -> str | None:
        v = _visual(item)
        if v == "ILLUST" or v == "DEMO":  # no picture / clip chosen yet: a new screen every time
            return f"{v}#{item['illust']}" if item.get("illust") else f"{v}@{id(item)}"
        return v

    def to_illust(item: dict) -> None:
        for k in _SCREEN_KEYS:
            item.pop(k, None)
        item["visual_ref"] = "ILLUST"

    used: set[str] = set()
    current, run = None, 0
    for i, line in enumerate(lines):
        if _ref(line.get("visual_ref")) == "OUTRO":
            continue
        changed = False
        for item in [line] + ((line.get("cuts") or []) if _cuts_allowed(i, line) else []):
            k = key(item)
            if k is None or k == current:
                continue
            if k in used:
                log.info("화면 반복 L%d %s -> 일러스트로", i, k)
                to_illust(item)
                k = key(item)
            used.add(k)
            current, changed = k, True
        run = 1 if changed else run + 1
        if run > hold:
            log.info("화면이 %d줄째 그대로 L%d -> 일러스트로", run, i)
            to_illust(line)
            current, run = key(line), 1
            used.add(current)


_DB: dict[Path, float] = {}


def mean_db(path: Path) -> float:
    """Mean loudness (dBFS) of an audio file via ffmpeg volumedetect; cached per file."""
    if path not in _DB:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
        _DB[path] = float(m.group(1)) if m else -20.0
    return _DB[path]


def sfx_files(events: list[tuple[float, str]], sfx_dir: Path) -> list[tuple[float, Path]]:
    """Kind -> a file from sfx/<kind>/*.mp3, rotating through the folder so repeats sound different.
    Kinds without files are skipped."""
    pools = {k: sorted((sfx_dir / k).glob("*.mp3")) for k in SFX_KINDS}
    used = {k: 0 for k in SFX_KINDS}
    out = []
    for t, kind in events:
        if pools[kind]:
            out.append((t, pools[kind][used[kind] % len(pools[kind])]))
            used[kind] += 1
    return out


def moments(lines: list[dict], kind: str) -> list[tuple[str, dict, str]]:
    """Every moment showing `kind` ("DEMO" / "ILLUST") as (key, line-or-cut dict, narration over it).
    Keys: "L3" = line 3 starts on it, "L3@쉽게" = a cut to it at that word in line 3."""
    out = []
    for i, line in enumerate(lines):
        text, cuts = line["text"], (line.get("cuts") or []) if _cuts_allowed(i, line) else []
        marks = sorted((text.find(str(c.get("at", ""))), c) for c in cuts if str(c.get("at", "")) in text)
        bounds = [0] + [p for p, _ in marks] + [len(text)]
        if _ref(line.get("visual_ref")) == kind:
            out.append((f"L{i}", line, text[: bounds[1]].strip()))
        for k, (pos, cut) in enumerate(marks):
            if _ref(cut.get("visual_ref")) == kind:
                out.append((f"L{i}@{cut['at']}", cut, text[pos: bounds[k + 2]].strip()))
    return out


def demo_moments(lines: list[dict]) -> list[tuple[str, dict, str]]:
    return moments(lines, "DEMO")


MAX_LINE = 40  # characters; longer lines make the TTS slur or break


_EASY = re.compile(r"쉽게 (말|보|치|얘기|비유)|예를 들")  # analogy openers: "쉽게 말하면", "예를 들면" (+ older wordings)
_SCREEN_KEYS = ("visual_ref", "demo_clip", "illust", "illust_url", "mood", "illust_mood")


def promote_first_cuts(lines: list[dict]) -> None:
    """A cut on a line's first word is really the line's own screen: move it onto the line
    (cuts on the first word are otherwise indistinguishable from the line start and get dropped)."""
    for line in lines:
        first = (line["text"].split() or [""])[0]
        for cut in [c for c in line.get("cuts") or [] if c.get("at") == first]:
            for key in _SCREEN_KEYS:
                line.pop(key, None)
                if key in cut:
                    line[key] = cut[key]
            if cut.get("sfx") and not line.get("sfx"):
                line["sfx"] = cut["sfx"]
            line["cuts"] = [c for c in line["cuts"] if c is not cut]


def easy_illust(lines: list[dict]) -> None:
    """Rule: the analogy after "쉽게 말하면" / "예를 들면" is shown as an いらすとや illustration."""
    for i, line in enumerate(lines):
        m = _EASY.search(line["text"])
        if i == 0 or not m:
            continue
        pos = m.start()
        opener = m.group(0).split()[0]  # the word the picture starts on: "쉽게" / "예를"
        if pos == 0:
            if any(str(c.get("at", "")) == opener for c in line.get("cuts") or []):  # keep the writer's picture
                promote_first_cuts([line])
            line["visual_ref"] = "ILLUST"
            continue
        cut = next((c for c in line.get("cuts") or [] if str(c.get("at", "")) == opener), None)
        if cut is None:
            cut = {"at": opener}
            line["cuts"] = (line.get("cuts") or []) + [cut]
        cut["visual_ref"] = "ILLUST"


TARGET_CHARS = (550, 600)  # ~10.5 chars/s spoken + the ~2.5s ending line = 56~59s (measured)


def script_issues(lines: list[dict]) -> list[str]:
    """Problems the TTS / renderer can't handle, phrased as fix instructions for the model."""
    issues = []
    total = sum(len(l["text"]) for l in lines)
    lo, hi = TARGET_CHARS
    if total < lo:
        issues.append(f"전체 {total}자로 영상이 {total // 10}초뿐임. 56~59초가 되게 {lo - total}자 이상 늘릴 것 "
                      f"(방법·결과를 구체적으로, 줄을 추가해서. 한 줄은 {MAX_LINE}자 이하 유지)")
    elif total > hi + 15:
        issues.append(f"전체 {total}자로 60초를 넘김. {total - hi}자 이상 줄일 것")
    for i, line in enumerate(lines):
        text = line["text"]
        if len(text) > MAX_LINE:
            issues.append(f"L{i}: {len(text)}자라 음성이 깨짐. {MAX_LINE}자 이하로 줄이거나 두 줄로 나눌 것: {text}")
        if not _ref(line.get("visual_ref")) and line.get("visual_ref"):
            issues.append(f"L{i}: visual_ref {line['visual_ref']!r} 는 DEMO / ILLUST / Figure N / Table N 이 아님")
        for c in line.get("cuts") or []:
            if str(c.get("at", "")) not in text.split():
                issues.append(f"L{i}: cuts 의 at {c.get('at')!r} 가 text 에 띄어쓰기 단위로 없음")
    # Rule: no line says again what another already said (e.g. the hook repeated as the next line).
    from difflib import SequenceMatcher

    for i, a in enumerate(lines):
        for j in range(i + 1, len(lines)):
            b = lines[j]
            if SequenceMatcher(None, a["text"].replace(" ", ""), b["text"].replace(" ", "")).ratio() >= 0.55:
                issues.append(f"L{i}·L{j}: 거의 같은 문장 ({a['text']} / {b['text']}). 같은 말 반복이면 한 줄을 새 내용으로 바꿀 것 "
                              "(일부러 대비시킨 두 줄이면 그대로)")
    return issues


def split_long(lines: list[dict], max_len: int = MAX_LINE) -> list[dict]:
    """Last resort for lines the model left too long: split at a word boundary near the middle,
    preferring after a connective ending (~는데, ~더니, ~고 …). Cuts follow their words; the second
    half starts on the screen that was showing at the split point."""
    out = []
    for line in lines:
        words = line["text"].split()
        if len(line["text"]) <= max_len or len(words) < 2:
            out.append(line)
            continue
        mid = len(line["text"]) / 2

        def cost(k):
            left = " ".join(words[:k])
            joint = 0 if re.search(r"(는데|더니|니까|면서|고|서|며|면|지만)$", words[k - 1]) else 8
            return abs(len(left) - mid) + joint

        k = min(range(1, len(words)), key=cost)
        a_text, b_text = " ".join(words[:k]), " ".join(words[k:])
        cuts_a = [c for c in line.get("cuts") or [] if c.get("at") in words[:k]]
        cuts_b = [c for c in line.get("cuts") or [] if c.get("at") in words[k:]]
        screen = cuts_a[-1] if cuts_a else line
        a = {**line, "text": a_text, "cuts": cuts_a, "pause_after_ms": 0}
        carried = ("demo_clip", "illust_url", "illust", "mood", "illust_mood")
        b = {**{k2: v for k2, v in line.items() if k2 not in ("sfx",) + carried},
             "text": b_text, "cuts": cuts_b, "visual_ref": screen.get("visual_ref")}
        for key in carried:
            if key in screen:
                b[key] = screen[key]
        out += split_long([a, b], max_len)
    return out


def _validate(data: dict) -> None:
    """Code checks the finished script; the model fixes what it can (2 rounds), code splits the rest."""
    import asyncio

    for _ in range(2):
        issues = script_issues(data["script"])
        if not issues:
            return
        log.info("대본 검증: %d개 문제, 수정 요청 %s", len(issues), issues[:3])
        critique = json.dumps({"critical_issues": issues, "specific_fixes": issues}, ensure_ascii=False)
        try:
            fixed = shorts_generator._parse_first_json(
                asyncio.run(shorts_generator._refine_query(json.dumps(data, ensure_ascii=False), critique,
                                                        system=_prompt("refine.md"))))
            if isinstance(fixed.get("script"), list) and fixed["script"]:
                data["script"] = fixed["script"]
                for line in data["script"]:
                    line["speaker"] = SPEAKER
                    line["text"] = strip_punct(line["text"])
        except Exception as e:
            log.warning("대본 수정 실패: %s", e)
            break
    data["script"] = split_long(data["script"])
    for line in data["script"]:  # cuts whose word vanished would never fire
        line["cuts"] = [c for c in line.get("cuts") or [] if str(c.get("at", "")) in line["text"].split()]
    left = script_issues(data["script"])
    if left:
        log.warning("대본 검증 후에도 남은 문제: %s", left)


REVIEW_PASS = 90  # script and illustration reviews: below this the model fixes / re-picks


def _review_script(data: dict, paper, rounds: int = 2) -> None:
    """The stronger model checks the script against the paper (templates/shortform/review.md: accuracy,
    flow, easiness, readability out of 100) and returns a fixed script when it scores below REVIEW_PASS."""
    for r in range(1, rounds + 1):
        prompt = (f"논문 제목: {paper.title}\n\n[논문 본문 (발췌)]\n{paper.text[:30000]}\n\n"
                  f"[완성 대본]\n{json.dumps(data['script'], ensure_ascii=False)}")
        try:
            out = _ask_json("review.md", prompt, "score", polish=True)
        except Exception as e:
            log.warning("대본 검토 실패, 그대로 진행: %s", e)
            return
        score = int(out.get("score") or 0)
        log.info("대본 검토 %d회차: %d점 %s", r, score, (out.get("problems") or [])[:5])
        if score >= REVIEW_PASS or not isinstance(out.get("script"), list) or not out["script"]:
            return
        data["script"] = out["script"]
        for line in data["script"]:
            line["speaker"] = SPEAKER
            line["text"] = strip_punct(line["text"])


def _ask_json(template: str, prompt: str, key: str, images: list[Path] | None = None, tries: int = 3,
              polish: bool = False) -> dict:
    """Model call with templates/shortform/<template>; retried when the reply isn't JSON with `key`
    (e.g. an unescaped quote inside a description)."""
    import asyncio

    from src.llm import generate_text

    for attempt in range(1, tries + 1):
        try:
            raw = asyncio.run(generate_text(_prompt(template), prompt, images=images, polish=polish))
            # Sheets label clips "#12", so the model sometimes writes "id": #12 (invalid JSON): drop the "#".
            raw = re.sub(r'(:\s*)#(\d+)', r"\1\2", raw)
            out = shorts_generator._parse_first_json(raw)
            if key in out:
                return out
            raise ValueError(f"no {key!r} in reply")
        except Exception as e:
            if attempt == tries:
                raise
            log.warning("%s 응답 오류, 다시 요청 (%d/%d): %s", template, attempt, tries, e)
    raise AssertionError("unreachable")


def segment_bounds(cuts: list[float], duration: float, min_len: float = 1.5, max_len: float = 6.0,
                   max_n: int = 36) -> list[tuple[float, float]]:
    """Scene-cut times -> clip spans: short ones merged into the previous, long ones split, at most max_n."""
    spans: list[list[float]] = []
    for a, b in zip([0.0] + cuts, cuts + [duration]):
        if b - a <= 0:
            continue
        if spans and b - a < min_len:
            spans[-1][1] = b
        else:
            spans.append([a, b])
    out: list[list[float]] = []
    for a, b in spans:
        n = max(1, round((b - a) / max_len + 0.49))
        out += [[a + (b - a) * k / n, a + (b - a) * (k + 1) / n] for k in range(n)]
    while len(out) > max_n:  # ponytail: merge the shortest pair; fine for demos of a few minutes
        k = min(range(len(out) - 1), key=lambda j: out[j + 1][1] - out[j][0])
        out[k:k + 2] = [[out[k][0], out[k + 1][1]]]
    return [(round(a, 2), round(b, 2)) for a, b in out]


def demo_catalog(demo: Path, work: Path) -> list[dict]:
    """What the demo shows and when: [{"id", "start", "end", "desc"}], cached in work/demo/catalog.json.

    Scene cuts split the clip; one middle frame per span goes on numbered contact sheets that the
    model looks at (templates/shortform/demo.md). [] if the model call fails (demo then runs on the
    video clock, as before)."""
    import asyncio

    from src.llm import generate_text

    out_dir = work / "demo"
    cached = out_dir / "catalog.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(demo)],
                           capture_output=True, text=True, check=True)
    duration = float(probe.stdout.strip())
    scan = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(demo), "-vf", "select='gt(scene,0.3)',showinfo",
                           "-an", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    cuts = sorted(float(t) for t in re.findall(r"pts_time:([\d.]+)", scan.stderr))
    spans = segment_bounds(cuts, duration)
    font = _font({"font": json.loads((TEMPLATE / "design.json").read_text(encoding="utf-8"))["font"]}, 30)
    tiles = []
    for i, (a, b) in enumerate(spans, 1):
        png = out_dir / f"clip_{i:02}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(a + b) / 2:.2f}", "-i", str(demo), "-frames:v", "1",
                        "-vf", "scale=480:-2", str(png)], check=True)
        tile = Image.new("RGB", (400, 270), (255, 255, 255))
        tile.paste(ImageOps.contain(Image.open(png).convert("RGB"), (400, 225)), (0, 45))
        ImageDraw.Draw(tile).text((10, 8), f"#{i}  {int(a) // 60}:{int(a) % 60:02}-{int(b) // 60}:{int(b) % 60:02}", font=font, fill=(200, 0, 0))
        tiles.append(tile)
    sheets = []
    for k in range(0, len(tiles), 12):  # 3x4 tiles per sheet; JPEG keeps each read under the SDK's 1MB message cap
        sheet = Image.new("RGB", (400 * 3, 270 * 4), (255, 255, 255))
        for j, tile in enumerate(tiles[k:k + 12]):
            sheet.paste(tile, (400 * (j % 3), 270 * (j // 3)))
        sheets.append(out_dir / f"sheet_{k // 12 + 1}.jpg")
        sheet.save(sheets[-1], quality=80)
    listing = "\n".join(f"#{i} {a:.1f}s-{b:.1f}s" for i, (a, b) in enumerate(spans, 1))
    log.info("데모 분석: %d개 구간, 장면표 %d장", len(spans), len(sheets))
    try:
        out = _ask_json("demo.md", f"[구간 목록]\n{listing}", "clips", images=sheets)
        descs = {int(c["id"]): c["desc"] for c in out["clips"]}
        wows = {int(c["id"]): int(c.get("wow", 3)) for c in out["clips"]}
    except Exception as e:
        log.warning("데모 분석 실패, 데모는 영상 시간대로 재생: %s", e)
        return []
    catalog = [{"id": i, "start": a, "end": b, "desc": descs.get(i, ""), "wow": wows.get(i, 3)}
               for i, (a, b) in enumerate(spans, 1)]
    cached.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    for c in catalog:
        log.info("데모 #%d %.1f-%.1fs: %s", c["id"], c["start"], c["end"], c["desc"])
    return catalog


def catalog_text(catalog: list[dict]) -> str:
    return "\n".join(f"#{c['id']} ({c['end'] - c['start']:.1f}초, 하이라이트 {c.get('wow', 3)}/5): {c['desc']}"
                     for c in catalog)


def highlight(catalog: list[dict]) -> dict:
    """The clip the short opens on: highest "wow", the longer one on ties (it holds the hook line)."""
    return max(catalog, key=lambda c: (c.get("wow", 3), c["end"] - c["start"]))


def plan_shots(shots: list[tuple[float, str | None]], duration: float, available: set[str],
               has_demo: bool, intro_until: float) -> list[tuple[float, float, str | None]]:
    """[(start, end, visual)] with consecutive repeats merged. visual: "DEMO" / "DEMO#<clip>", a figure
    ref, or None. None / unavailable figures keep the previous screen (the first ones borrow the first
    usable one). Scripts with no DEMO at all (older ones) play the demo until intro_until."""
    is_demo = lambda v: (v or "").startswith("DEMO")  # noqa: E731
    if has_demo and not any(is_demo(v) for _, v in shots):
        shots = [(t, "DEMO" if t < intro_until else v) for t, v in shots]
    usable = [v if (is_demo(v) and has_demo) or v in available else None for _, v in shots]
    first = next((v for v in usable if v), None)
    out: list[tuple[float, float, str | None]] = []
    prev = first
    for (t, _), v in zip(shots, usable):
        prev = v or prev
        if out and out[-1][2] == prev:
            continue
        if out:
            out[-1] = (out[-1][0], t, out[-1][2])
        out.append((t, duration, prev))
    if out:
        out[0] = (0.0, out[0][1], out[0][2])
    return [s for s in out if s[1] - s[0] > 1e-3]


def split_lines(ass: Path, y: int, gap: int) -> None:
    """Draw each caption line as its own event. libass puts \\N lines a full
    winAscent+winDescent apart (about 2 em for this font); gap = distance between line centers."""
    tag = rf"{{\pos(540,{y})}}"
    out = []
    for row in ass.read_text(encoding="utf-8").splitlines():
        head, sep, text = row.partition(tag)
        if not sep or r"\N" not in text:
            out.append(row)
            continue
        parts = text.split(r"\N")
        top = y - gap * (len(parts) - 1) / 2
        out += [rf"{head}{{\pos(540,{round(top + k * gap)})}}{p}" for k, p in enumerate(parts)]
    ass.write_text("\n".join(out) + "\n", encoding="utf-8")


def ass_size(design: dict, em_px: int) -> int:
    """ASS font size for an em of em_px: libass sizes by winAscent+winDescent, not the em."""
    from fontTools.ttLib import TTFont

    f = TTFont(str(TEMPLATE / design["font"]))
    return round(em_px * (f["OS/2"].usWinAscent + f["OS/2"].usWinDescent) / f["head"].unitsPerEm)


def _font(design: dict, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(TEMPLATE / design["font"]), size)


def _frame(design: dict, title: str, art: Path | None, out: Path) -> Path:
    bg = Image.open(TEMPLATE / design["background"]).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(bg)
    t = design["title"]
    size = t["font_size"]
    while size > 30 and draw.textlength(title, font=_font(design, size)) > W - 80:
        size -= 2
    draw.text((W // 2, t["y"]), title, font=_font(design, size), fill=tuple(t["color"]), anchor="mm")
    if art:
        x0, y0, x1, y1 = design["figure_box"]
        fig = ImageOps.contain(Image.open(art).convert("RGBA"), (x1 - x0, y1 - y0), Image.Resampling.LANCZOS)
        bg.paste(fig, (x0 + (x1 - x0 - fig.width) // 2, y0 + (y1 - y0 - fig.height) // 2), fig)  # keeps transparency
    bg.save(out)
    return out


def _script(pdf: Path, slug: str, venue: str, catalog: list[dict]) -> dict:
    cached = SCRIPTS_DIR / f"{slug}-shorts.json"
    if cached.exists():
        log.info("2/4 기존 숏폼 스크립트 재사용: %s", cached.name)
        return json.loads(cached.read_text(encoding="utf-8"))
    log.info("2/4 숏폼 스크립트 (templates/shortform 프롬프트)")
    paper = pdf_parser.parse(pdf)
    # The writer sees what the demo can actually show, so DEMO lands on lines it can illustrate.
    demo_info = (f"[데모 영상 장면 목록 — DEMO는 아래 장면으로 실제로 보여줄 수 있는 순간에만]\n{catalog_text(catalog)}\n\n"
                 if catalog else "")
    # Pictures first, story second: the writer sees which いらすとや pictures exist and writes the
    # ILLUST lines around one of them ("illust": number), instead of us hunting for a match afterwards.
    pool = illust_pool(paper)
    analogies = design_analogies(paper, pool)  # adds each analogy's candidate pictures to the pool
    pool_info = (f"[사용할 수 있는 일러스트 목록 — ILLUST 줄·컷은 이 중 하나의 번호를 \"illust\" 에 적고 그 그림 장면에 맞춰 쓸 것]\n"
                 + "\n".join(f"#{p['id']} {p['title']}" for p in pool) + "\n\n") if pool else ""
    analogy_info = ("[비유 설계 — 본론(방법·결과)에서 아래 비유를 \"쉽게 말하면 ~ / 예를 들면 ~\" 으로 쓰고, 그 순간 cuts 로 ILLUST + 추천 그림 번호]\n"
                    + "\n".join(f"- {a['concept']} → {a['analogy']} (대응: {a.get('mapping', '')}; 추천 그림: "
                                f"{', '.join('#' + str(i) for i in a.get('candidates', [])) or '목록에서 고를 것'})"
                                for a in analogies) + "\n\n") if analogies else ""
    figs = figure_list(pdf, AUDIO_DIR / f"{slug}-shorts" / "crops")
    fig_info = ("[사용 가능한 Figure/Table — visual_ref 는 이 목록에 있는 것만. 없는 번호는 화면에 못 나옴]\n"
                + "\n".join(f"{ref}: {cap}" for ref, cap in figs) + "\n\n") if figs else ""
    data = shorts_generator.generate_from_paper_iterative(
        paper_title=paper.title or slug, authors=paper.authors, venue=venue,
        paper_text=fig_info + analogy_info + pool_info + demo_info + paper.text,
        slug=slug, rounds=1, lang="ko",
        systems={"draft": _prompt("prompt.md"), "critic": _prompt("critic.md"), "refine": _prompt("refine.md"),
                 "polish": _prompt("polish.md")},
    )
    for line in data["script"]:
        line["speaker"] = SPEAKER
        line["text"] = strip_punct(line["text"])
    data.setdefault("metadata", {})["template"] = "shortform"
    _review_script(data, paper)
    _validate(data)
    easy_illust(data["script"])
    replace_missing_figures(data["script"], {ref for ref, _ in figs}, bool(catalog))
    _match_demo(data, paper, catalog)
    vary_screens(data["script"])
    use_pool(data["script"], pool)
    dropped = drop_text_pictures(data, AUDIO_DIR / f"{slug}-shorts")
    _pick_illustrations(data, paper, AUDIO_DIR / f"{slug}-shorts", avoid=dropped)  # ILLUST moments still without a picture
    cached.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


IRASUTOYA = "https://www.irasutoya.com/search?q="
_UA = {"User-Agent": "Mozilla/5.0 (papercast shortform; a few searches per video)"}


def irasutoya_search(query: str) -> list[tuple[str, str]]:
    """[(title, image url)] from one いらすとや search page (about 20 results).

    Terms (checked 2026-10): free for monetized YouTube up to 20 illustrations per video incl. the
    thumbnail, no credit needed, no redistribution, so files stay in the gitignored work dir."""
    import time
    import urllib.parse
    import urllib.request

    time.sleep(1)  # be gentle: a handful of searches per video, one at a time
    req = urllib.request.Request(IRASUTOYA + urllib.parse.quote(query), headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    import html as htmllib

    return [(htmllib.unescape(t), u) for u, t in re.findall(r'bp_thumbnail_resize\("([^"]+)","([^"]*)"\)', html)]


def illust_pool(paper) -> list[dict]:
    """Candidate いらすとや pictures for this paper, found before the script is written:
    the model proposes Japanese search words for the everyday problem and analogies
    (templates/shortform/illust_pool.md), each search keeps its top 4. [{"id", "title", "url"}]"""
    try:
        queries = _ask_json("illust_pool.md", f"논문 제목: {paper.title}\n\n[논문 본문 (발췌)]\n{paper.text[:8000]}",
                            "queries")["queries"]
    except Exception as e:
        log.warning("일러스트 후보 검색어 실패, 후보 없이 대본 작성: %s", e)
        return []
    pool, seen = [], set()
    for q in [str(q) for q in queries][:16]:
        try:
            hits = irasutoya_search(q) or (irasutoya_search(q.split()[0]) if " " in q else [])
        except OSError as e:
            log.warning("이라스토야 검색 실패 %r: %s", q, e)
            continue
        for title, url in hits[:4]:
            if url not in seen:
                seen.add(url)
                pool.append({"id": len(pool) + 1, "title": title, "url": url})
    log.info("일러스트 후보: 검색어 %d개 -> %d장 %s", len(queries), len(pool), [p["title"][:12] for p in pool[:8]])
    return pool[:40]  # analogy pictures are appended after these


def design_analogies(paper, pool: list[dict]) -> list[dict]:
    """Before the script: the stronger (polish) model works out 3~4 analogies for the paper's core
    mechanisms (templates/shortform/analogy.md): several candidates each, a part-by-part mapping, where
    it breaks, keep the best. Each analogy's search words are looked up on いらすとや and appended to
    the pool; their ids go in analogy["candidates"]. [] on failure."""
    try:
        out = _ask_json("analogy.md", f"논문 제목: {paper.title}\n\n[논문 본문 (발췌)]\n{paper.text[:30000]}",
                        "analogies", polish=True)
    except Exception as e:
        log.warning("비유 설계 실패, 비유 없이 대본 작성: %s", e)
        return []
    seen = {p["url"] for p in pool}
    analogies = [a for a in out["analogies"] if a.get("concept") and a.get("analogy")][:4]
    for a in analogies:
        a["candidates"] = []
        for q in [str(q) for q in a.get("search") or []][:3]:
            try:
                hits = irasutoya_search(q) or (irasutoya_search(q.split()[0]) if " " in q else [])
            except OSError:
                continue
            for title, url in hits[:3]:
                if url not in seen:
                    seen.add(url)
                    pool.append({"id": len(pool) + 1, "title": title, "url": url})
                    a["candidates"].append(len(pool))
        log.info("비유: %s → %s | 대응 %s | 그림 후보 %s", a["concept"], a["analogy"], a.get("mapping"), a["candidates"])
    return analogies


def use_pool(lines: list[dict], pool: list[dict]) -> None:
    """ILLUST lines/cuts that name a pool picture ("illust": n) get its URL; their "mood" becomes the
    picture's mood (a mood change between pictures plays a sound effect)."""
    by_id = {p["id"]: p for p in pool}
    for key, item, text in moments(lines, "ILLUST"):
        try:
            pick = by_id.get(int(str(item.get("illust", "")).lstrip("#")))
        except ValueError:
            pick = None
        if pick:
            item["illust_url"] = _sized(pick["url"], "s800")
            if item.get("mood") in SFX_KINDS:
                item["illust_mood"] = item["mood"]
            log.info("일러스트 %s -> #%d %s | %s", key, pick["id"], pick["title"], text)


def _sized(url: str, size: str) -> str:
    """Blogger image URL at another size: .../s72-c/x.png -> .../s400/x.png"""
    return re.sub(r"/s\d+(-c)?/", f"/{size}/", url)


def _fetch(url: str) -> bytes:
    import urllib.request

    with urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=30) as r:
        return r.read()


def _illust_sheets(items: list[tuple[str, str]], out_dir: Path, name: str) -> list[Path]:
    """[(label, いらすとや url)] -> numbered JPEG contact sheets, 4x3 tiles each (JPEG keeps each
    read under the SDK's 1MB cap)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    font = _font({"font": json.loads((TEMPLATE / "design.json").read_text(encoding="utf-8"))["font"]}, 26)
    tiles = []
    for label, url in items:
        try:
            img = Image.open(io.BytesIO(_fetch(_sized(url, "s300")))).convert("RGBA")
        except OSError:
            continue
        tile = Image.new("RGB", (300, 340), (255, 255, 255))
        img = ImageOps.contain(img, (290, 290))
        tile.paste(img, ((300 - img.width) // 2, 45), img)
        ImageDraw.Draw(tile).text((8, 6), label, font=font, fill=(200, 0, 0))
        tiles.append(tile)
    sheets = []
    for k in range(0, len(tiles), 12):
        sheet = Image.new("RGB", (300 * 4, 340 * 3), (255, 255, 255))
        for j, tile in enumerate(tiles[k:k + 12]):
            sheet.paste(tile, (300 * (j % 4), 340 * (j // 4)))
        sheets.append(out_dir / f"{name}_{k // 12 + 1}.jpg")
        sheet.save(sheets[-1], quality=80)
    return sheets


def drop_text_pictures(data: dict, work: Path) -> set[str]:
    """Rule: no picture with Japanese writing in it (viewers can't read it). The writer picks pool
    pictures by title only, so one look at them (templates/shortform/illust_text.md) finds the ones
    with text; those moments lose their picture and go back to the picker. Returns the dropped URLs."""
    chosen = [(k, item) for k, item, _ in moments(data["script"], "ILLUST") if item.get("illust_url")]
    if not chosen:
        return set()
    sheets = _illust_sheets([(k, item["illust_url"]) for k, item in chosen], work / "illust", "text")
    try:
        found = set(_ask_json("illust_text.md", "[키 목록]\n" + "\n".join(k for k, _ in chosen), "has_text",
                              images=sheets)["has_text"])
    except Exception as e:
        log.warning("일러스트 글자 검사 실패, 그대로 진행: %s", e)
        return set()
    dropped = set()
    for k, item in chosen:
        if k in found:
            dropped.add(item.pop("illust_url"))
            item.pop("illust", None)
            item.pop("illust_mood", None)
    log.info("일러스트 글자 검사: 일본어 글자 있음 %s -> 다시 고름", sorted(found))
    return dropped


def _pick_illustrations(data: dict, paper, work: Path, avoid: set[str] = frozenset()) -> None:
    """For every ILLUST moment still without a picture: the model writes Japanese search words
    (templates/shortform/illust_search.md; the last one is the line's subject, as a fallback), we search
    いらすとや, the model looks at the candidates on numbered sheets and picks one per moment
    (illust_pick.md). Pictures already in the video are not offered again."""
    found = [m for m in moments(data["script"], "ILLUST") if not m[1].get("illust_url")]
    avoid = set(avoid) | {m[1]["illust_url"] for m in moments(data["script"], "ILLUST") if m[1].get("illust_url")}
    targets = {key: item for key, item, _ in found}
    spoken = {key: text for key, _, text in found}
    if not targets:
        return
    lines = "\n".join(f"L{i} [{l.get('visual_ref')}] {l['text']}" for i, l in enumerate(data["script"]))
    need = "\n".join(f"{k}: {spoken[k]}" for k in targets)  # "L5@쉽게" = from that word to the next cut
    ask = f"논문 제목: {paper.title}\n\n[확정된 대본]\n{lines}\n\n[그림이 필요한 줄 — 키: 그 그림이 나오는 동안의 나레이션]\n{need}"
    try:
        queries = _ask_json("illust_search.md", ask, "queries")["queries"]
    except Exception as e:
        log.warning("이라스토야 검색어 생성 실패, 그림 없이 진행: %s", e)
        return
    cands: dict[str, list[tuple[str, str]]] = {}
    for key in targets:
        seen: dict[str, str] = {}
        for q in (queries.get(key) or [])[:4]:  # the 4th is the line's subject: always finds something
            try:
                hits = irasutoya_search(q)
                if not hits and " " in q:  # multi-word searches often match nothing: retry the main word
                    hits = irasutoya_search(q.split()[0])
                for title, url in hits:
                    if _sized(url, "s800") not in avoid:
                        seen.setdefault(url, title)
            except OSError as e:
                log.warning("이라스토야 검색 실패 %r: %s", q, e)
        cands[key] = list(seen.items())[:9]
        log.info("이라스토야 %s: 검색어 %s -> 후보 %d개", key, queries.get(key), len(cands[key]))
    sheets = _illust_sheets([(f"{key}-{n}", url) for key in cands for n, (url, _) in enumerate(cands[key], 1)],
                            work / "illust", "sheet")
    if not sheets:
        log.warning("이라스토야 후보 없음, 그림 없이 진행")
        return
    listing = "\n".join(f"{key}-{n}: {title}" for key in cands for n, (_, title) in enumerate(cands[key], 1))
    ask = f"[그림이 필요한 줄]\n" + "\n".join(f"{k}: {spoken[k]}" for k in targets) + f"\n\n[후보 제목]\n{listing}"
    try:
        out = _ask_json("illust_pick.md", ask, "picks", images=sheets)
        picks, moods = out["picks"], out.get("moods") or {}
    except Exception as e:
        log.warning("이라스토야 그림 고르기 실패, 그림 없이 진행: %s", e)
        return
    for key, line in targets.items():
        m = re.fullmatch(rf"{key}-(\d+)", str(picks.get(key) or ""))
        if not (m and 1 <= int(m.group(1)) <= len(cands[key]) and _sized(cands[key][int(m.group(1)) - 1][0], "s800") not in avoid):
            # Rule: always show something. No pick -> the top search hit not used yet (the subject query
            # guarantees a few), so the screen still changes.
            n = next((n for n, (u, _) in enumerate(cands[key], 1) if _sized(u, "s800") not in avoid), None)
            m = re.fullmatch(r"(\d+)", str(n)) if n else None
            if m:
                log.info("이라스토야 %s: 고른 그림 없음 -> 검색 1순위 후보 사용", key)
        if m:
            url, title = cands[key][int(m.group(1)) - 1]
            avoid.add(_sized(url, "s800"))  # one picture, one moment
            line["illust_url"] = _sized(url, "s800")
            if moods.get(key) in SFX_KINDS:  # a change of mood between pictures gets a sound effect
                line["illust_mood"] = moods[key]
            log.info("이라스토야 %s -> %s (%s) | %s", key, title, moods.get(key), spoken[key])
        else:
            log.warning("이라스토야 %s: 맞는 그림 없음 (%s)", key, picks.get(key))


def crop_figure(pdf: Path, ref: str, page: int, png: Path) -> Path | None:
    """Crop one Figure/Table; None when the cropper could only return the whole page
    (unreadable on a phone, e.g. tables in two-column layouts)."""
    if not png.exists():
        figure_cropper.crop_visual(pdf, page, ref, png)
    import fitz

    with fitz.open(pdf) as doc:
        full = doc[page - 1].rect
    w, h = Image.open(png).size
    if w >= full.width * 300 / 72 * 0.95 and h >= full.height * 300 / 72 * 0.95:
        return None
    return png


def figure_list(pdf: Path, crops_dir: Path) -> list[tuple[str, str]]:
    """[(ref, caption start)] for every Figure/Table that crops cleanly, so the writer only picks
    visuals that can actually be shown."""
    import fitz

    index = figure_indexer.build_index(pdf)
    crops_dir.mkdir(parents=True, exist_ok=True)
    out = []
    with fitz.open(pdf) as doc:
        # Appendix figures (after the references) are never what a short shows, and some are huge
        # vector plots that take minutes each to crop: skip them.
        refs_page = next((i + 1 for i in range(len(doc) // 3, len(doc))
                          if re.search(r"(?m)^\s*(References|REFERENCES|Bibliography)\s*$", doc[i].get_text())), len(doc))
        for ref, page in sorted(index.items(), key=lambda kv: (kv[0].split()[0], int(kv[0].split()[-1]))):
            if page > refs_page:
                log.info("%s: 부록(%d쪽)이라 제외", ref, page)
                continue
            if not crop_figure(pdf, ref, page, crops_dir / f"{ref.replace(' ', '_')}.png"):
                log.info("%s: 깔끔하게 잘리지 않아 제외", ref)
                continue
            num = int(ref.split()[-1])
            kind = "fig(?:ure|[.])" if ref.startswith("Figure") else "table"
            pat = rf"(?i)\b(?:{kind})\s*(?:{num}|{figure_indexer.int_to_roman(num)})\s*[:.|]\s*([^\n]{{0,80}})"
            m = re.search(pat, doc[page - 1].get_text())
            out.append((ref, m.group(1).strip() if m else ""))
    return out


def _match_demo(data: dict, paper, catalog: list[dict]) -> None:
    """Once the script is final, one more model call (templates/shortform/match.md) reads the paper,
    the script and the demo catalog and picks, for every DEMO moment, the clip that shows what the
    narration says. On failure DEMO plays on the video clock."""
    import asyncio

    from src.llm import generate_text

    if not catalog:
        return
    # Rule: the first screen is the demo's highlight, whatever the writer chose for the hook.
    best = highlight(catalog)
    hook = data["script"][0]
    hook["visual_ref"], hook["demo_clip"] = "DEMO", best["id"]
    log.info("첫 화면 = 데모 하이라이트 #%d (%d/5): %s", best["id"], best.get("wow", 3), best["desc"])
    moments = [m for m in demo_moments(data["script"]) if m[1] is not hook]
    if not moments:
        return
    lines = "\n".join(f"L{i} [{l.get('visual_ref')}] {l['text']}" for i, l in enumerate(data["script"]))
    prompt = (f"논문 제목: {paper.title}\n\n[논문 본문 (발췌)]\n{paper.text[:30000]}\n\n[확정된 대본]\n{lines}\n\n"
              f"[데모 영상 장면 목록 — #{best['id']} 은 첫 화면(L0)에 이미 썼으니 다른 순간엔 쓰지 말 것]\n{catalog_text(catalog)}\n\n"
              "[데모 구간을 골라야 하는 순간]\n" + "\n".join(f"{k}: {t}" for k, _, t in moments))
    log.info("데모 매칭: 대본 + 데모 장면을 읽고 %d순간에 구간 배정", len(moments))
    try:
        clips = _ask_json("match.md", prompt, "demo_clips")["demo_clips"]
    except Exception as e:
        log.warning("데모 매칭 실패, 데모는 영상 시간대로 재생: %s", e)
        return
    ids = {c["id"] for c in catalog}
    for key, item, text in moments:
        clip = clips.get(key)
        if isinstance(clip, int) and clip in ids:
            item["demo_clip"] = clip
            log.info("데모 %s -> #%d | %s", key, clip, text)


def build(pdf_in: Path, demo: Path | None, slug: str, venue: str = "") -> Path:
    from src.pipeline import _run_tts_and_merge  # pipeline imports this module

    pdf = PAPERS_DIR / f"{slug}.pdf"
    shutil.copy2(pdf_in, pdf)
    voice = _register_voice()
    design = json.loads((TEMPLATE / "design.json").read_text(encoding="utf-8"))
    shorts_slug = f"{slug}-shorts"
    work = AUDIO_DIR / shorts_slug
    catalog = demo_catalog(demo, work) if demo else []
    data = _script(pdf, slug, venue, catalog)
    lines = data["script"]
    outro = design.get("outro") or {}
    if outro.get("text") and lines[-1].get("visual_ref") != "OUTRO":  # fixed ending, not written by the model
        lines.append({"section": "outro", "speaker": SPEAKER, "text": outro["text"], "visual_ref": "OUTRO",
                      "emotion": "neutral", "pause_after_ms": 400})
    promote_first_cuts(lines)  # also fixes scripts saved before this rule

    if spoken_numbers(lines) | add_description_line(data):  # saved: a rebuild reads/describes the same way
        script_json = SCRIPTS_DIR / f"{shorts_slug}.json"
        script_json.write_text(json.dumps({**data, "script": [l for l in lines if l.get("visual_ref") != "OUTRO"]},
                                          ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("3/4 숏폼 TTS %d lines", len(lines))
    # The voice reads "tts" (numbers in Korean words) where present; captions below use "text".
    mp3, wavs, _ = _run_tts_and_merge({**data, "script": [{**l, "text": l.get("tts") or l["text"]} for l in lines]},
                                      shorts_slug)
    durs = [len(AudioSegment.from_file(wav)) / 1000 for wav in wavs]
    raw = sum(durs) + sum(int(l.get("pause_after_ms", 200)) / 1000 for l in lines)
    speed = max(float(voice.get("speed", 1.0)), raw / MAX_SECONDS)  # rule: the whole short stays under 60s
    if speed > float(voice.get("speed", 1.0)):
        log.info("나레이션 %.1f초 -> %.2f배속으로 %.1f초", raw, speed, MAX_SECONDS)
    starts, ends, t = [], [], 0.0
    for line, dur in zip(lines, durs):
        starts.append(t / speed)
        ends.append((t + dur) / speed)
        t += dur + int(line.get("pause_after_ms", 200)) / 1000
    duration = t / speed

    log.info("4/4 숏폼 영상 조립")
    cap = design["caption"]
    ass = work / "captions.ass"
    word_timing.build_subtitles(line_tokens(lines, starts, ends), ass, step=cap.get("mode") == "step",
                                line_chars=cap.get("line_chars", 10))
    ass.write_text(
        ass.read_text(encoding="utf-8")
        .replace("Pretendard Black,78,&H00FFFFFF", f"{cap['font_name']},{ass_size(design, cap['font_size'])},{cap['color']}")
        .replace(",1,5,0,5,", f",1,{cap.get('outline', 0)},0,5,")
        .replace(r"\pos(540,1380)", rf"\pos(540,{cap['y']})"),
        encoding="utf-8",
    )
    split_lines(ass, cap["y"], round(cap["font_size"] * cap.get("line_spacing", 1.25)))

    # Screen plan: line visuals + mid-line cuts -> [(start, end, "DEMO" | figure ref)].
    tokens = line_tokens(lines, starts, ends)
    shots = shot_list(lines, tokens, starts)
    fig_index = figure_indexer.build_index(pdf)
    crops_dir = work / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    pngs: dict[str, Path] = {}
    for _, item, _ in moments(lines, "ILLUST"):  # いらすとや pictures chosen at script time, downloaded once
        ref = _visual(item)
        if (ref or "").startswith("ILLUST:"):
            png = work / "illust" / item["illust_url"].rsplit("/", 1)[-1]
            if not png.exists():
                png.parent.mkdir(parents=True, exist_ok=True)
                png.write_bytes(_fetch(item["illust_url"]))
            pngs[ref] = png
    if outro.get("image") and (TEMPLATE / outro["image"]).exists():
        pngs["OUTRO"] = TEMPLATE / outro["image"]
    for ref in {v for _, v in shots if v and not v.startswith(("DEMO", "ILLUST", "OUTRO"))}:
        if fig_index.get(ref) and crop_figure(pdf, ref, fig_index[ref], crops_dir / f"{ref.replace(' ', '_')}.png"):
            pngs[ref] = crops_dir / f"{ref.replace(' ', '_')}.png"  # whole-page crops are left out (unreadable)
    intro_until = next((starts[i] for i, l in enumerate(lines) if l.get("section") == "method" and i),
                       starts[min(2, len(starts) - 1)])
    plan = plan_shots(shots, duration, set(pngs), demo is not None, intro_until)
    # Each DEMO span plays its chosen clip from that clip's start; unassigned DEMO uses the video clock.
    clip_start = {f"DEMO#{c['id']}": c["start"] for c in catalog}
    demo_spans = [(a, b, clip_start.get(v, a)) for a, b, v in plan if (v or "").startswith("DEMO")]

    title = re.sub(r"\*\*", "", (data.get("title_hook") or data.get("paper_title", "")).split("\n")[0])
    frames, segments = {}, []
    for a, b, v in plan:  # DEMO / ILLUST -> empty frame; those are overlaid (moving) below
        art = None if (v or "").startswith(("DEMO", "ILLUST")) else pngs.get(v)
        if art not in frames:
            frames[art] = _frame(design, title, art, crops_dir / f"frame_{len(frames):02}.png")
        segments.append((frames[art], b - a))
    concat = work / "frames.txt"
    composer._write_concat_list(segments, concat)

    x0, y0, x1, y1 = design["figure_box"]
    bw, bh = x1 - x0, y1 - y0
    tempo = f",atempo={speed}" if speed != 1.0 else ""
    bgm = design.get("bgm") or {}
    bgm_file = TEMPLATE / bgm["file"] if bgm.get("file") else None
    if bgm_file and not bgm_file.exists():
        log.warning("배경음 없음: %s (배경음 없이 진행)", bgm_file)
        bgm_file = None
    # Inputs: 0 = still frames, 1..n = one demo input per span (seeked to its clip), then narration, bgm.
    demo_inputs, video = [], "[0:v]fps=30[v0]"  # fps=30: overlay only composites when a main frame arrives
    for k, (a, b, start) in enumerate(demo_spans, 1):
        demo_inputs += ["-stream_loop", "-1", "-ss", f"{start:.3f}", "-t", f"{b - a + 1:.3f}", "-i", str(demo)]
        video += (f";[{k}:v]setpts=PTS-STARTPTS+{a:.3f}/TB,scale={bw}:{bh}:force_original_aspect_ratio=decrease,setsar=1[d{k}]"
                  f";[v{k - 1}][d{k}]overlay={x0}+({bw}-w)/2:{y0}+({bh}-h)/2:enable='between(t,{a:.3f},{b:.3f})'[v{k}]")
    # Illustrations: slow zoom-in while on screen (start at 90% of the box, grow by illust_zoom).
    # The picture is composited onto the background's own patch, then zoompan crops a fixed-size
    # window from a 4x copy: sub-pixel steps, so no 1px shaking (scaling the overlay itself jittered).
    zoom = float(design.get("illust_zoom", 0.05))
    bg_box = Image.open(TEMPLATE / design["background"]).convert("RGB").resize((W, H), Image.Resampling.LANCZOS).crop((x0, y0, x1, y1))
    k = len(demo_spans)
    for a, b, v in plan:
        if not (v or "").startswith("ILLUST:") or v not in pngs:
            continue
        k += 1
        fit = ImageOps.contain(Image.open(pngs[v]).convert("RGBA"), (round(bw * 0.9), round(bh * 0.9)), Image.Resampling.LANCZOS)
        box = bg_box.copy()
        box.paste(fit, ((bw - fit.width) // 2, (bh - fit.height) // 2), fit)
        box_png = pngs[v].with_name(f"box_{k:02}.png")
        box.save(box_png)
        frames_n = max(2, round((b - a) * 30) + 1)
        demo_inputs += ["-i", str(box_png)]
        video += (f";[{k}:v]scale={bw * 4}:{bh * 4},zoompan=z='1+{zoom}*on/{frames_n}'"
                  f":x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frames_n}:s={bw}x{bh}:fps=30,"
                  f"setpts=PTS-STARTPTS+{a:.3f}/TB[d{k}]"
                  f";[v{k - 1}][d{k}]overlay={x0}:{y0}:enable='between(t,{a:.3f},{b:.3f})'[v{k}]")
    n = k
    nar = n + 1
    # Audio: narration, then bgm (looped, faded out over the last 2s), then one input per sound effect.
    # bgm and sound effects are levelled to the narration: mix_db relative to its loudness (-6 = half).
    level = mean_db(mp3) + float(design.get("mix_db", -6))
    tracks, extra = [f"[{nar}:a]anull{tempo}[n]"], []
    if bgm_file:
        extra += ["-stream_loop", "-1", "-i", str(bgm_file)]
        bgm_level = mean_db(mp3) + float(bgm.get("db", design.get("mix_db", -6)))  # bgm can sit lower than sfx
        tracks.append(f"[{nar + 1}:a]volume={bgm_level - mean_db(bgm_file):.1f}dB,"
                      f"afade=t=out:st={max(0.0, duration - 2):.3f}:d=2[m]")
    sfx = design.get("sfx") or {}
    events = [(t, f) for t, f in sfx_files(sfx_events(lines, tokens, starts), TEMPLATE / sfx.get("dir", "sfx")) if t < duration - 0.3]
    first_sfx = nar + 1 + bool(bgm_file)
    for k, (t, f) in enumerate(events):
        extra += ["-i", str(f)]
        ms = round(t * 1000)
        tracks.append(f"[{first_sfx + k}:a]adelay={ms}:all=1,volume={level - mean_db(f):.1f}dB[s{k}]")
    labels = "[n]" + ("[m]" if bgm_file else "") + "".join(f"[s{k}]" for k in range(len(events)))
    audio = ";".join(tracks) + f";{labels}amix=inputs={labels.count('[')}:duration=first:normalize=0[a]"
    out = VIDEOS_DIR / f"{shorts_slug}.mp4"
    graph = (video + f";[v{n}]subtitles='{composer._escape_filter_path(ass)}'"
             f":fontsdir='{composer._escape_filter_path(TEMPLATE)}'[v];" + audio)
    if events:
        log.info("효과음: %s", [(round(t, 1), f.parent.name + "/" + f.stem) for t, f in events])
    composer._run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), *demo_inputs, "-i", str(mp3), *extra,
        "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-r", "30", "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ])
    log.info("shortform: %s (%.1fs, demo %s)", out.name, duration,
             [(round(a, 1), round(b, 1), round(s, 1)) for a, b, s in demo_spans])
    return out


def _selftest() -> None:
    assert strip_punct("83.4%가 1,000명. 근데, 진짜") == "83.4%가 1,000명 근데 진짜"
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        ass = Path(d) / "c.ass"
        ass.write_text("Dialogue: 0,0:00:00.00,0:00:01.00,Speech,,0,0,0,,{\\pos(540,560)}가나\\N다라\n", encoding="utf-8")
        split_lines(ass, 560, 80)
        assert ass.read_text(encoding="utf-8").splitlines() == [
            "Dialogue: 0,0:00:00.00,0:00:01.00,Speech,,0,0,0,,{\\pos(540,520)}가나",
            "Dialogue: 0,0:00:00.00,0:00:01.00,Speech,,0,0,0,,{\\pos(540,600)}다라",
        ]
    lines = [{"text": "님들 혹시 이거 암?", "visual_ref": "DEMO"},
             {"text": "연구팀이 이거 만듦", "visual_ref": "DEMO", "cuts": [{"at": "이거", "visual_ref": "Figure 1"}]},
             {"text": "근데 진짜 문제는 이거임", "visual_ref": None, "cuts": [{"at": "문제는", "visual_ref": "DEMO"}]}]
    toks = line_tokens(lines, [0.0, 2.0, 4.0], [2.0, 4.0, 8.0])
    shots = shot_list(lines, toks, [0.0, 2.0, 4.0])[1:]  # drop the hook; plan below starts at line 1
    assert [v for _, v in shots] == ["DEMO", "Figure 1", None, "DEMO"]
    assert _ref("Fig. 3") == "Figure 3" and _ref("demo#4") == "DEMO#4" and _ref("illust") == "ILLUST"
    assert _sized("https://b.com/img/a/s72-c/sara_arai.png", "s800") == "https://b.com/img/a/s800/sara_arai.png"
    ill = {"text": "설거지가 산더미", "visual_ref": "ILLUST", "illust_url": "https://b.com/s800/sara_arai.png",
           "cuts": [{"at": "산더미", "visual_ref": "DEMO"}]}
    assert _visual(ill) == "ILLUST:SARA_ARAI.PNG" and not _cuts_allowed(1, ill)
    first = [{"text": "쉽게 보면 안무를 덩어리째 추는 셈임", "visual_ref": "Figure 1",
              "cuts": [{"at": "쉽게", "visual_ref": "ILLUST", "illust": 67, "illust_url": "u", "mood": "positive"}]}]
    promote_first_cuts(first)
    assert first[0]["visual_ref"] == "ILLUST" and first[0]["illust"] == 67 and first[0]["cuts"] == []
    easy = [{"text": "님들 혹시 이거 암?"}, {"text": "이게 RCC인데 쉽게 말해 순서표임", "visual_ref": "Figure 3"}]
    easy_illust(easy)
    assert easy[1]["cuts"] == [{"at": "쉽게", "visual_ref": "ILLUST"}]
    assert [(k, t) for k, _, t in moments(easy, "ILLUST")] == [("L1@쉽게", "쉽게 말해 순서표임")]
    ex = [{"text": "님들 혹시 이거 암?"}, {"text": "묶어서 외우는 거임 예를 들면 안무 8박자", "visual_ref": "Figure 1"}]
    easy_illust(ex)
    assert ex[1]["cuts"] == [{"at": "예를", "visual_ref": "ILLUST"}]
    long_line = {"text": "로봇이 사람한테 시범을 오십 번 보고 배웠는데 엘리베이터 호출은 무려 구십오 퍼센트 성공함",
                 "visual_ref": "DEMO", "demo_clip": 7, "sfx": "positive",
                 "cuts": [{"at": "엘리베이터", "visual_ref": "Table 1"}]}
    parts = split_long([long_line], 40)
    assert all(len(p["text"]) <= 40 for p in parts) and len(parts) == 2
    assert parts[0]["text"].endswith("배웠는데") and parts[0]["sfx"] == "positive" and "sfx" not in parts[1]
    assert parts[1]["visual_ref"] == "DEMO" and parts[1]["demo_clip"] == 7 and parts[1]["cuts"][0]["at"] == "엘리베이터"
    pool_lines = [{"text": "님들 혹시 이거 암?"}, {"text": "설거지가 산더미임", "visual_ref": "ILLUST", "illust": "#2", "mood": "negative"},
                  {"text": "빨래도 산더미임", "visual_ref": "ILLUST", "illust": 9}]
    use_pool(pool_lines, [{"id": 2, "title": "皿洗い", "url": "https://b.com/s72-c/sara.png"}])
    assert pool_lines[1]["illust_url"] == "https://b.com/s800/sara.png" and pool_lines[1]["illust_mood"] == "negative"
    assert "illust_url" not in pool_lines[2]  # unknown number: left for the fallback picker
    got = script_issues([{"text": "가" * 41, "cuts": [{"at": "없음"}]}])
    assert got[0].startswith("전체 41자") and got[1].startswith("L0: 41자")
    assert not any(i.startswith("전체") for i in script_issues([{"text": "가" * 30}] * 19))  # 570 chars: in range
    fx = [{"text": "님들 혹시 이거 암?", "sfx": "surprise", "visual_ref": "DEMO"},
          {"text": "근데 새우는 망함", "sfx": "nope", "visual_ref": "Figure 1",
           "cuts": [{"at": "새우는", "sfx": "negative", "visual_ref": "DEMO"}]},
          {"text": "그래도 계속 볶음", "sfx": "weird"}]  # same screen: its sound is dropped (rule)
    ev = sfx_events(fx, line_tokens(fx, [0.0, 2.0, 6.0], [2.0, 4.0, 8.0]), [0.0, 2.0, 6.0])
    assert [k for _, k in ev] == ["negative"] and ev[0][0] > 2.0  # the hook's sfx is dropped (rule)
    il = [{"text": "님들 혹시 이거 암?"},
          {"text": "설거지가 산더미임", "visual_ref": "ILLUST", "illust_mood": "negative", "illust_url": "u/a.png"},
          {"text": "빨래도 산더미임", "visual_ref": "ILLUST", "illust_mood": "negative", "illust_url": "u/b.png"},
          {"text": "근데 로봇이 다 해줌", "visual_ref": "ILLUST", "illust_mood": "positive", "sfx": "surprise", "illust_url": "u/c.png"},
          {"text": "그래도 비쌈", "visual_ref": "ILLUST", "illust_mood": "weird", "illust_url": "u/d.png"}]
    ev = sfx_events(il, line_tokens(il, [0, 2, 4, 6, 8], [2, 4, 6, 8, 10]), [0, 2, 4, 6, 8])
    # mood sounds only on a change; the script's own sound wins where both fall at once
    assert ev == [(2, "negative"), (6, "surprise"), (8, "weird")]
    with tempfile.TemporaryDirectory() as d:
        for name in ("negative/a.mp3", "negative/b.mp3"):
            (Path(d) / name).parent.mkdir(exist_ok=True)
            (Path(d) / name).write_bytes(b"")
        got = sfx_files([(1, "negative"), (2, "negative"), (3, "negative"), (4, "weird")], Path(d))
        assert [f.name for _, f in got] == ["a.mp3", "b.mp3", "a.mp3"]  # rotates, skips kinds without files
    # scene cuts: 0.5s blip merges into the previous span, longer than 6s shots split into <=6s pieces
    assert segment_bounds([3.0, 3.5, 10.0], 24.0) == [(0.0, 3.5), (3.5, 6.75), (6.75, 10.0), (10.0, 14.67), (14.67, 19.33), (19.33, 24.0)]
    assert len(segment_bounds([float(t) for t in range(1, 100)], 100.0, min_len=0.5, max_n=36)) == 36
    script = [{"text": "님들 혹시 이거 암?", "visual_ref": "DEMO"},
              {"text": "엘리베이터 호출은 95% 성공 새우 볶기는 실패", "visual_ref": "Table 1",
               "cuts": [{"at": "새우", "visual_ref": "DEMO"}]}]
    assert [(k, t) for k, _, t in demo_moments(script)] == [("L0", "님들 혹시 이거 암?"), ("L1@새우", "새우 볶기는 실패")]
    script[1]["cuts"][0]["demo_clip"] = 7
    assert [v for _, v in shot_list(script, line_tokens(script, [0.0, 2.0], [2.0, 5.0]), [0.0, 2.0])] == ["DEMO", "Table 1", "DEMO#7"]
    assert plan_shots(shots, 8.0, {"Figure 1"}, True, 0)[1:] == [(shots[1][0], shots[3][0], "Figure 1"), (shots[3][0], 8.0, "DEMO")]
    assert [v for *_, v in plan_shots(shots, 8.0, {"Figure 1"}, False, 0)] == ["Figure 1"]  # no clip: figure only
    old = [(0.0, None), (2.0, None), (4.0, "Figure 2"), (6.0, "Table 9")]  # older script, Table 9 not croppable
    assert plan_shots(old, 8.0, {"Figure 2"}, True, 4.0) == [(0.0, 4.0, "DEMO"), (4.0, 8.0, "Figure 2")]
    vs = [{"text": "훅", "visual_ref": "DEMO", "demo_clip": 1}, {"text": "가", "visual_ref": "Figure 1"},
          {"text": "나"}, {"text": "다", "visual_ref": "Figure 1"}, {"text": "라"},  # 4th line on Figure 1
          {"text": "마", "visual_ref": "Figure 2"}, {"text": "바 사", "visual_ref": "Figure 3",
                                                    "cuts": [{"at": "사", "visual_ref": "Figure 1"}]}]
    vary_screens(vs)
    mf = [{"text": "가", "visual_ref": "Figure 9", "illust": 3}, {"text": "나 다", "visual_ref": "Figure 1",
                                                                 "cuts": [{"at": "다", "visual_ref": "Table 2"}]}]
    replace_missing_figures(mf, {"Figure 1"}, True)
    assert mf[0] == {"text": "가", "visual_ref": "DEMO"} and mf[1]["cuts"][0]["visual_ref"] == "DEMO"
    assert [_ref(l.get("visual_ref")) for l in vs][4:6] == ["ILLUST", "Figure 2"]  # hold of 3 lines, then a picture
    assert vs[6]["cuts"][0]["visual_ref"] == "ILLUST"  # Figure 1 again -> picture instead
    cat = [{"id": 1, "start": 0, "end": 2, "wow": 1}, {"id": 2, "start": 2, "end": 4, "wow": 5},
           {"id": 3, "start": 4, "end": 9, "wow": 5}, {"id": 4, "start": 9, "end": 10}]
    assert highlight(cat)["id"] == 3  # top wow, the longer clip on ties
    toks = line_tokens([{"text": "가 나나"}], [1.0], [4.0])
    assert [(x["start"], x["end"]) for x in toks] == [(1.0, 2.0), (2.0, 4.0)]


if __name__ == "__main__":
    _selftest()
    print("ok")
