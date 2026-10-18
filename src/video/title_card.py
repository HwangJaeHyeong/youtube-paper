"""Generate fallback cover and clickbait-style title cards.

The title card is the first 1~2 seconds of every shorts — effectively the
in-feed thumbnail. It needs to read like a tabloid headline: bold, high-contrast,
numbers in an accent color so the eye stops on them.
"""
from __future__ import annotations

import re as _re
import os
import textwrap
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from src.config import SHORTS_RESOLUTION

_BOLD_FONT = os.getenv("FONT_BOLD", r"C:\Windows\Fonts\malgunbd.ttf")
_REG_FONT = os.getenv("FONT_REG", r"C:\Windows\Fonts\malgun.ttf")
# macOS / cross-platform Pretendard Black for the header title strip.
_HEADER_FONT_CANDIDATES = [
    "/Library/Fonts/Pretendard-Black.otf",
    "/Users/jaehyeong/Library/Fonts/Pretendard-Black.otf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    r"C:\Windows\Fonts\malgunbd.ttf",
    "/usr/share/fonts/pretendard/Pretendard-Black.otf",  # Docker
]


def _load_header_font(size_pt: int) -> ImageFont.FreeTypeFont:
    for path in _HEADER_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size_pt)
        except OSError:
            continue
    return ImageFont.load_default()
_ACCENT = (255, 215, 0)       # yellow — for numbers / key fragments
_FG = (250, 250, 252)         # near-white main text
_PAREN_FG = (180, 200, 255)   # cool blue — paper name tag
_BG_TOP = (8, 10, 18)         # near-black gradient top
_BG_BOTTOM = (28, 18, 40)     # plum gradient bottom


def render_cover(
    out_png: Path,
    size: tuple[int, int] = SHORTS_RESOLUTION,
    color: tuple[int, int, int] = (20, 22, 30),
    hero_png: Path | None = None,
) -> Path:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    bg = _gradient(size, _BG_TOP, _BG_BOTTOM)
    if hero_png and hero_png.exists():
        hero = Image.open(hero_png).convert("RGBA")
        # Fit hero to ~85% of frame width, center vertically.
        target_w = int(size[0] * 0.85)
        ratio = target_w / hero.width
        target_h = int(hero.height * ratio)
        # Cap height to ~55% of frame so subtitles remain readable.
        max_h = int(size[1] * 0.55)
        if target_h > max_h:
            target_h = max_h
            target_w = int(hero.width * (target_h / hero.height))
        hero = hero.resize((target_w, target_h), Image.LANCZOS)
        x = (size[0] - target_w) // 2
        y = (size[1] - target_h) // 2
        # Soft darkening overlay underneath subtitle band (bottom 30%).
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rectangle([0, int(size[1] * 0.7), size[0], size[1]], fill=(0, 0, 0, 140))
        bg = bg.convert("RGBA")
        bg.paste(hero, (x, y), hero if hero.mode == "RGBA" else None)
        bg = Image.alpha_composite(bg, overlay).convert("RGB")
    bg.save(out_png, "PNG")
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
    height: int = 360,
    font_size: int = 96,
) -> Path:
    """Transparent header strip for the top of YouTube Shorts.

    - **bold** markers in the title render in accent yellow (rest is white).
    - Explicit `\\n` in the title is honored as a line break; otherwise word-wraps.
    - Pretendard Black with thick black outline. Sized for the YT Shorts top
      safe-zone (stays clear of YouTube's top UI bar).
    """
    head_clean, bold_ranges = _strip_markdown(title.strip())
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    target_w = int(width * 0.94)
    stroke_w = 8

    explicit_lines = (
        [ln.strip() for ln in head_clean.split("\n") if ln.strip()]
        if "\n" in head_clean else None
    )

    chosen_font: ImageFont.FreeTypeFont | None = None
    chosen_lines: list[str] = []
    chosen_fonts: list[ImageFont.FreeTypeFont] = []
    if explicit_lines is not None:
        # Fit each explicit line independently so a short first line can render
        # large even when later lines are long.
        chosen_lines = explicit_lines
        for ln in explicit_lines:
            sel: ImageFont.FreeTypeFont | None = None
            for size_pt in range(144, 38, -3):
                f = _load_header_font(size_pt)
                w = draw.textbbox((0, 0), ln, font=f, stroke_width=stroke_w)[2]
                if w <= target_w:
                    sel = f
                    break
            chosen_fonts.append(sel or _load_header_font(38))
        chosen_font = chosen_fonts[0]
    else:
        for size_pt in range(font_size, 38, -3):
            f = _load_header_font(size_pt)
            # Try 1, 2, then 3 lines via word-aware wrap; pick smallest fit.
            for max_lines in (1, 2, 3):
                fitted = False
                for wrap_chars in range(8, 32):
                    lines = textwrap.wrap(head_clean, width=wrap_chars, break_long_words=False) or [head_clean]
                    if len(lines) > max_lines:
                        continue
                    widths = [draw.textbbox((0, 0), ln, font=f, stroke_width=stroke_w)[2] for ln in lines]
                    if max(widths) <= target_w:
                        chosen_font, chosen_lines = f, lines
                        fitted = True
                        break
                if fitted:
                    break
            if chosen_font:
                break
        if chosen_font is None:
            chosen_font = _load_header_font(42)
            chosen_lines = textwrap.wrap(head_clean, width=14, break_long_words=False) or [head_clean]
        chosen_fonts = [chosen_font] * len(chosen_lines)

    # Map each rendered line to its char offset in head_clean (for highlight ranges).
    line_offsets: list[int] = []
    cursor = 0
    for ln in chosen_lines:
        idx = head_clean.find(ln, cursor)
        if idx < 0:
            idx = cursor
        line_offsets.append(idx)
        cursor = idx + len(ln)

    line_heights = [f.size + 18 for f in chosen_fonts]
    total_h = sum(line_heights)
    y0 = (height - total_h) // 2

    y_cur = y0
    for i, (line, line_off, font, lh) in enumerate(zip(chosen_lines, line_offsets, chosen_fonts, line_heights)):
        segs = _split_for_highlight(line, abs_offset=line_off, bold_ranges=bold_ranges)
        seg_widths = [draw.textbbox((0, 0), s, font=font, stroke_width=stroke_w)[2] for s, _ in segs]
        total_w = sum(seg_widths)
        x = (width - total_w) // 2
        y = y_cur
        for (segment, is_hl), sw in zip(segs, seg_widths):
            color = _ACCENT if is_hl else (255, 255, 255)
            draw.text((x, y), segment, font=font, fill=color,
                      stroke_width=stroke_w, stroke_fill=(0, 0, 0))
            x += sw
        y_cur += lh

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG")
    return out_png


def render_footer_strip(
    text: str,
    out_png: Path,
    width: int = 1080,
    height: int = 110,
    font_size: int = 56,
) -> Path:
    """Transparent footer strip for the bottom of YouTube Shorts.

    Single-line CTA-style line. **bold** markers render in accent yellow.
    Designed to sit ABOVE the YT Shorts bottom UI (description + buttons),
    typically overlaid at y≈1480 on a 1920-tall frame.
    """
    head_clean, bold_ranges = _strip_markdown(text.strip())
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    target_w = int(width * 0.92)
    stroke_w = 6

    chosen_font: ImageFont.FreeTypeFont | None = None
    for size_pt in range(font_size, 28, -2):
        f = _load_header_font(size_pt)
        if draw.textbbox((0, 0), head_clean, font=f, stroke_width=stroke_w)[2] <= target_w:
            chosen_font = f
            break
    if chosen_font is None:
        chosen_font = _load_header_font(28)

    segs = _split_for_highlight(head_clean, abs_offset=0, bold_ranges=bold_ranges)
    seg_widths = [draw.textbbox((0, 0), s, font=chosen_font, stroke_width=stroke_w)[2] for s, _ in segs]
    total_w = sum(seg_widths)
    bbox = draw.textbbox((0, 0), head_clean, font=chosen_font, stroke_width=stroke_w)
    text_h = bbox[3] - bbox[1]
    x = (width - total_w) // 2
    y = (height - text_h) // 2 - bbox[1]
    for (segment, is_hl), sw in zip(segs, seg_widths):
        color = _ACCENT if is_hl else (255, 255, 255)
        draw.text((x, y), segment, font=chosen_font, fill=color,
                  stroke_width=stroke_w, stroke_fill=(0, 0, 0))
        x += sw

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
    teaser_alpha: float = 0.92,
) -> Path:
    """Clickbait-style: gradient bg, bold heading, accent-colored numbers, smaller paper tag.

    If `teaser_path` is given, the teaser image is composited as a clearly visible
    hero (sharp, near-opaque) behind the title text.
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
