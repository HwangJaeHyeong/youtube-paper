"""AXIS-A monogram — palette study v4.

Same geometry as v3's AX1 (letter A made of three coordinate-axis strokes
meeting at a filled origin), but explored across modern colour systems.
The previous saturated tri-colour (amber + teal + crimson) read as dated
RGB-axis convention; this set leans on either monochrome with one pop
accent or a single shared gradient — the dominant 2020s logo idiom.

  P1 · Ink + Crimson Pop  — KU minimal: black axes, single crimson origin
  P2 · Indigo Gradient    — premium: shared indigo→violet gradient
  P3 · Linear Pink-Purple — Linear/Vercel style hero gradient
  P4 · Cool Teal Mono     — refined teal monochrome
  P5 · Warm Clay          — Korean modern: charcoal + terracotta on cream
  P6 · Electric Black     — pure ink + electric blue accent
"""
from __future__ import annotations

from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "logos" / "palettes"
OUT.mkdir(parents=True, exist_ok=True)


def axis_a_svg(left_color: str, right_color: str, cross_color: str,
               origin_color: str, defs: str = "",
               apex=(512, 220), bl=(260, 870), br=(764, 870),
               crossbar_y=660, stroke_w=58,
               bg: str | None = None) -> str:
    """Render the axis-A geometry with arbitrary colour assignments.

    Each parameter accepts a solid hex like '#000' or a paint reference
    like 'url(#grad-x)' — extra <defs> can be supplied via `defs`.
    """
    ax, ay = apex
    blx, bly = bl
    brx, bry = br
    t = (crossbar_y - ay) / (bly - ay)
    cl_x = ax + t * (blx - ax)
    cr_x = ax + t * (brx - ax)
    bg_rect = f'<rect width="1024" height="1024" fill="{bg}"/>' if bg else ""
    body = f"""
      {bg_rect}
      <line x1="{ax}" y1="{ay}" x2="{blx}" y2="{bly}"
            stroke="{left_color}" stroke-width="{stroke_w}" stroke-linecap="round"/>
      <line x1="{ax}" y1="{ay}" x2="{brx}" y2="{bry}"
            stroke="{right_color}" stroke-width="{stroke_w}" stroke-linecap="round"/>
      <line x1="{cl_x:.1f}" y1="{crossbar_y}" x2="{cr_x:.1f}" y2="{crossbar_y}"
            stroke="{cross_color}" stroke-width="{stroke_w}" stroke-linecap="round"/>
      <circle cx="{ax}" cy="{ay}" r="{stroke_w * 0.78:.1f}" fill="{origin_color}"/>
    """
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" '
        f'width="1024" height="1024">{defs}{body}</svg>'
    )


def write_pair(name: str, doc: str, bg_color: str = "#FFFFFF") -> Path:
    """Write SVG + PNG. PNG gets a solid bg colour for previewing on light/dark."""
    svg_path = OUT / f"{name}.svg"
    png_path = OUT / f"{name}.png"
    svg_path.write_text(doc, encoding="utf-8")
    cairosvg.svg2png(
        bytestring=doc.encode("utf-8"),
        write_to=str(png_path),
        output_width=2048, output_height=2048,
        background_color=bg_color,
    )
    print(f"  {svg_path.relative_to(ROOT)}  +  {png_path.relative_to(ROOT)}")
    return png_path


# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
def p1_ink_crimson():
    return axis_a_svg("#0A0A0A", "#0A0A0A", "#0A0A0A", "#862633"), "#FFFFFF"


def p2_indigo_gradient():
    defs = """
    <defs>
      <linearGradient id="g-indigo" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#6366F1"/>
        <stop offset="1" stop-color="#312E81"/>
      </linearGradient>
    </defs>"""
    grad = "url(#g-indigo)"
    return axis_a_svg(grad, grad, grad, "#1E1B4B", defs=defs), "#FFFFFF"


def p3_pink_purple():
    defs = """
    <defs>
      <linearGradient id="g-pp" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#A78BFA"/>
        <stop offset="0.55" stop-color="#EC4899"/>
        <stop offset="1" stop-color="#F472B6"/>
      </linearGradient>
    </defs>"""
    grad = "url(#g-pp)"
    return axis_a_svg(grad, grad, grad, "#1F1147", defs=defs), "#FFFFFF"


def p4_teal_mono():
    return axis_a_svg("#0E7490", "#0E7490", "#0E7490", "#083344"), "#FFFFFF"


def p5_warm_clay():
    return axis_a_svg("#262321", "#262321", "#262321", "#C8553D",
                      bg="#F5EFE7"), "#F5EFE7"


def p6_electric_black():
    return axis_a_svg("#0F0F0F", "#0F0F0F", "#0F0F0F", "#3B82F6"), "#FFFFFF"


# ---------------------------------------------------------------------------
# Contact sheet — light background tiles, with the actual palette bg under each
# ---------------------------------------------------------------------------
def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    search_dirs = [
        "/System/Library/Fonts/", "/System/Library/Fonts/Supplemental/",
        "/Library/Fonts/", str(Path.home() / "Library" / "Fonts"),
    ]
    for name in candidates:
        for d in search_dirs:
            p = Path(d) / name
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except OSError:
                    continue
    return ImageFont.load_default()


def build_contact_sheet(paths: list[Path], labels: list[str],
                        bgs: list[str], out_path: Path) -> None:
    cell, pad, label_h, title_h = 700, 40, 60, 100
    cols, rows = 3, 2
    width = cols * cell + (cols + 1) * pad
    height = title_h + rows * (cell + label_h) + (rows + 1) * pad
    canvas = Image.new("RGB", (width, height), color="#FAFAF7")
    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 44)
    label_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 26)
    draw.text((width // 2, title_h // 2),
              "AXIS-A — palette options",
              font=title_font, fill="#0A0A0A", anchor="mm")
    for i, (p, label, bg) in enumerate(zip(paths, labels, bgs)):
        col = i % cols
        row = i // cols
        x = pad + col * (cell + pad)
        y = title_h + pad + row * (cell + label_h + pad)
        # paint the per-tile bg first
        draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=bg, outline="#D8D8D8", width=2)
        img = Image.open(p).convert("RGBA").resize((cell, cell), Image.LANCZOS)
        canvas.paste(img, (x, y), img)
        draw.text((x + cell // 2, y + cell + label_h // 2), label,
                  font=label_font, fill="#0A0A0A", anchor="mm")
    canvas.save(out_path, "PNG")


def main() -> None:
    print("Generating AXIS-A palette options ...")
    palettes = [
        ("p1_ink_crimson",   p1_ink_crimson,   "P1 · Ink + Crimson Pop"),
        ("p2_indigo",        p2_indigo_gradient,"P2 · Indigo Gradient"),
        ("p3_pink_purple",   p3_pink_purple,   "P3 · Pink–Purple Gradient"),
        ("p4_teal_mono",     p4_teal_mono,     "P4 · Teal Mono"),
        ("p5_warm_clay",     p5_warm_clay,     "P5 · Warm Clay (cream bg)"),
        ("p6_electric",      p6_electric_black,"P6 · Ink + Electric Blue"),
    ]
    paths, labels, bgs = [], [], []
    for slug, fn, label in palettes:
        doc, bg = fn()
        paths.append(write_pair(f"axis_a_{slug}", doc, bg_color=bg))
        labels.append(label)
        bgs.append(bg)
    build_contact_sheet(paths, labels, bgs, OUT / "_palette_contact_sheet.png")
    print(f"  contact sheet → {(OUT / '_palette_contact_sheet.png').relative_to(ROOT)}")
    print("done.")


if __name__ == "__main__":
    main()
