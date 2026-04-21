"""FFmpeg video assembly: longform (16:9) and shorts (9:16).

Minimal MVP:
- Shorts: first page of paper as background (letterboxed into 1080x1920),
  hard-coded SRT subtitles center, audio from the merged MP3.
- Longform: same pattern, 1920x1080, slides could later cycle per section.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from src.config import AUDIO_BITRATE, FPS, LONGFORM_RESOLUTION, SHORTS_RESOLUTION

_SUB_FONT = "Malgun Gothic"


def _escape_subs_path(p: Path) -> str:
    """FFmpeg subtitles filter needs backslash-escaped, colons escaped too (Windows)."""
    s = str(p.resolve()).replace("\\", "/").replace(":", "\\:")
    return s


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed:\n{e.stderr[-2000:]}") from None


def compose_shorts(
    audio_mp3: Path,
    srt_file: Path,
    background_png: Path,
    out_mp4: Path,
) -> Path:
    """1080x1920 vertical. Background image letterboxed, big center subtitles."""
    w, h = SHORTS_RESOLUTION
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    subs_style = (
        f"FontName={_SUB_FONT},FontSize=14,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,"
        "Alignment=2,MarginV=200,Bold=1"
    )
    vf = (
        f"scale={w}:-1:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x1a1a1a,"
        f"subtitles='{_escape_subs_path(srt_file)}':force_style='{subs_style}'"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", str(background_png),
        "-i", str(audio_mp3),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        "-shortest", "-movflags", "+faststart",
        str(out_mp4),
    ]
    _run(cmd)
    return out_mp4


def compose_longform(
    audio_mp3: Path,
    srt_file: Path,
    background_png: Path,
    out_mp4: Path,
) -> Path:
    """1920x1080. Same assembly as shorts but horizontal."""
    w, h = LONGFORM_RESOLUTION
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    subs_style = (
        f"FontName={_SUB_FONT},FontSize=12,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
        "Alignment=2,MarginV=80"
    )
    vf = (
        f"scale={w}:-1:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x1a1a1a,"
        f"subtitles='{_escape_subs_path(srt_file)}':force_style='{subs_style}'"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", str(background_png),
        "-i", str(audio_mp3),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        "-shortest", "-movflags", "+faststart",
        str(out_mp4),
    ]
    _run(cmd)
    return out_mp4
