"""Crop Figure/Table regions out of a paper PDF using text-block boundaries.

Heuristic:
- Find the caption text line ("Figure N:" / "Table N:").
- For figures: crop spans from the END of the closest text block ABOVE the caption
  to the BOTTOM of the caption itself.
- For tables: crop spans from the TOP of the caption to the START of the closest
  text block BELOW the caption.
- Falls back to whole page only when the caption can't be located.

Renders at 300 DPI so the crop survives upscaling to 1080x1920 when shown.
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz  # pymupdf


def _find_caption_rect(page: fitz.Page, ref: str) -> fitz.Rect | None:
    # ref looks like "Figure 1" or "Table 2".
    # Try standard punctuation, Nature pipe format, and short "Fig. N" variant.
    short = ref.replace("Figure", "Fig.")
    variants = [
        f"{ref}:", f"{ref}.", f"{ref} |",
        f"{short}:", f"{short}.", f"{short} |",
        ref, short,
    ]
    for variant in variants:
        rects = page.search_for(variant)
        if rects:
            return rects[0]
    return None


def _text_blocks(page: fitz.Page) -> list[tuple[float, float, float, float, str]]:
    """Return (x0, y0, x1, y1, text) tuples for text blocks only."""
    blocks = []
    for b in page.get_text("blocks"):
        # b: (x0, y0, x1, y1, text, block_no, block_type)
        if len(b) >= 7 and b[6] == 0:  # text block
            txt = (b[4] or "").strip()
            if txt:
                blocks.append((b[0], b[1], b[2], b[3], txt))
    return blocks


def crop_visual(pdf_path: Path, page_idx_1based: int, ref: str, out_png: Path, dpi: int = 300) -> Path:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    try:
        page = doc[page_idx_1based - 1]
        page_rect = page.rect
        cap = _find_caption_rect(page, ref)

        if cap is None:
            page.get_pixmap(dpi=dpi).save(str(out_png))
            return out_png

        blocks = _text_blocks(page)
        is_table = ref.lower().startswith("table")

        # Max visual extent — keep crops tight instead of whole-page by accident.
        max_h = page_rect.height * 0.55

        # Detect the left margin (most common x0 across all text blocks — body text).
        if blocks:
            xs = [round(b[0]) for b in blocks]
            left_margin = min(xs)
        else:
            left_margin = page_rect.x0

        if is_table:
            # Table cells are typically indented (x0 > left_margin). Body paragraphs
            # start at x0 ≈ left_margin. Walk blocks after caption; the first block
            # that looks like body text (x0 close to left_margin AND wider) marks the
            # end of the table. Gap > 20pt is a secondary signal.
            candidates = sorted([b for b in blocks if b[1] > cap.y1 + 3], key=lambda b: b[1])
            table_end = cap.y1 + max_h
            prev_y1 = cap.y1
            for b in candidates:
                gap = b[1] - prev_y1
                width = b[2] - b[0]
                is_body = b[0] <= left_margin + 4 and width > 300
                if is_body or gap > 24:
                    table_end = b[1] - 4
                    break
                prev_y1 = max(prev_y1, b[3])
            top = max(page_rect.y0, cap.y0 - 2)
            bottom = min(page_rect.y1, table_end, top + max_h)
        else:
            # figure above caption; find last text block ending ABOVE caption start.
            above = [b for b in blocks if b[3] < cap.y0 - 3]
            above.sort(key=lambda b: b[3], reverse=True)
            prev_bottom = above[0][3] if above else cap.y0 - max_h
            bottom = min(page_rect.y1, cap.y1 + 4)
            top = max(page_rect.y0, prev_bottom + 4, bottom - max_h)

        # margin trim sides (LaTeX margins)
        x0 = page_rect.x0 + 10
        x1 = page_rect.x1 - 10
        crop = fitz.Rect(x0, top, x1, bottom)

        if crop.height < 80 or crop.width < 80:
            # fall back to whole page
            page.get_pixmap(dpi=dpi).save(str(out_png))
            return out_png

        page.get_pixmap(dpi=dpi, clip=crop).save(str(out_png))
        return out_png
    finally:
        doc.close()


_REF_RE = re.compile(r"(?i)(figure|fig\.?|table)\s*(\d+)")


def normalize_ref(ref: str | None) -> str | None:
    """Pull a 'Figure N' or 'Table N' token out of a possibly messy ref string.

    Uses `search` (not `match`) so creative refs like
    "iPhone vibration patterns + Figure 1 (teaser overlay)" still resolve.
    """
    if not ref:
        return None
    if ref == "__TITLE__":
        return "__TITLE__"
    if ref.startswith("scene_"):
        return ref
    m = _REF_RE.search(ref)
    if not m:
        return None
    kind = "Figure" if m.group(1).lower().startswith("fig") else "Table"
    return f"{kind} {int(m.group(2))}"
