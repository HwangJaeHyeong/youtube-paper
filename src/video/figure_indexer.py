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
# STRICT caption patterns (unambiguous: Nature pipe, colon, ISSCC session form).
# Body references like "as shown in Fig. 2," cannot match these.
_STRICT_PATTERNS = [
    # ISSCC session-based ("Figure 31.5.1:") — last component is canonical.
    re.compile(r"(?i)\b(figure|fig\.)\s*\d+\.\d+\.(\d+)\s*[:.]"),
    # Nature pipe ("Fig. 1 | Title...")
    re.compile(r"(?i)\b(figure|fig\.)\s*(\d+)\s*\|"),
    # Colon ("Figure 1: Title", CHI/ACM/IEEE)
    re.compile(r"(?i)\b(figure|fig\.)\s*(\d+)\s*:"),
    re.compile(r"(?i)\b(table)\s*(\d+)\s*[:|]"),
]
# LOOSE patterns — period after the number. Captures real captions in some
# IEEE styles but ALSO catches sentence-ending body references. Used only as
# a fallback when strict patterns produced no hit for a given key.
_LOOSE_PATTERNS = [
    re.compile(r"(?i)\b(figure|fig\.)\s*(\d+)\s*\."),
    re.compile(r"(?i)\b(table)\s*(\d+)\s*\."),
]


def _normalize(kind: str, number: str) -> str:
    k = kind.lower()
    if k in ("figure", "fig."):
        return f"Figure {int(number)}"
    if k == "table":
        return f"Table {int(number)}"
    return f"{k.capitalize()} {int(number)}"


def build_index(pdf_path: Path) -> dict[str, int]:
    """Return {'Figure 1': page_idx_1_based, ...}. Strict captions win over body refs.

    Two-pass: first scan every page for unambiguous caption forms (pipe / colon /
    ISSCC). Only when no strict match was found for a given key does the loose
    period-pattern fill in. This avoids indexing body sentences ("...as shown in
    Fig. 2.") as caption locations.
    """
    reader = PdfReader(str(pdf_path))
    pages_text = [(i, p.extract_text() or "") for i, p in enumerate(reader.pages, start=1)]
    index: dict[str, int] = {}
    for pat in _STRICT_PATTERNS:
        for page_idx, text in pages_text:
            for m in pat.finditer(text):
                key = _normalize(m.group(1), m.group(2))
                index.setdefault(key, page_idx)
    for pat in _LOOSE_PATTERNS:
        for page_idx, text in pages_text:
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
