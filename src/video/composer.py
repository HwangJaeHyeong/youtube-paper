"""FFmpeg-based final video assembly. Phase 2 scaffolding."""
from __future__ import annotations

from pathlib import Path

import ffmpeg

from src.config import AUDIO_BITRATE, FPS, LONGFORM_RESOLUTION


def compose_audio_only(audio_mp3: Path, cover_png: Path, out_mp4: Path) -> Path:
    """Minimum-viable video: one static cover image + the merged audio."""
    w, h = LONGFORM_RESOLUTION
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    (
        ffmpeg
        .input(str(cover_png), loop=1, framerate=FPS)
        .filter("scale", w, h, force_original_aspect_ratio="decrease")
        .filter("pad", w, h, "(ow-iw)/2", "(oh-ih)/2", color="black")
        .output(
            ffmpeg.input(str(audio_mp3)),
            str(out_mp4),
            vcodec="libx264",
            pix_fmt="yuv420p",
            acodec="aac",
            audio_bitrate=AUDIO_BITRATE,
            shortest=None,
            movflags="+faststart",
        )
        .overwrite_output()
        .run(quiet=True)
    )
    return out_mp4
