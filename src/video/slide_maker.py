"""Render paper pages as slide images (PNG) via PyMuPDF (no poppler needed)."""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF


def render_pages(pdf_path: Path, out_dir: Path, dpi: int = 150) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    paths: list[Path] = []
    with fitz.open(str(pdf_path)) as doc:
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            p = out_dir / f"page_{i:03d}.png"
            pix.save(str(p))
            paths.append(p)
    return paths
