"""Generate keyword/concept background cards for shorts when no figure exists.

Each card is a 1080x1920 vertical PNG with:
- A bold accent keyword anchored in the upper third (y≈260-560)
- Themed gradient/decoration filling the rest
- Vertical center kept visually calm for the hype-style subtitle (an5)
- Bottom area reserved (the subtitle bar + footer overlay land there)
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.config import SHORTS_RESOLUTION
from src.video.title_card import _HEADER_FONT_CANDIDATES, _gradient


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in _HEADER_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_with_stroke(draw, xy, text, font, fill, stroke=6, stroke_fill=(0, 0, 0)):
    draw.text(xy, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)


def _wrap(text: str, font, max_w: int, draw) -> list[str]:
    """Greedy word-wrap that handles Korean (no spaces fallback)."""
    words = text.split()
    if not words:
        return [text]
    lines, cur = [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), cand, font=font)
        if bbox[2] - bbox[0] <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    # If a single chunk still overruns max_w, hard-break by char (Korean fallback)
    final = []
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        if bbox[2] - bbox[0] <= max_w:
            final.append(ln)
            continue
        buf = ""
        for ch in ln:
            cand = buf + ch
            bb = draw.textbbox((0, 0), cand, font=font)
            if bb[2] - bb[0] > max_w and buf:
                final.append(buf)
                buf = ch
            else:
                buf = cand
        if buf:
            final.append(buf)
    return final


def _add_grain(img: Image.Image, amount: int = 8) -> Image.Image:
    """Subtle film grain so flat gradients don't look like cheap stock."""
    w, h = img.size
    noise = Image.effect_noise((w, h), amount).convert("L")
    noise = noise.filter(ImageFilter.GaussianBlur(0.6))
    layer = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(img, layer, 0.06)


def _decorate_corner_glow(img: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    """Soft radial glow in upper area to push focus toward keyword text."""
    w, h = img.size
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = w // 2, int(h * 0.36)
    for r in range(420, 60, -40):
        alpha = int(255 * (1 - (r - 60) / (420 - 60)))
        gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=tuple(min(255, c + alpha // 4) for c in color))
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    return Image.blend(img, glow, 0.45)


def render_concept(
    keyword: str,
    out_png: Path,
    *,
    bg_top: tuple[int, int, int] = (10, 12, 24),
    bg_bottom: tuple[int, int, int] = (38, 14, 48),
    accent: tuple[int, int, int] = (255, 215, 0),
    glow: tuple[int, int, int] | None = None,
    size: tuple[int, int] = SHORTS_RESOLUTION,
    seed: int = 0,
) -> Path:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    w, h = size
    img = _gradient(size, bg_top, bg_bottom)
    if glow is not None:
        img = _decorate_corner_glow(img, glow)
    img = _add_grain(img, amount=10)

    draw = ImageDraw.Draw(img)

    # Pick font size so it fits in ~85% width across at most 2 lines.
    # Cap at 140pt for 2-line cases so keyword block ends well above the
    # subtitle band (subtitle renders middle-center around y≈830-1080).
    max_text_w = int(w * 0.86)
    target_size = 180
    while target_size >= 80:
        font = _font(target_size)
        lines = _wrap(keyword, font, max_text_w, draw)
        if len(lines) <= 2:
            if all(draw.textbbox((0, 0), ln, font=font)[2] - draw.textbbox((0, 0), ln, font=font)[0] <= max_text_w for ln in lines):
                if len(lines) == 2 and target_size > 140:
                    target_size = 140  # force tighter font for 2-line keywords
                    continue
                break
        target_size -= 10
    font = _font(target_size)
    lines = _wrap(keyword, font, max_text_w, draw)

    # Keyword anchored below the header strip (header bottom ≈ y=410) and
    # above the subtitle band (subtitle starts ≈ y=830).
    line_h = int(target_size * 1.18)
    y0 = int(h * 0.30) if len(lines) == 1 else int(h * 0.26)
    for i, ln in enumerate(lines):
        bb = draw.textbbox((0, 0), ln, font=font)
        tw = bb[2] - bb[0]
        x = (w - tw) // 2
        y = y0 + i * line_h
        _draw_with_stroke(draw, (x, y), ln, font, fill=accent, stroke=8, stroke_fill=(0, 0, 0))

    # Decorative dotted stripe near bottom (purely aesthetic, well below subtitle line)
    rng = random.Random(seed)
    stripe_y = int(h * 0.86)
    for _ in range(36):
        cx = rng.randint(40, w - 40)
        cy = stripe_y + rng.randint(-18, 18)
        rd = rng.randint(2, 6)
        col = tuple(min(255, c + rng.randint(20, 60)) for c in bg_bottom)
        draw.ellipse((cx - rd, cy - rd, cx + rd, cy + rd), fill=col)

    img.save(out_png, "PNG")
    return out_png
