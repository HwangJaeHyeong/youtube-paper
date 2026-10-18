"""Build subtitles from per-line audio durations.

build_srt: plain SRT (fallback, legacy).
build_ass: ASS format with per-speaker color styling (preferred).
"""
from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment

from src.config import VOICE_CONFIG


def _fmt_srt(ms: int) -> str:
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _fmt_ass(ms: int) -> str:
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    cs = ms // 10
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_srt(lines: list[dict], audio_files: list[Path], out_path: Path) -> Path:
    assert len(lines) == len(audio_files)
    cursor_ms = 0
    entries: list[str] = []
    for idx, (line, audio) in enumerate(zip(lines, audio_files), start=1):
        dur_ms = len(AudioSegment.from_file(audio))
        start, end = cursor_ms, cursor_ms + dur_ms
        entries.append(f"{idx}\n{_fmt_srt(start)} --> {_fmt_srt(end)}\n{line['speaker']}: {line['text']}\n")
        cursor_ms = end + int(line.get("pause_after_ms", 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(entries), encoding="utf-8")
    return out_path


_DEFAULT_COLOR = "&H00FFFFFF"  # white


import re as _re

_SENT_SPLIT = _re.compile(r"(?<=[\.\!\?。！？])\s+|(?<=[\.\!\?。！？])(?=[A-Z가-힣])")


def _chunk_text(text: str, max_chars: int = 28) -> list[str]:
    """Strict sentence-level chunks. Each sentence becomes one subtitle entry; ASS handles wrap.

    `max_chars` is kept for backwards compat but ignored — sentences are atomic.
    """
    text = text.strip()
    sentences = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    return sentences or [text]


def _force_wrap(text: str, max_chars: int = 12) -> str:
    """Greedy *word-aware* wrap with ASS `\\N` line breaks.

    Never splits a word mid-character. If a single word exceeds max_chars it
    gets its own line (slightly overflowing) rather than being chopped.

    Clause-end tolerance: a SHORT word ending in punctuation (e.g. "아닌,",
    "근데.") is allowed to overflow max_chars by up to TOLERANCE chars to
    avoid isolating it on a line by itself.

    Locks visual layout so `\\fscx`/`\\fscy` scale animations cannot trigger
    libass auto-wrap reflow mid-animation.
    """
    TOLERANCE = 4
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word) if current else word
        is_short_clause_end = (
            current and len(word) <= 4 and word and word[-1] in ",.;:?!"
        )
        if len(candidate) <= max_chars or not current:
            current = candidate
        elif is_short_clause_end and len(candidate) <= max_chars + TOLERANCE:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return r"\N".join(lines)


def build_ass(
    lines: list[dict],
    audio_files: list[Path],
    out_path: Path,
    font_size: int = 66,
    margin_v: int = 280,
    margin_lr: int = 35,
    font: str = "Malgun Gothic",
    line_is_cover: list[bool] | None = None,
    style: str = "default",
) -> Path:
    """ASS subtitle with per-speaker PrimaryColour (defined in VOICE_CONFIG).

    Defaults sized so Korean lines up to ~28 chars fit within a 1080-wide frame.
    When `line_is_cover[i]` is True, that line renders centered (an5) instead of
    bottom-anchored (an2) — useful when no figure is shown behind the text.

    style="hype": Korean YouTube-shorts caption look — large Pretendard Black,
    always center, pop-in scale animation per chunk for snappy entrance.
    """
    if style == "hype":
        font = "Pretendard Black"
        font_size = 88
        outline_px = 5
        shadow_px = 0
        # alignment 5 = middle-center; margins ignored for vertical placement
        alignment = 5
        bold_flag = 0  # Pretendard Black is already extra heavy
    else:
        outline_px = 4
        shadow_px = 0
        alignment = 2  # bottom-center (default per-style; per-line an5 override for cover)
        bold_flag = -1

    assert len(lines) == len(audio_files)
    speakers = sorted({l["speaker"] for l in lines})
    style_defs: list[str] = []
    for spk in speakers:
        color = VOICE_CONFIG.get(spk, {}).get("subtitle_color", _DEFAULT_COLOR)
        # Override colour for hype: pure white text + pure black outline (Korean shorts standard)
        primary = "&H00FFFFFF" if style == "hype" else color
        outline_col = "&H00000000"
        # Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,
        # Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle,
        # Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        style_defs.append(
            f"Style: {spk},{font},{font_size},{primary},&H000000FF,{outline_col},&H00000000,"
            f"{bold_flag},0,0,0,100,100,0,0,1,{outline_px},{shadow_px},{alignment},"
            f"{margin_lr},{margin_lr},{margin_v},1"
        )

    # Pop-in entrance: snappy grow 80% → 100% over 110ms with a 30ms fade-in.
    # Small scale delta + short duration keeps motion crisp without bounce.
    POP_IN_TAG = r"{\fad(30,0)\fscx80\fscy80\t(0,110,\fscx100\fscy100)}"
    # Lead each visual line ~150ms ahead of its audio cue so the text is fully
    # on screen slightly before the corresponding audio plays (animation itself
    # eats ~140ms — fade 30ms + scale 110ms — so this puts the fully-rendered
    # caption ~10ms ahead of the spoken word).
    LEAD_MS = 150

    events: list[str] = []
    cursor_ms = 0
    n = len(lines)
    for i, (line, audio) in enumerate(zip(lines, audio_files)):
        dur_ms = len(AudioSegment.from_file(audio))
        pause_ms = int(line.get("pause_after_ms", 0))
        # Where the *next* line's audio (and thus its subtitle) begins.
        next_line_start = cursor_ms + dur_ms + pause_ms
        # Hold this line's last chunk until the next line takes over — eliminates
        # the blank-frame "blink" while pause_after_ms elapses between lines.
        # Opt-out via hide_subtitle_during_pause for "judge the picture" beats
        # where the visual must read clean during the silent pause.
        if line.get("hide_subtitle_during_pause"):
            last_chunk_end = cursor_ms + dur_ms
        else:
            last_chunk_end = next_line_start if i < n - 1 else cursor_ms + dur_ms

        if line.get("skip_subtitle"):
            cursor_ms = next_line_start
            continue
        raw_text = line["text"].replace("\n", " ")
        is_cover = bool(line_is_cover and i < len(line_is_cover) and line_is_cover[i])
        chunks = _chunk_text(raw_text, max_chars=30)
        total_len = sum(len(c) for c in chunks) or 1
        chunk_start = cursor_ms
        for ci, chunk in enumerate(chunks):
            share = int(dur_ms * len(chunk) / total_len)
            if ci < len(chunks) - 1:
                chunk_end = chunk_start + share
            else:
                chunk_end = last_chunk_end
            if style == "hype":
                # Emit ONE event per visual line (after force-wrap), so lines pop in
                # sequentially rather than appearing all at once.
                wrapped = _force_wrap(chunk, max_chars=12)
                visual_lines = wrapped.split(r"\N")
                vl_total = sum(len(v) for v in visual_lines) or 1
                vl_start = chunk_start
                for vi, vline in enumerate(visual_lines):
                    if vi < len(visual_lines) - 1:
                        vl_share = int((chunk_end - chunk_start) * len(vline) / vl_total)
                        vl_end = vl_start + vl_share
                    else:
                        vl_end = chunk_end
                    text = POP_IN_TAG + vline
                    # Apply uniform lead so subs hit full scale on the audio cue.
                    ev_start = max(0, vl_start - LEAD_MS)
                    ev_end = max(ev_start + 1, vl_end - LEAD_MS)
                    events.append(f"Dialogue: 0,{_fmt_ass(ev_start)},{_fmt_ass(ev_end)},{line['speaker']},,0,0,0,,{text}")
                    vl_start = vl_end
            else:
                text = chunk
                if is_cover:
                    text = r"{\an5}" + text
                events.append(f"Dialogue: 0,{_fmt_ass(chunk_start)},{_fmt_ass(chunk_end)},{line['speaker']},,0,0,0,,{text}")
            chunk_start = chunk_end
        cursor_ms = next_line_start

    ass = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "YCbCr Matrix: TV.709\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        + "\n".join(style_defs) + "\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + "\n".join(events) + "\n"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(ass, encoding="utf-8")
    return out_path
