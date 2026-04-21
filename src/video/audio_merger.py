"""Merge per-line WAV files into a single MP3 with inter-line pauses."""
from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment


def merge(line_files: list[tuple[Path, int]], out_path: Path) -> Path:
    """
    line_files: [(wav_path, pause_after_ms), ...] in playback order.
    Returns the merged MP3 path.
    """
    combined = AudioSegment.empty()
    for path, pause_ms in line_files:
        combined += AudioSegment.from_file(path)
        if pause_ms > 0:
            combined += AudioSegment.silent(duration=pause_ms)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.export(out_path, format="mp3", bitrate="192k")
    return out_path
