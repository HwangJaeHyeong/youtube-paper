"""AXIS-A — concept variations in the P1 palette (ink + crimson pop).

Eight new takes on the axis-A monogram, each pushing a different angle
on the AXIS identity. Single-color body (ink black) + a single crimson
pop accent in every mark, so the set reads as one family.

  C1 · Stem A         — letter A with a vertical Y-axis stem through apex
  C2 · Horizon A      — A standing on a baseline X-axis with arrow
  C3 · Cursor Apex    — A whose apex is a stylized pointer cursor
  C4 · Cube Cutout    — solid iso cube with the A carved as negative space
  C5 · AX Compound    — A and X overlaid (the literal lab-name letters)
  C6 · Bracket A      — A framed by AR-reticle corner brackets
  C7 · Atom A         — A with orbital dots on each terminus
  C8 · Triangle A     — A enclosed by a triangular outline (geometric frame)

All marks: 1024x1024 transparent SVG + PNG, ink #0A0A0A + crimson #862633.
"""
from __future__ import annotations

import math
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "logos" / "ideas"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#0A0A0A"
CRIM = "#862633"
W = H = 1024


def svg(body: str) -> str:
    defs = f"""
    <defs>
      <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5"
              markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 Z" fill="{INK}"/>
      </marker>
    </defs>
    """
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}">{defs}{body}</svg>'
    )


def write_pair(name: str, doc: str) -> Path:
    sp = OUT / f"{name}.svg"
    pp = OUT / f"{name}.png"
    sp.write_text(doc, encoding="utf-8")
    cairosvg.svg2png(bytestring=doc.encode("utf-8"),
                     write_to=str(pp),
                     output_width=2048, output_height=2048)
    print(f"  {sp.relative_to(ROOT)}  +  {pp.relative_to(ROOT)}")
    return pp


# ---------------------------------------------------------------------------
# Shared geometry helpers
# ---------------------------------------------------------------------------
def axis_a_paths(apex, bl, br, crossbar_y, sw, color=INK):
    """Three strokes that compose the letter A."""
    ax, ay = apex
    blx, bly = bl
    brx, bry = br
    t = (crossbar_y - ay) / (bly - ay)
    cl_x = ax + t * (blx - ax)
    cr_x = ax + t * (brx - ax)
    return f"""
      <line x1="{ax}" y1="{ay}" x2="{blx}" y2="{bly}"
            stroke="{color}" stroke-width="{sw}" stroke-linecap="round"/>
      <line x1="{ax}" y1="{ay}" x2="{brx}" y2="{bry}"
            stroke="{color}" stroke-width="{sw}" stroke-linecap="round"/>
      <line x1="{cl_x:.1f}" y1="{crossbar_y}" x2="{cr_x:.1f}" y2="{crossbar_y}"
            stroke="{color}" stroke-width="{sw}" stroke-linecap="round"/>
    """


# ---------------------------------------------------------------------------
# C1 — Stem A
#   Standard A + a vertical stem rising from the apex with an arrow tip.
#   Reads as "letter A with a coordinate Y-axis going through it".
# ---------------------------------------------------------------------------
def c1_stem_a() -> str:
    apex = (512, 320)
    a = axis_a_paths(apex, (260, 880), (764, 880), 700, 56)
    stem = f"""
      <line x1="{apex[0]}" y1="{apex[1]}" x2="{apex[0]}" y2="120"
            stroke="{INK}" stroke-width="36" stroke-linecap="round"
            marker-end="url(#arr)"/>
    """
    dot = f'<circle cx="{apex[0]}" cy="{apex[1]}" r="42" fill="{CRIM}"/>'
    return svg(stem + a + dot)


# ---------------------------------------------------------------------------
# C2 — Horizon A
#   A sits on a horizontal baseline with a right-pointing X-axis arrow.
# ---------------------------------------------------------------------------
def c2_horizon_a() -> str:
    apex = (512, 220)
    bl, br = (300, 760), (724, 760)
    a = axis_a_paths(apex, bl, br, 590, 56)
    base_y = 800
    horizon = f"""
      <line x1="120" y1="{base_y}" x2="900" y2="{base_y}"
            stroke="{INK}" stroke-width="36" stroke-linecap="round"
            marker-end="url(#arr)"/>
    """
    dot = f'<circle cx="{bl[0]}" cy="{base_y}" r="40" fill="{CRIM}"/>'
    return svg(horizon + a + dot)


# ---------------------------------------------------------------------------
# C3 — Cursor Apex
#   A whose apex is a stylised pointer-arrow cursor.
# ---------------------------------------------------------------------------
def c3_cursor_apex() -> str:
    # render A's two legs and the crossbar, but stop the legs short of the
    # apex so the cursor pointer can take its place
    apex = (512, 220)
    bl, br = (260, 880), (764, 880)
    cross_y = 700
    sw = 56
    legs = (
        f'<line x1="{apex[0]}" y1="{apex[1]+20}" x2="{bl[0]}" y2="{bl[1]}" '
        f'stroke="{INK}" stroke-width="{sw}" stroke-linecap="round"/>'
        f'<line x1="{apex[0]}" y1="{apex[1]+20}" x2="{br[0]}" y2="{br[1]}" '
        f'stroke="{INK}" stroke-width="{sw}" stroke-linecap="round"/>'
    )
    # crossbar
    t = (cross_y - apex[1]) / (bl[1] - apex[1])
    cl = apex[0] + t * (bl[0] - apex[0])
    cr = apex[0] + t * (br[0] - apex[0])
    crossbar = (
        f'<line x1="{cl:.1f}" y1="{cross_y}" x2="{cr:.1f}" y2="{cross_y}" '
        f'stroke="{INK}" stroke-width="{sw}" stroke-linecap="round"/>'
    )
    # crimson cursor pointer — tip at apex, body extending up-left
    cur = f"""
      <path d="M {apex[0]} {apex[1]+8}
               L {apex[0]-150} {apex[1]-130}
               L {apex[0]-72} {apex[1]-118}
               L {apex[0]-30} {apex[1]-220}
               L {apex[0]+30} {apex[1]-200}
               L {apex[0]+8} {apex[1]-100}
               L {apex[0]+88} {apex[1]-66}
               Z"
            fill="{CRIM}" stroke="{INK}" stroke-width="10"
            stroke-linejoin="round"/>
    """
    return svg(legs + crossbar + cur)


# ---------------------------------------------------------------------------
# C4 — Cube Cutout
#   Solid iso cube; the front-facing area carries the A as bold negative
#   space (white strokes punching through), with a crimson origin dot.
# ---------------------------------------------------------------------------
def c4_cube_cutout() -> str:
    cx, cy = 512, 540
    s = 360
    rx, ry = math.cos(math.radians(30)), math.sin(math.radians(30))
    top = (cx, cy - s)
    right = (cx + s * rx, cy - s + s * ry)
    left = (cx - s * rx, cy - s + s * ry)
    midR = (cx + s * rx, cy + s * ry)
    midL = (cx - s * rx, cy + s * ry)
    bottom = (cx, cy + 2 * s * ry)
    cube_hex = f"""
      <polygon points="{top[0]},{top[1]} {right[0]:.0f},{right[1]:.0f}
                       {midR[0]:.0f},{midR[1]:.0f} {bottom[0]},{bottom[1]}
                       {midL[0]:.0f},{midL[1]:.0f} {left[0]:.0f},{left[1]:.0f}"
               fill="{INK}"/>
    """
    # A in white on top — using ROUND linecap creates clean cutout illusion
    apex = (cx, cy - 220)
    a = axis_a_paths(apex, (cx - 170, cy + 200), (cx + 170, cy + 200),
                     cy + 70, 44, color="white")
    dot = f'<circle cx="{apex[0]}" cy="{apex[1]}" r="34" fill="{CRIM}"/>'
    return svg(cube_hex + a + dot)


# ---------------------------------------------------------------------------
# C5 — AX Compound
#   A and X letters overlaid sharing a common center, the literal first
#   two letters of the lab name. Crimson highlights the X.
# ---------------------------------------------------------------------------
def c5_ax_compound() -> str:
    # A — black, larger
    apex = (512, 200)
    a = axis_a_paths(apex, (272, 880), (752, 880), 660, 56)
    # X — crimson, drawn over the A's interior space
    x_size = 280
    x_cx, x_cy = 512, 580
    xstrokes = f"""
      <line x1="{x_cx - x_size/2}" y1="{x_cy - x_size/2}"
            x2="{x_cx + x_size/2}" y2="{x_cy + x_size/2}"
            stroke="{CRIM}" stroke-width="50" stroke-linecap="round"/>
      <line x1="{x_cx + x_size/2}" y1="{x_cy - x_size/2}"
            x2="{x_cx - x_size/2}" y2="{x_cy + x_size/2}"
            stroke="{CRIM}" stroke-width="50" stroke-linecap="round"/>
    """
    return svg(a + xstrokes)


# ---------------------------------------------------------------------------
# C6 — Bracket A
#   A inside four AR-reticle corner brackets — frames the monogram as a
#   target/observation field. Crimson dot at apex.
# ---------------------------------------------------------------------------
def c6_bracket_a() -> str:
    apex = (512, 320)
    a = axis_a_paths(apex, (320, 760), (704, 760), 620, 50)
    dot = f'<circle cx="{apex[0]}" cy="{apex[1]}" r="38" fill="{CRIM}"/>'
    bw = 30  # bracket arm length factor
    bl_len = 110
    brackets = f"""
      <g stroke="{INK}" stroke-width="28" stroke-linecap="round" fill="none">
        <polyline points="180,{180+bl_len} 180,180 {180+bl_len},180"/>
        <polyline points="{844-bl_len},180 844,180 844,{180+bl_len}"/>
        <polyline points="180,{844-bl_len} 180,844 {180+bl_len},844"/>
        <polyline points="{844-bl_len},844 844,844 844,{844-bl_len}"/>
      </g>
    """
    return svg(brackets + a + dot)


# ---------------------------------------------------------------------------
# C7 — Atom A
#   A with three small filled circles on each terminus (apex + two feet),
#   evoking an atomic/triad/orbital reading on top of the letter.
# ---------------------------------------------------------------------------
def c7_atom_a() -> str:
    apex = (512, 240)
    bl, br = (260, 860), (764, 860)
    a = axis_a_paths(apex, bl, br, 660, 50)
    # connecting orbital arc behind the A
    orbit = f"""
      <ellipse cx="512" cy="560" rx="380" ry="160"
               fill="none" stroke="{INK}" stroke-width="10" opacity="0.5"
               transform="rotate(0 512 560)"/>
    """
    nodes = f"""
      <circle cx="{apex[0]}" cy="{apex[1]}" r="46" fill="{CRIM}"/>
      <circle cx="{bl[0]}" cy="{bl[1]}" r="34" fill="{INK}"/>
      <circle cx="{br[0]}" cy="{br[1]}" r="34" fill="{INK}"/>
    """
    return svg(orbit + a + nodes)


# ---------------------------------------------------------------------------
# C8 — Triangle A
#   A bounded by a triangular outline matching its silhouette. Geometric,
#   blueprint-y feel.
# ---------------------------------------------------------------------------
def c8_triangle_a() -> str:
    apex = (512, 180)
    bl, br = (180, 880), (844, 880)
    a = axis_a_paths(apex, (300, 800), (724, 800), 620, 50)
    tri = (
        f'<polygon points="{apex[0]},{apex[1]} {bl[0]},{bl[1]} {br[0]},{br[1]}" '
        f'fill="none" stroke="{INK}" stroke-width="14"/>'
    )
    dot = f'<circle cx="{apex[0]}" cy="{apex[1]}" r="38" fill="{CRIM}"/>'
    return svg(tri + a + dot)


# ---------------------------------------------------------------------------
# Contact sheet
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


def build_contact_sheet(paths: list[Path], labels: list[str], out_path: Path) -> None:
    cell, pad, label_h, title_h = 600, 36, 56, 100
    cols, rows = 4, 2
    width = cols * cell + (cols + 1) * pad
    height = title_h + rows * (cell + label_h) + (rows + 1) * pad
    canvas = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 44)
    label_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 24)
    draw.text((width // 2, title_h // 2),
              "AXIS-A — concept ideas (P1 palette)",
              font=title_font, fill="#0A0A0A", anchor="mm")
    for i, (p, label) in enumerate(zip(paths, labels)):
        col = i % cols
        row = i // cols
        x = pad + col * (cell + pad)
        y = title_h + pad + row * (cell + label_h + pad)
        img = Image.open(p).convert("RGBA").resize((cell, cell), Image.LANCZOS)
        canvas.paste(img, (x, y), img)
        draw.rectangle([x, y, x + cell - 1, y + cell - 1],
                       outline="#E0E0E0", width=2)
        draw.text((x + cell // 2, y + cell + label_h // 2), label,
                  font=label_font, fill="#0A0A0A", anchor="mm")
    canvas.save(out_path, "PNG")


def main() -> None:
    print("Generating AXIS-A concept ideas ...")
    concepts = [
        ("c1_stem_a",       c1_stem_a,       "C1 · Stem A"),
        ("c2_horizon_a",    c2_horizon_a,    "C2 · Horizon A"),
        ("c3_cursor_apex",  c3_cursor_apex,  "C3 · Cursor Apex"),
        ("c4_cube_cutout",  c4_cube_cutout,  "C4 · Cube Cutout"),
        ("c5_ax_compound",  c5_ax_compound,  "C5 · AX Compound"),
        ("c6_bracket_a",    c6_bracket_a,    "C6 · Bracket A"),
        ("c7_atom_a",       c7_atom_a,       "C7 · Atom A"),
        ("c8_triangle_a",   c8_triangle_a,   "C8 · Triangle A"),
    ]
    paths, labels = [], []
    for slug, fn, label in concepts:
        paths.append(write_pair(f"axis_{slug}", fn()))
        labels.append(label)
    build_contact_sheet(paths, labels, OUT / "_ideas_contact_sheet.png")
    print(f"  contact sheet → {(OUT / '_ideas_contact_sheet.png').relative_to(ROOT)}")
    print("done.")


if __name__ == "__main__":
    main()
