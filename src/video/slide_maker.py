"""Render paper pages as slide images (PNG)."""
from __future__ import annotations

from pathlib import Path

from pdf2image import convert_from_path


def render_pages(pdf_path: Path, out_dir: Path, dpi: int = 150) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    images = convert_from_path(str(pdf_path), dpi=dpi)
    paths: list[Path] = []
    for i, img in enumerate(images, start=1):
        p = out_dir / f"page_{i:03d}.png"
        img.save(p, "PNG")
        paths.append(p)
    return paths
