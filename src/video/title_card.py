"""Generate fallback cover and clickbait-style title cards.

The title card is the first 1~2 seconds of every shorts — effectively the
in-feed thumbnail. It needs to read like a tabloid headline: bold, high-contrast,
numbers in an accent color so the eye stops on them.
"""
from __future__ import annotations

import re as _re
import textwrap
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from src.config import SHORTS_RESOLUTION

_BOLD_FONT = r"C:\Windows\Fonts\malgunbd.ttf"
_REG_FONT = r"C:\Windows\Fonts\malgun.ttf"
_ACCENT = (255, 215, 0)       # yellow — for numbers / key fragments
_FG = (250, 250, 252)         # near-white main text
_PAREN_FG = (180, 200, 255)   # cool blue — paper name tag
_BG_TOP = (8, 10, 18)         # near-black gradient top
_BG_BOTTOM = (28, 18, 40)     # plum gradient bottom


def render_cover(out_png: Path, size: tuple[int, int] = SHORTS_RESOLUTION, color: tuple[int, int, int] = (20, 22, 30)) -> Path:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(out_png, "PNG")
    return out_png


def _gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    w, h = size
    base = Image.new("RGB", size, top)
    grad = Image.new("L", (1, h))
    for y in range(h):
        grad.putpixel((0, y), int(255 * (y / max(1, h - 1))))
    grad = grad.resize(size)
    overlay = Image.new("RGB", size, bottom)
    return Image.composite(overlay, base, grad)


def _load_font(path: str, size_pt: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size_pt)
    except OSError:
        return ImageFont.load_default()


def _draw_text_with_stroke(draw: ImageDraw.ImageDraw, xy, text, font, fill, stroke_w=4, stroke_fill=(0, 0, 0)):
    draw.text(xy, text, font=font, fill=fill, stroke_width=stroke_w, stroke_fill=stroke_fill)


_NUM_RE = _re.compile(r"(\d+(?:[.,]\d+)?[%배]?|[A-Za-z]{2,}-?\d+|GPT-?\d|\d+x|\d+분|\d+초|\d+달러|\$\d+)")
_BOLD_RE = _re.compile(r"\*\*(.+?)\*\*")


def _strip_markdown(text: str) -> tuple[str, list[tuple[int, int]]]:
    """Strip **bold** markers, return (cleaned_text, [(start,end)] highlight ranges in cleaned)."""
    out = []
    spans: list[tuple[int, int]] = []
    i = 0
    cleaned_pos = 0
    while i < len(text):
        m = _BOLD_RE.match(text, i)
        if m:
            inner = m.group(1)
            out.append(inner)
            spans.append((cleaned_pos, cleaned_pos + len(inner)))
            cleaned_pos += len(inner)
            i = m.end()
        else:
            out.append(text[i])
            cleaned_pos += 1
            i += 1
    return "".join(out), spans


def _split_for_highlight(line: str, abs_offset: int = 0, bold_ranges: list[tuple[int, int]] | None = None) -> list[tuple[str, bool]]:
    """Split a line into (segment, is_highlight). Auto-numbers + bold ranges (in absolute coord)."""
    auto_ranges = [(m.start() + abs_offset, m.end() + abs_offset) for m in _NUM_RE.finditer(line)]
    explicit = []
    if bold_ranges:
        # Translate bold ranges (absolute) -> overlap with this line's [abs_offset, abs_offset+len(line))
        line_end = abs_offset + len(line)
        for s, e in bold_ranges:
            if e <= abs_offset or s >= line_end:
                continue
            explicit.append((max(s, abs_offset), min(e, line_end)))
    all_ranges = sorted(auto_ranges + explicit)
    merged: list[tuple[int, int]] = []
    for s, e in all_ranges:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    parts: list[tuple[str, bool]] = []
    pos = abs_offset
    for s, e in merged:
        if s > pos:
            parts.append((line[pos - abs_offset:s - abs_offset], False))
        parts.append((line[s - abs_offset:e - abs_offset], True))
        pos = e
    if pos < abs_offset + len(line):
        parts.append((line[pos - abs_offset:], False))
    return parts or [(line, False)]


def render_header_strip(
    title: str,
    out_png: Path,
    width: int = 1080,
    height: int = 180,
    font_size: int = 56,
) -> Path:
    """Transparent header strip with title text (black-stroked) for overlay."""
    # Strip markdown bold markers — they should not appear in the header text.
    title = title.replace("**", "")
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(_BOLD_FONT, font_size)
    except OSError:
        font = ImageFont.load_default()
    # Auto-shrink if line is too wide
    while font.size > 28 and draw.textbbox((0, 0), title, font=font, stroke_width=6)[2] > int(width * 0.94):
        font = ImageFont.truetype(_BOLD_FONT, font.size - 4)
    bbox = draw.textbbox((0, 0), title, font=font, stroke_width=6)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (width - tw) // 2
    y = (height - th) // 2
    draw.text((x, y), title, font=font, fill=_FG, stroke_width=6, stroke_fill=(0, 0, 0))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG")
    return out_png


def render_title_card(
    title: str,
    out_png: Path,
    size: tuple[int, int] = SHORTS_RESOLUTION,
    bg: tuple[int, int, int] | None = None,
    fg: tuple[int, int, int] = _FG,
    teaser_path: Path | None = None,
    teaser_alpha: float = 0.55,
) -> Path:
    """Clickbait-style: gradient bg, bold heading, accent-colored numbers, smaller paper tag.

    If `teaser_path` is given, the teaser image is composited behind everything as a
    low-opacity backdrop (defocuses + tints with the gradient).
    """
    w, h = size
    img = _gradient(size, _BG_TOP, _BG_BOTTOM)

    # Optional teaser as semi-transparent backdrop motif (~80% of frame width).
    # White-ish background pixels are keyed to transparent so only the subject
    # blends with the gradient (no visible photo rectangle).
    if teaser_path and Path(teaser_path).exists():
        teaser_src = Image.open(teaser_path).convert("RGBA")
        target_w = int(w * 0.8)
        scale = target_w / teaser_src.width
        teaser_src = teaser_src.resize(
            (target_w, int(teaser_src.height * scale)), Image.LANCZOS
        )
        # Build alpha mask: if image has no real alpha, key out near-white background.
        r, g, b, a = teaser_src.split()
        if a.getextrema() == (255, 255):
            # Per-pixel min RGB; lower = darker (closer to subject), higher = closer to white
            min_rgb = ImageChops.darker(ImageChops.darker(r, g), b)
            # invert + linearly amplify: make darker pixels opaque, near-white transparent.
            inv = ImageChops.invert(min_rgb)  # 255 = was black, 0 = was white
            a = inv.point(lambda v: 0 if v < 10 else min(255, (v - 10) * 6))
        # Place teaser onto a transparent layer
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        x = (w - teaser_src.width) // 2
        y = (h - teaser_src.height) // 2
        rgb = Image.merge("RGB", (r, g, b))
        layer.paste(rgb, (x, y), a)
        # Blur for depth-of-field
        layer = layer.filter(ImageFilter.GaussianBlur(8))
        # Apply teaser_alpha by scaling the alpha channel
        la = layer.split()[3].point(lambda v: int(v * teaser_alpha))
        layer.putalpha(la)
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")

    # Subtle vignette to focus eye on text
    vignette = Image.new("L", size, 0)
    vd = ImageDraw.Draw(vignette)
    cx, cy = w // 2, h // 2
    vd.ellipse([cx - w * 0.7, cy - h * 0.55, cx + w * 0.7, cy + h * 0.55], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(180))
    overlay = Image.new("RGB", size, _BG_TOP)
    img = Image.composite(img, overlay, vignette)

    draw = ImageDraw.Draw(img)
    target_w = int(w * 0.88)

    # Split: head (loud headline) + (paper tag). Strip **bold** markers, keep ranges.
    m = _re.match(r"^(.*?)\s*(\([^)]+\))\s*$", title)
    if m:
        head_raw, paren = m.group(1).strip(), m.group(2).strip()
    else:
        head_raw, paren = title.strip(), ""
    head, bold_ranges = _strip_markdown(head_raw)

    # Find best font size + wrap for the head.
    def _fit_head() -> tuple[ImageFont.FreeTypeFont, list[str]]:
        base = 96 if w < h else 76
        for size_pt in range(base, 44, -4):
            f = _load_font(_BOLD_FONT, size_pt)
            for wrap_chars in range(7, 22):
                lines = textwrap.wrap(head, width=wrap_chars, break_long_words=True) or [head]
                widths = [draw.textbbox((0, 0), ln, font=f, stroke_width=4)[2] for ln in lines]
                if widths and max(widths) <= target_w and len(lines) <= 4:
                    return f, lines
        return _load_font(_BOLD_FONT, 44), textwrap.wrap(head, width=10, break_long_words=True) or [head]

    head_font, head_lines = _fit_head()
    head_lh = head_font.size + 14
    paren_font_size = max(34, head_font.size - 24)
    paren_font = _load_font(_REG_FONT, paren_font_size)

    # Layout: head block centered vertically, paren slightly below head block.
    paren_h = paren_font.size + 8 if paren else 0
    total_h = head_lh * len(head_lines) + (paren_h + 30 if paren else 0)
    y = (h - total_h) // 2

    # Compute absolute char offset of each wrapped line in the cleaned head string.
    line_offsets: list[int] = []
    cursor = 0
    for ln in head_lines:
        idx = head.find(ln, cursor)
        if idx < 0:
            idx = cursor
        line_offsets.append(idx)
        cursor = idx + len(ln)

    for ln, line_off in zip(head_lines, line_offsets):
        segs = _split_for_highlight(ln, abs_offset=line_off, bold_ranges=bold_ranges)
        seg_widths = [draw.textbbox((0, 0), s, font=head_font, stroke_width=4)[2] for s, _ in segs]
        total_w = sum(seg_widths)
        x = (w - total_w) // 2
        for (segment, is_hl), sw in zip(segs, seg_widths):
            color = _ACCENT if is_hl else fg
            _draw_text_with_stroke(draw, (x, y), segment, head_font, color, stroke_w=5)
            x += sw
        y += head_lh

    if paren:
        y += 30
        bbox = draw.textbbox((0, 0), paren, font=paren_font, stroke_width=2)
        pw = bbox[2] - bbox[0]
        px = (w - pw) // 2
        _draw_text_with_stroke(draw, (px, y), paren, paren_font, _PAREN_FG, stroke_w=2)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG")
    return out_png
