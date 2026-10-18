"""Generate AXIS Lab (Korea University) logo concepts.

Outputs SVG + PNG (1024x1024 square mark, 2400x720 horizontal lockup) for
each concept variant into ``assets/logos/``.

Concepts mirror common Korean HCI lab visual identity (KAIST HCIL, KIXLAB,
SNU HCI Lab, HCI Tech): minimal wordmark + tight geometric symbol, mostly
mono-color or paired with the institutional accent.
"""
from __future__ import annotations

import math
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "logos"
OUT.mkdir(parents=True, exist_ok=True)

# Korea University crimson (official close approximation)
KU_CRIMSON = "#862633"
INK = "#0A0A0A"
DIM = "#5A5A5A"
LIGHT = "#C8C8C8"

FULL_NAME = "Augmented eXperience and Interactive Systems"
INSTITUTION = "Korea University"

FONT_SANS = "Pretendard, 'Helvetica Neue', Helvetica, Arial, sans-serif"
FONT_MONO = "'JetBrains Mono', Menlo, Consolas, monospace"
FONT_SERIF = "'Times New Roman', Times, Garamond, serif"


def svg_doc(width: int, height: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f"{body}</svg>"
    )


def write_pair(name: str, svg: str, width: int, height: int) -> None:
    svg_path = OUT / f"{name}.svg"
    png_path = OUT / f"{name}.png"
    svg_path.write_text(svg, encoding="utf-8")
    cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        write_to=str(png_path),
        output_width=width * 2,
        output_height=height * 2,
    )
    print(f"  wrote {svg_path.relative_to(ROOT)}  +  {png_path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Concept A — Crossed axes wordmark (KAIST HCIL minimalism)
#   Heavy Pretendard "AXIS"; the X has subtle extending strokes that echo
#   crossed coordinate axes. Caption below.
# ---------------------------------------------------------------------------
def concept_a_square() -> str:
    body = f"""
    <g font-family="{FONT_SANS}" fill="{INK}">
      <text x="512" y="500" text-anchor="middle" font-size="280"
            font-weight="900" letter-spacing="-8">AXIS</text>
      <line x1="220" y1="540" x2="804" y2="540" stroke="{INK}" stroke-width="6"/>
      <text x="512" y="595" text-anchor="middle" font-size="26"
            font-weight="500" fill="{DIM}" letter-spacing="2">
        Augmented eXperience and Interactive Systems
      </text>
      <text x="512" y="650" text-anchor="middle" font-size="28"
            font-weight="700" fill="{KU_CRIMSON}" letter-spacing="10">
        KOREA UNIVERSITY
      </text>
    </g>
    """
    return svg_doc(1024, 1024, body)


def concept_a_lockup() -> str:
    body = f"""
    <g font-family="{FONT_SANS}">
      <text x="120" y="380" font-size="320" font-weight="900"
            letter-spacing="-10" fill="{INK}">AXIS</text>
      <line x1="900" y1="200" x2="900" y2="500" stroke="{LIGHT}" stroke-width="3"/>
      <text x="940" y="290" font-size="44" font-weight="700" fill="{INK}">
        AXIS Laboratory
      </text>
      <text x="940" y="350" font-size="32" font-weight="500" fill="{DIM}">
        {FULL_NAME}
      </text>
      <text x="940" y="410" font-size="32" font-weight="700" fill="{KU_CRIMSON}">
        Korea University
      </text>
    </g>
    """
    return svg_doc(2400, 600, body)


# ---------------------------------------------------------------------------
# Concept B — Haptic wave underline (lab identity = haptics)
#   Mono wordmark sitting on a baseline that becomes a sine wave to the right.
# ---------------------------------------------------------------------------
def _sine_path(x0: float, y0: float, length: float, amp: float, cycles: float, samples: int = 200) -> str:
    pts = []
    for i in range(samples + 1):
        t = i / samples
        x = x0 + t * length
        y = y0 - amp * math.sin(2 * math.pi * cycles * t)
        pts.append(f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}")
    return " ".join(pts)


def concept_b_square() -> str:
    wave = _sine_path(180, 620, 664, amp=42, cycles=2.5)
    body = f"""
    <g>
      <text x="512" y="510" text-anchor="middle"
            font-family="{FONT_MONO}" font-size="240" font-weight="700"
            fill="{INK}" letter-spacing="-4">AXIS</text>
      <path d="{wave}" stroke="{KU_CRIMSON}" stroke-width="10"
            stroke-linecap="round" fill="none"/>
      <text x="512" y="730" text-anchor="middle" font-family="{FONT_SANS}"
            font-size="28" font-weight="500" fill="{DIM}" letter-spacing="3">
        Augmented eXperience and Interactive Systems
      </text>
      <text x="512" y="775" text-anchor="middle" font-family="{FONT_SANS}"
            font-size="28" font-weight="700" fill="{INK}" letter-spacing="6">
        KOREA UNIVERSITY
      </text>
    </g>
    """
    return svg_doc(1024, 1024, body)


def concept_b_lockup() -> str:
    wave = _sine_path(120, 410, 760, amp=36, cycles=2.5)
    body = f"""
    <g>
      <text x="120" y="380" font-family="{FONT_MONO}" font-size="280"
            font-weight="700" fill="{INK}" letter-spacing="-6">AXIS</text>
      <path d="{wave}" stroke="{KU_CRIMSON}" stroke-width="10"
            stroke-linecap="round" fill="none"/>
      <g font-family="{FONT_SANS}">
        <text x="980" y="290" font-size="44" font-weight="700" fill="{INK}">
          AXIS Lab
        </text>
        <text x="980" y="345" font-size="30" font-weight="500" fill="{DIM}">
          Haptics · HCI · VR/AR
        </text>
        <text x="980" y="400" font-size="30" font-weight="700" fill="{KU_CRIMSON}">
          Korea University
        </text>
      </g>
    </g>
    """
    return svg_doc(2400, 600, body)


# ---------------------------------------------------------------------------
# Concept C — Coordinate origin mark (three axes from a single point)
#   Geometric symbol: three rays at 0°, 90°, 210° forming an axis triad.
#   Reads as "A" silhouette and as XYZ axes simultaneously.
# ---------------------------------------------------------------------------
def _axis_triad(cx: float, cy: float, length: float, stroke: float, color_x: str, color_y: str, color_z: str) -> str:
    # X axis to the right, Y up, Z back-left at 210°
    x_end = (cx + length, cy)
    y_end = (cx, cy - length)
    z_angle = math.radians(210)
    z_end = (cx + length * math.cos(z_angle), cy - length * math.sin(z_angle))
    head = 14
    return f"""
      <line x1="{cx}" y1="{cy}" x2="{x_end[0]:.1f}" y2="{x_end[1]:.1f}"
            stroke="{color_x}" stroke-width="{stroke}" stroke-linecap="round"/>
      <line x1="{cx}" y1="{cy}" x2="{y_end[0]:.1f}" y2="{y_end[1]:.1f}"
            stroke="{color_y}" stroke-width="{stroke}" stroke-linecap="round"/>
      <line x1="{cx}" y1="{cy}" x2="{z_end[0]:.1f}" y2="{z_end[1]:.1f}"
            stroke="{color_z}" stroke-width="{stroke}" stroke-linecap="round"/>
      <circle cx="{cx}" cy="{cy}" r="{head}" fill="{INK}"/>
    """


def concept_c_square() -> str:
    triad = _axis_triad(512, 440, length=240, stroke=22,
                        color_x=KU_CRIMSON, color_y=INK, color_z=DIM)
    body = f"""
    <g>
      {triad}
      <g font-family="{FONT_SANS}" fill="{INK}" text-anchor="middle">
        <text x="512" y="730" font-size="170" font-weight="800"
              letter-spacing="6">AXIS</text>
        <text x="512" y="800" font-size="30" font-weight="500" fill="{DIM}"
              letter-spacing="4">Augmented eXperience &amp; Interactive Systems</text>
        <text x="512" y="855" font-size="28" font-weight="700"
              fill="{KU_CRIMSON}" letter-spacing="8">KOREA UNIVERSITY</text>
      </g>
    </g>
    """
    return svg_doc(1024, 1024, body)


def concept_c_lockup() -> str:
    triad = _axis_triad(280, 320, length=180, stroke=20,
                        color_x=KU_CRIMSON, color_y=INK, color_z=DIM)
    body = f"""
    <g>
      {triad}
      <line x1="540" y1="180" x2="540" y2="430" stroke="{LIGHT}" stroke-width="3"/>
      <g font-family="{FONT_SANS}">
        <text x="600" y="270" font-size="100" font-weight="800"
              fill="{INK}" letter-spacing="-2">AXIS</text>
        <text x="600" y="345" font-size="30" font-weight="500" fill="{DIM}">
          {FULL_NAME}
        </text>
        <text x="600" y="395" font-size="30" font-weight="700"
              fill="{KU_CRIMSON}">Korea University</text>
      </g>
    </g>
    """
    return svg_doc(2400, 600, body)


# ---------------------------------------------------------------------------
# Concept D — Korea University crimson chip + monogram
#   Filled crimson rounded square with "AX" monogram in white,
#   wordmark to the right. Most institutional/serious of the set.
# ---------------------------------------------------------------------------
def concept_d_square() -> str:
    body = f"""
    <g>
      <rect x="312" y="200" width="400" height="400" rx="48"
            fill="{KU_CRIMSON}"/>
      <text x="512" y="490" text-anchor="middle"
            font-family="{FONT_SANS}" font-size="280" font-weight="900"
            fill="#FFFFFF" letter-spacing="-12">AX</text>
      <g font-family="{FONT_SANS}" fill="{INK}" text-anchor="middle">
        <text x="512" y="720" font-size="120" font-weight="800"
              letter-spacing="2">AXIS LAB</text>
        <text x="512" y="780" font-size="28" font-weight="500" fill="{DIM}"
              letter-spacing="2">Augmented eXperience and Interactive Systems</text>
        <text x="512" y="830" font-size="28" font-weight="700"
              fill="{KU_CRIMSON}" letter-spacing="8">KOREA UNIVERSITY</text>
      </g>
    </g>
    """
    return svg_doc(1024, 1024, body)


def concept_d_lockup() -> str:
    body = f"""
    <g>
      <rect x="100" y="170" width="280" height="280" rx="36" fill="{KU_CRIMSON}"/>
      <text x="240" y="370" text-anchor="middle" font-family="{FONT_SANS}"
            font-size="200" font-weight="900" fill="#FFFFFF"
            letter-spacing="-10">AX</text>
      <g font-family="{FONT_SANS}">
        <text x="430" y="260" font-size="92" font-weight="800" fill="{INK}"
              letter-spacing="-2">AXIS Lab</text>
        <text x="430" y="320" font-size="30" font-weight="500" fill="{DIM}">
          {FULL_NAME}
        </text>
        <text x="430" y="375" font-size="30" font-weight="700"
              fill="{KU_CRIMSON}">Korea University</text>
      </g>
    </g>
    """
    return svg_doc(2400, 600, body)


# ---------------------------------------------------------------------------
# Concept E — Isometric cube (AR/spatial vibe)
#   Cube drawn isometrically; three visible faces tinted; wordmark beneath.
# ---------------------------------------------------------------------------
def concept_e_square() -> str:
    cx, cy = 512, 380
    s = 160  # half-edge in iso projection
    # iso unit vectors
    rx, ry = math.cos(math.radians(30)), math.sin(math.radians(30))
    # cube corners (top, front-right, front-left, bottom)
    top = (cx, cy - s)
    right = (cx + s * rx, cy - s + s * ry)
    left = (cx - s * rx, cy - s + s * ry)
    midR = (cx + s * rx, cy + s * ry)
    midL = (cx - s * rx, cy + s * ry)
    bottom = (cx, cy + 2 * s * ry)
    center = (cx, cy - s + 2 * s * ry)

    body = f"""
    <g stroke="{INK}" stroke-width="6" stroke-linejoin="round" fill="none">
      <!-- top face (light) -->
      <polygon points="{top[0]},{top[1]} {right[0]:.1f},{right[1]:.1f} {center[0]:.1f},{center[1]:.1f} {left[0]:.1f},{left[1]:.1f}"
               fill="#F5E1E4"/>
      <!-- left face (medium) -->
      <polygon points="{left[0]:.1f},{left[1]:.1f} {center[0]:.1f},{center[1]:.1f} {bottom[0]},{bottom[1]} {midL[0]:.1f},{midL[1]:.1f}"
               fill="#E0AAB1"/>
      <!-- right face (crimson) -->
      <polygon points="{right[0]:.1f},{right[1]:.1f} {center[0]:.1f},{center[1]:.1f} {bottom[0]},{bottom[1]} {midR[0]:.1f},{midR[1]:.1f}"
               fill="{KU_CRIMSON}"/>
    </g>
    <g font-family="{FONT_SANS}" fill="{INK}" text-anchor="middle">
      <text x="512" y="780" font-size="170" font-weight="800"
            letter-spacing="6">AXIS</text>
      <text x="512" y="845" font-size="28" font-weight="500" fill="{DIM}"
            letter-spacing="3">Augmented eXperience and Interactive Systems</text>
      <text x="512" y="895" font-size="28" font-weight="700"
            fill="{KU_CRIMSON}" letter-spacing="8">KOREA UNIVERSITY</text>
    </g>
    """
    return svg_doc(1024, 1024, body)


def concept_e_lockup() -> str:
    cx, cy = 240, 300
    s = 110
    rx, ry = math.cos(math.radians(30)), math.sin(math.radians(30))
    top = (cx, cy - s)
    right = (cx + s * rx, cy - s + s * ry)
    left = (cx - s * rx, cy - s + s * ry)
    midR = (cx + s * rx, cy + s * ry)
    midL = (cx - s * rx, cy + s * ry)
    bottom = (cx, cy + 2 * s * ry)
    center = (cx, cy - s + 2 * s * ry)
    body = f"""
    <g stroke="{INK}" stroke-width="5" stroke-linejoin="round" fill="none">
      <polygon points="{top[0]},{top[1]} {right[0]:.1f},{right[1]:.1f} {center[0]:.1f},{center[1]:.1f} {left[0]:.1f},{left[1]:.1f}" fill="#F5E1E4"/>
      <polygon points="{left[0]:.1f},{left[1]:.1f} {center[0]:.1f},{center[1]:.1f} {bottom[0]},{bottom[1]} {midL[0]:.1f},{midL[1]:.1f}" fill="#E0AAB1"/>
      <polygon points="{right[0]:.1f},{right[1]:.1f} {center[0]:.1f},{center[1]:.1f} {bottom[0]},{bottom[1]} {midR[0]:.1f},{midR[1]:.1f}" fill="{KU_CRIMSON}"/>
    </g>
    <line x1="490" y1="170" x2="490" y2="430" stroke="{LIGHT}" stroke-width="3"/>
    <g font-family="{FONT_SANS}">
      <text x="540" y="260" font-size="100" font-weight="800" fill="{INK}"
            letter-spacing="-2">AXIS</text>
      <text x="540" y="335" font-size="28" font-weight="500" fill="{DIM}">
        {FULL_NAME}
      </text>
      <text x="540" y="385" font-size="30" font-weight="700"
            fill="{KU_CRIMSON}">Korea University</text>
    </g>
    """
    return svg_doc(2400, 600, body)


# ---------------------------------------------------------------------------
# Concept F — Academic minimal (serif, lowercase)
#   Lowercase "axis" set in serif italic, with a tiny coordinate cross.
# ---------------------------------------------------------------------------
def concept_f_square() -> str:
    body = f"""
    <g>
      <!-- tiny coordinate cross -->
      <g stroke="{INK}" stroke-width="6" stroke-linecap="round">
        <line x1="380" y1="320" x2="644" y2="320"/>
        <line x1="512" y1="220" x2="512" y2="420"/>
        <polygon points="644,320 624,310 624,330" fill="{INK}"/>
        <polygon points="512,220 502,240 522,240" fill="{INK}"/>
      </g>
      <text x="660" y="330" font-family="{FONT_SERIF}" font-size="32"
            font-style="italic" fill="{DIM}">x</text>
      <text x="525" y="218" font-family="{FONT_SERIF}" font-size="32"
            font-style="italic" fill="{DIM}">y</text>
      <text x="512" y="600" text-anchor="middle"
            font-family="{FONT_SERIF}" font-size="220"
            font-style="italic" font-weight="500" fill="{INK}">axis</text>
      <line x1="332" y1="660" x2="692" y2="660" stroke="{INK}" stroke-width="2"/>
      <text x="512" y="710" text-anchor="middle"
            font-family="{FONT_SERIF}" font-size="32" fill="{DIM}"
            letter-spacing="3">Augmented · eXperience · Interactive · Systems</text>
      <text x="512" y="770" text-anchor="middle" font-family="{FONT_SANS}"
            font-size="28" font-weight="700" fill="{KU_CRIMSON}"
            letter-spacing="10">KOREA UNIVERSITY</text>
    </g>
    """
    return svg_doc(1024, 1024, body)


def concept_f_lockup() -> str:
    body = f"""
    <g stroke="{INK}" stroke-width="5" stroke-linecap="round">
      <line x1="140" y1="380" x2="340" y2="380"/>
      <line x1="240" y1="280" x2="240" y2="460"/>
      <polygon points="340,380 322,370 322,390" fill="{INK}"/>
      <polygon points="240,280 230,298 250,298" fill="{INK}"/>
    </g>
    <text x="420" y="380" font-family="{FONT_SERIF}" font-size="180"
          font-style="italic" font-weight="500" fill="{INK}">axis</text>
    <line x1="900" y1="180" x2="900" y2="450" stroke="{LIGHT}" stroke-width="3"/>
    <g font-family="{FONT_SERIF}">
      <text x="940" y="260" font-size="40" font-style="italic" fill="{INK}">
        Laboratory
      </text>
      <text x="940" y="320" font-size="30" fill="{DIM}">
        {FULL_NAME}
      </text>
      <text x="940" y="380" font-size="30" font-weight="700" font-style="normal"
            fill="{KU_CRIMSON}">Korea University</text>
    </g>
    """
    return svg_doc(2400, 600, body)


# ---------------------------------------------------------------------------
# Contact sheet — composite all square PNGs in a 3x2 grid using Pillow
# ---------------------------------------------------------------------------
def build_contact_sheet(square_paths: list[Path], out_path: Path) -> None:
    cell = 700
    pad = 40
    cols, rows = 3, 2
    label_h = 60
    title_h = 100
    width = cols * cell + (cols + 1) * pad
    height = title_h + rows * (cell + label_h) + (rows + 1) * pad

    canvas = Image.new("RGB", (width, height), color="#FAFAF7")
    draw = ImageDraw.Draw(canvas)

    # title
    title_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf", "Arial.ttf"], 44)
    label_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf", "Arial.ttf"], 26)
    draw.text((width // 2, title_h // 2), "AXIS Lab — Logo Concepts",
              font=title_font, fill="#0A0A0A", anchor="mm")

    labels = ["A · Wordmark", "B · Haptic Wave", "C · Axis Triad",
              "D · KU Chip", "E · Iso Cube", "F · Serif Mark"]
    for i, (p, label) in enumerate(zip(square_paths, labels)):
        col = i % cols
        row = i // cols
        x = pad + col * (cell + pad)
        y = title_h + pad + row * (cell + label_h + pad)
        img = Image.open(p).convert("RGBA")
        img = img.resize((cell, cell), Image.LANCZOS)
        # subtle border
        canvas.paste(img, (x, y), img)
        draw.rectangle([x, y, x + cell - 1, y + cell - 1],
                       outline="#E0E0E0", width=2)
        draw.text((x + cell // 2, y + cell + label_h // 2), label,
                  font=label_font, fill="#0A0A0A", anchor="mm")

    canvas.save(out_path, "PNG")


def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    search_dirs = [
        "/System/Library/Fonts/",
        "/System/Library/Fonts/Supplemental/",
        "/Library/Fonts/",
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


def main() -> None:
    print("Generating AXIS Lab logo concepts ...")
    square_paths = []
    concepts = [
        ("a_wordmark", concept_a_square, concept_a_lockup),
        ("b_wave",     concept_b_square, concept_b_lockup),
        ("c_triad",    concept_c_square, concept_c_lockup),
        ("d_ku_chip",  concept_d_square, concept_d_lockup),
        ("e_iso_cube", concept_e_square, concept_e_lockup),
        ("f_serif",    concept_f_square, concept_f_lockup),
    ]
    for slug, sq_fn, lk_fn in concepts:
        write_pair(f"axis_{slug}_square", sq_fn(), 1024, 1024)
        write_pair(f"axis_{slug}_lockup", lk_fn(), 2400, 600)
        square_paths.append(OUT / f"axis_{slug}_square.png")

    sheet_path = OUT / "_contact_sheet.png"
    build_contact_sheet(square_paths, sheet_path)
    print(f"  wrote {sheet_path.relative_to(ROOT)}")
    print("done.")


if __name__ == "__main__":
    main()
