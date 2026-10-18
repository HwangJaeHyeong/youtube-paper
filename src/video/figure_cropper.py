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
    """Locate the actual caption (not body-text references like "as shown in Fig. 1,").

    Strategy: try caption-distinctive patterns first ("|" then ":" then ".") and
    short out as soon as one yields hits. When multiple hits remain (e.g. several
    "Fig. 1" mentions on the same page), pick the one with the largest cluster of
    drawings/images directly adjacent — that's the real caption next to the figure.
    """
    short = ref.replace("Figure", "Fig.")
    is_table = ref.lower().startswith("table")

    # Patterns ordered by caption-distinctiveness.
    pattern_groups = [
        [f"{ref} |", f"{short} |"],   # Nature-style pipe — strongest signal
        [f"{ref}:", f"{short}:"],     # CHI/ACM/IEEE colon caption
        [f"{ref}.", f"{short}."],     # period — caption OR body ref, ambiguous
        [ref, short],                  # bare — last resort
    ]

    candidates: list[fitz.Rect] = []
    for group in pattern_groups:
        for variant in group:
            for r in page.search_for(variant):
                candidates.append(r)
        if candidates:
            break  # use the most distinctive group that hit anything

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Multiple matches → score by visual mass adjacent in the expected direction.
    visuals = _visual_rects(page)

    def score(rect: fitz.Rect) -> float:
        if is_table:
            adj = [v for v in visuals if v.y0 >= rect.y1 - 2 and v.y0 < rect.y1 + 250]
        else:
            adj = [v for v in visuals if v.y1 <= rect.y0 + 2 and v.y1 > rect.y0 - 250]
        return sum(v.width * v.height for v in adj)

    return max(candidates, key=score)


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


def _visual_rects(page: fitz.Page) -> list[fitz.Rect]:
    """Bounding rects of every drawing path + raster image on the page.

    These are the actual graphical elements (lines, shapes, photos) — far more
    accurate than guessing a figure's extent from surrounding text-block gaps.
    """
    rects: list[fitz.Rect] = []
    for d in page.get_drawings():
        r = d.get("rect")
        if r is not None and r.width > 1 and r.height > 1:
            rects.append(fitz.Rect(r))
    for info in page.get_image_info():
        bbox = info.get("bbox")
        if bbox:
            r = fitz.Rect(bbox)
            if r.width > 1 and r.height > 1:
                rects.append(r)
    return rects


def _cluster_visuals_near(
    visuals: list[fitz.Rect],
    cap: fitz.Rect,
    page_rect: fitz.Rect,
    direction: str,
    other_caps: list[fitz.Rect],
) -> fitz.Rect | None:
    """Walk visuals from the caption outward, growing a cluster while gaps are small.

    `direction='up'` for figures (caption below the figure), `'down'` for tables.
    Stops if it would cross another caption's rect (so adjacent figures don't merge).
    """
    if not visuals:
        return None

    # Block any region beyond a competing caption.
    if direction == "up":
        blockers = [c for c in other_caps if c.y1 < cap.y0 - 3]
        upper_limit = max((c.y1 for c in blockers), default=page_rect.y0)
        candidates = [v for v in visuals if v.y1 <= cap.y0 + 2 and v.y0 >= upper_limit - 2]
        candidates.sort(key=lambda r: r.y1, reverse=True)  # closest to caption first
        boundary = cap.y0
        cluster: list[fitz.Rect] = []
        for v in candidates:
            gap = boundary - v.y1
            if gap > 40 and cluster:  # too far from current cluster -> stop
                break
            cluster.append(v)
            boundary = min(boundary, v.y0)
    else:
        blockers = [c for c in other_caps if c.y0 > cap.y1 + 3]
        lower_limit = min((c.y0 for c in blockers), default=page_rect.y1)
        candidates = [v for v in visuals if v.y0 >= cap.y1 - 2 and v.y1 <= lower_limit + 2]
        candidates.sort(key=lambda r: r.y0)  # closest to caption first
        boundary = cap.y1
        cluster = []
        for v in candidates:
            gap = v.y0 - boundary
            if gap > 40 and cluster:
                break
            cluster.append(v)
            boundary = max(boundary, v.y1)

    if not cluster:
        return None

    # Bounding box of the cluster.
    x0 = min(v.x0 for v in cluster)
    y0 = min(v.y0 for v in cluster)
    x1 = max(v.x1 for v in cluster)
    y1 = max(v.y1 for v in cluster)
    return fitz.Rect(x0, y0, x1, y1)


def _all_caption_rects(page: fitz.Page) -> list[fitz.Rect]:
    """Find every Figure/Table caption rect on the page (used as boundaries).

    Pattern: capital-F/T word followed by digits and ':'/'.', e.g. 'Figure 2:'.
    """
    rects: list[fitz.Rect] = []
    text = page.get_text()
    for m in re.finditer(r"(?:Figure|Fig\.|Table)\s*\d+(?:\.\d+){0,2}\s*[:.|]", text):
        for r in page.search_for(m.group()):
            rects.append(r)
    return rects


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

        is_table = ref.lower().startswith("table")
        visuals = _visual_rects(page)
        all_caps = [r for r in _all_caption_rects(page) if not r.intersects(cap)]

        crop: fitz.Rect | None = None
        if visuals:
            cluster = _cluster_visuals_near(
                visuals, cap, page_rect,
                direction="down" if is_table else "up",
                other_caps=all_caps,
            )
            if cluster is not None:
                # Expand the caption rect to its full text block so multi-line
                # captions ("Figure 1. Some long title that wraps to two lines.")
                # don't get cut off mid-sentence at the crop bottom.
                cap_full = cap
                for b in page.get_text("blocks"):
                    if len(b) < 7 or b[6] != 0:  # text blocks only
                        continue
                    bx0, by0, bx1, by1 = b[0], b[1], b[2], b[3]
                    if (bx0 - 1 <= cap.x0 and bx1 + 1 >= cap.x1
                            and by0 - 1 <= cap.y0 and by1 + 1 >= cap.y1):
                        cap_full = fitz.Rect(bx0, by0, bx1, by1)
                        break

                # Union the visual cluster with the (full) caption + small padding.
                pad = 6
                if is_table:
                    top = max(page_rect.y0, cap_full.y0 - pad)
                    bottom = min(page_rect.y1, cluster.y1 + pad)
                else:
                    top = max(page_rect.y0, cluster.y0 - pad)
                    bottom = min(page_rect.y1, cap_full.y1 + pad)
                # Horizontal extent: union the cluster span with the caption block.
                x0 = max(page_rect.x0, min(cluster.x0, cap_full.x0) - pad)
                x1 = min(page_rect.x1, max(cluster.x1, cap_full.x1) + pad)
                crop = fitz.Rect(x0, top, x1, bottom)

        # Fallback: text-block heuristic when no drawings/images were found
        # (rare; e.g. fully-vectorized PDFs without explicit drawing ops).
        if crop is None:
            blocks = _text_blocks(page)
            max_h = page_rect.height * 0.55
            if is_table:
                candidates = sorted([b for b in blocks if b[1] > cap.y1 + 3], key=lambda b: b[1])
                table_end = cap.y1 + max_h
                for b in candidates:
                    if b[1] - cap.y1 > 24:
                        table_end = b[1] - 4
                        break
                top = max(page_rect.y0, cap.y0 - 4)
                bottom = min(page_rect.y1, table_end)
            else:
                above = [b for b in blocks if b[3] < cap.y0 - 3]
                above.sort(key=lambda b: b[3], reverse=True)
                prev_bottom = above[0][3] if above else cap.y0 - max_h
                bottom = min(page_rect.y1, cap.y1 + 4)
                top = max(page_rect.y0, prev_bottom + 4)
            crop = fitz.Rect(page_rect.x0 + 10, top, page_rect.x1 - 10, bottom)

        if crop.height < 80 or crop.width < 80:
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
    if m:
        kind = "Figure" if m.group(1).lower().startswith("fig") else "Table"
        return f"{kind} {int(m.group(2))}"
    # External / user-supplied ref (e.g. "RNN", "CNN", "LLM_logos") — keep as-is.
    # Pipeline will look for crops/<ref>.png and use it if present.
    return ref.strip()
