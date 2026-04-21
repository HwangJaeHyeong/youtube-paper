"""Build SRT subtitles from per-line audio durations."""
from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment


def _fmt(ms: int) -> str:
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(lines: list[dict], audio_files: list[Path], out_path: Path) -> Path:
    """lines: script lines with `text` + `pause_after_ms`. audio_files aligned to lines."""
    assert len(lines) == len(audio_files)
    cursor_ms = 0
    entries: list[str] = []
    for idx, (line, audio) in enumerate(zip(lines, audio_files), start=1):
        dur_ms = len(AudioSegment.from_file(audio))
        start, end = cursor_ms, cursor_ms + dur_ms
        entries.append(f"{idx}\n{_fmt(start)} --> {_fmt(end)}\n{line['speaker']}: {line['text']}\n")
        cursor_ms = end + int(line.get("pause_after_ms", 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(entries), encoding="utf-8")
    return out_path
