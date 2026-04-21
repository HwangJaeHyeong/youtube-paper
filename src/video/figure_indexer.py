"""Scan a paper PDF and build a {caption → page_index} map.

Catches `Figure N`, `Fig. N`, `Table N` and their Korean variants.
Page indices are 1-based to match pdf2image output filenames.
"""
from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

# Caption-start patterns. Require that the mention actually looks like a
# figure/table CAPTION line (followed by ":" or "."), which lives on the page
# showing the figure. Body-text references like "as in Figure 1" can occur on
# any page and would mislead the mapping.
_CAPTION_PATTERNS = [
    re.compile(r"(?i)\b(figure|fig\.)\s*(\d+)\s*[:.]"),
    re.compile(r"(?i)\b(table)\s*(\d+)\s*[:.]"),
]


def _normalize(kind: str, number: str) -> str:
    k = kind.lower()
    if k in ("figure", "fig."):
        return f"Figure {int(number)}"
    if k == "table":
        return f"Table {int(number)}"
    return f"{k.capitalize()} {int(number)}"


def build_index(pdf_path: Path) -> dict[str, int]:
    """Return {'Figure 1': page_idx_1_based, 'Table 3': 8, ...}. First-occurrence wins."""
    reader = PdfReader(str(pdf_path))
    index: dict[str, int] = {}
    for page_idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for pat in _CAPTION_PATTERNS:
            for m in pat.finditer(text):
                key = _normalize(m.group(1), m.group(2))
                index.setdefault(key, page_idx)
    return index


def resolve_visual_ref(ref: str | None, index: dict[str, int], fallback_page: int = 1) -> int:
    """Given a visual_ref string like 'Figure 1' or None, return a 1-based page index."""
    if not ref:
        return fallback_page
    # Accept 'Figure 1', 'figure 1', 'Fig 1', 'Fig. 1', 'Table 1', etc.
    m = re.match(r"(?i)(figure|fig\.?|table)\s*(\d+)", ref.strip())
    if not m:
        return fallback_page
    kind = "Figure" if m.group(1).lower().startswith("fig") else "Table"
    normalized = f"{kind} {int(m.group(2))}"
    return index.get(normalized, fallback_page)
