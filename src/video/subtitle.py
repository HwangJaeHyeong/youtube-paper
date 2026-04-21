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


def build_ass(
    lines: list[dict],
    audio_files: list[Path],
    out_path: Path,
    font_size: int = 66,
    margin_v: int = 280,
    margin_lr: int = 35,
    font: str = "Malgun Gothic",
) -> Path:
    """ASS subtitle with per-speaker PrimaryColour (defined in VOICE_CONFIG).

    Defaults sized so Korean lines up to ~28 chars fit within a 1080-wide frame.
    """
    assert len(lines) == len(audio_files)
    speakers = sorted({l["speaker"] for l in lines})
    style_defs: list[str] = []
    for spk in speakers:
        color = VOICE_CONFIG.get(spk, {}).get("subtitle_color", _DEFAULT_COLOR)
        # Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour,
        # Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle,
        # Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        style_defs.append(
            f"Style: {spk},{font},{font_size},{color},&H000000FF,&H00000000,&H00000000,"
            f"-1,0,0,0,100,100,0,0,1,4,0,2,{margin_lr},{margin_lr},{margin_v},1"
        )

    events: list[str] = []
    cursor_ms = 0
    for line, audio in zip(lines, audio_files):
        dur_ms = len(AudioSegment.from_file(audio))
        start, end = cursor_ms, cursor_ms + dur_ms
        text = line["text"].replace("\n", "\\N")
        events.append(f"Dialogue: 0,{_fmt_ass(start)},{_fmt_ass(end)},{line['speaker']},,0,0,0,,{text}")
        cursor_ms = end + int(line.get("pause_after_ms", 0))

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
