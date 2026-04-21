"""Generate clean fallback background images for non-figure segments.

No arXiv watermark, no paper-page noise. Just a solid dark frame so subtitles pop.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from src.config import SHORTS_RESOLUTION


def render_cover(out_png: Path, size: tuple[int, int] = SHORTS_RESOLUTION, color: tuple[int, int, int] = (20, 22, 30)) -> Path:
    """Dark flat PNG at `size`. Used as fallback background for lines without visual_ref."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color)
    img.save(out_png, "PNG")
    return out_png
