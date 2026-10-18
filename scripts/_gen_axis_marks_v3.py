"""AXIS Lab marks v3 — committed to the AXIS identity.

The lab name AXIS literally means "축" (coordinate axis), and the first
letter "A" is geometrically two diagonal strokes meeting at an apex —
which is the same shape as two axes radiating from an origin.

This set leans into that double meaning. Every mark says either
"I am the letter A" or "I am a coordinate axis system" — usually both.

  AX1 · Axis-A           — letter A whose strokes are coordinate axes
  AX2 · Axis-A + Touch   — AX1 with a fingertip tap at the origin (apex)
  AX3 · Axis-A + Hand    — AX1 with a hand grasping/pivoting it
  AX4 · 3D Triad Origin  — XYZ triad with AR cube + tap dot at origin
  AX5 · A in AR Cube     — bold A floating inside an iso cube wireframe
  AX6 · Pivot A          — letter A with a curved rotation arrow (axis = pivot)

Palette: each axis gets its own conventional color (X = warm, Y = teal,
Z = crimson) so the mark also reads as a 3D coordinate frame at a glance.
"""
from __future__ import annotations

import math
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "logos" / "marks_v3"
OUT.mkdir(parents=True, exist_ok=True)

# Per-axis palette (kept conventional: warm = X, cool = Y, accent = Z)
X_COL  = "#F59E0B"   # amber  (right leg of A)
Y_COL  = "#0891B2"   # teal   (apex / vertical axis)
Z_COL  = "#862633"   # crimson (left leg / KU accent)
NAVY   = "#0F2A44"
TEAL_HI = "#5EEAD4"

DEFS = f"""
<defs>
  <linearGradient id="grad-teal" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{TEAL_HI}"/>
    <stop offset="1" stop-color="{Y_COL}"/>
  </linearGradient>
  <linearGradient id="grad-warm" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FCD34D"/>
    <stop offset="1" stop-color="{X_COL}"/>
  </linearGradient>
  <marker id="arr-x" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 Z" fill="{X_COL}"/>
  </marker>
  <marker id="arr-y" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 Z" fill="{Y_COL}"/>
  </marker>
  <marker id="arr-z" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 Z" fill="{Z_COL}"/>
  </marker>
  <marker id="arr-navy" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">
    <path d="M 0 0 L 10 5 L 0 10 Z" fill="{NAVY}"/>
  </marker>
</defs>
"""


def svg(body: str, w: int = 1024, h: int = 1024) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">{DEFS}{body}</svg>'
    )


def write_pair(name: str, doc: str) -> Path:
    svg_path = OUT / f"{name}.svg"
    png_path = OUT / f"{name}.png"
    svg_path.write_text(doc, encoding="utf-8")
    cairosvg.svg2png(
        bytestring=doc.encode("utf-8"),
        write_to=str(png_path),
        output_width=2048, output_height=2048,
    )
    print(f"  {svg_path.relative_to(ROOT)}  +  {png_path.relative_to(ROOT)}")
    return png_path


# ---------------------------------------------------------------------------
# Axis-A primitive — the shared geometric core for AX1/AX2/AX3/AX6.
#
# Apex = origin O (filled dot).
# Three coordinate axes radiate from O:
#   • Left leg (Z axis):   O → bottom-left,    crimson, arrow at tip
#   • Right leg (X axis):  O → bottom-right,   amber,   arrow at tip
#   • Crossbar at h_cross: between the legs,   teal/navy
# The result is geometrically a letter A made of axis arrows.
# ---------------------------------------------------------------------------
def axis_a(apex=(512, 200), bl=(240, 870), br=(784, 870),
           crossbar_y=640, stroke_w=46) -> str:
    ax, ay = apex
    blx, bly = bl
    brx, bry = br
    # crossbar endpoints — on the legs at y = crossbar_y
    t = (crossbar_y - ay) / (bly - ay)
    cl_x = ax + t * (blx - ax)
    cr_x = ax + t * (brx - ax)

    # axes (drawn first so origin dot covers the joint cleanly)
    body = f"""
      <line x1="{ax}" y1="{ay}" x2="{blx}" y2="{bly}"
            stroke="{Z_COL}" stroke-width="{stroke_w}" stroke-linecap="round"
            marker-end="url(#arr-z)"/>
      <line x1="{ax}" y1="{ay}" x2="{brx}" y2="{bry}"
            stroke="{X_COL}" stroke-width="{stroke_w}" stroke-linecap="round"
            marker-end="url(#arr-x)"/>
      <line x1="{cl_x:.1f}" y1="{crossbar_y}" x2="{cr_x:.1f}" y2="{crossbar_y}"
            stroke="{Y_COL}" stroke-width="{stroke_w}" stroke-linecap="round"/>
      <circle cx="{ax}" cy="{ay}" r="{stroke_w * 0.85:.1f}" fill="{NAVY}"/>
    """
    return body


# ---------------------------------------------------------------------------
# AX1 — Axis-A monogram (no extras)
# ---------------------------------------------------------------------------
def mark_ax1_axis_a() -> str:
    return svg(axis_a())


# ---------------------------------------------------------------------------
# AX2 — Axis-A + Touch (HCI variant: tap dot + ripple at the origin)
# ---------------------------------------------------------------------------
def mark_ax2_axis_a_touch() -> str:
    apex = (512, 280)
    body = axis_a(apex=apex, bl=(240, 870), br=(784, 870), crossbar_y=680)
    ax, ay = apex
    ripples = f"""
      <g fill="none" stroke="{NAVY}" stroke-linecap="round">
        <path d="M {ax-100} {ay-50} A 110 110 0 0 1 {ax+100} {ay-50}"
              stroke-width="14" opacity="0.55"/>
        <path d="M {ax-170} {ay-90} A 190 190 0 0 1 {ax+170} {ay-90}"
              stroke-width="12" opacity="0.28"/>
      </g>
      <circle cx="{ax}" cy="{ay}" r="44" fill="{Z_COL}"/>
    """
    return svg(body + ripples)


# ---------------------------------------------------------------------------
# AX3 — Axis-A + Hand (hand pivots/holds the axis-A)
# ---------------------------------------------------------------------------
def _open_hand(cx, cy, scale=1.0, fill="url(#grad-teal)"):
    s = scale
    palm_w, palm_h = 320 * s, 280 * s
    palm_x = cx - palm_w / 2
    palm_y = cy - 40 * s
    palm = (
        f'<rect x="{palm_x}" y="{palm_y}" width="{palm_w}" height="{palm_h}" '
        f'rx="{90*s}" ry="{90*s}" fill="{fill}"/>'
    )
    finger_w = 64 * s
    finger_specs = [(-130, 200, 30), (-50, 290, 0), (30, 320, -20), (110, 250, 10)]
    fingers = []
    for dx, h, top_off in finger_specs:
        fx = cx + dx * s - finger_w / 2
        fy = palm_y - h * s + top_off * s
        fh = (palm_y + 40 * s) - fy
        fingers.append(
            f'<rect x="{fx}" y="{fy}" width="{finger_w}" height="{fh}" '
            f'rx="{finger_w/2}" ry="{finger_w/2}" fill="{fill}"/>'
        )
    thumb_cx = cx - 180 * s
    thumb_cy = cy + 140 * s
    thumb = (
        f'<g transform="translate({thumb_cx} {thumb_cy}) rotate(-25)">'
        f'<rect x="{-100*s}" y="{-50*s}" width="{180*s}" height="{100*s}" '
        f'rx="{50*s}" ry="{50*s}" fill="{fill}"/></g>'
    )
    return thumb + palm + "".join(fingers)


def mark_ax3_axis_a_hand() -> str:
    # axis-A scaled smaller, top-half of canvas
    a_apex = (512, 130)
    a_bl   = (300, 600)
    a_br   = (724, 600)
    body = axis_a(apex=a_apex, bl=a_bl, br=a_br, crossbar_y=440, stroke_w=38)
    # hand below, palm-up cradling the A
    hand = _open_hand(512, 820, scale=0.75, fill="url(#grad-teal)")
    return svg(hand + body)


# ---------------------------------------------------------------------------
# AX4 — 3D Triad Origin: full XYZ triad in perspective, AR cube floating
# at origin + crimson tap dot. Most "literal axis lab" reading.
# ---------------------------------------------------------------------------
def mark_ax4_triad_origin() -> str:
    cx, cy = 460, 580
    L = 360
    # Y up
    yx, yy = cx, cy - L
    # X right (slight downward perspective)
    xx, xy = cx + L * math.cos(math.radians(-15)), cy + L * math.sin(math.radians(-15))
    # Z back-left (perspective)
    zx, zy = cx - L * math.cos(math.radians(25)), cy - L * math.sin(math.radians(-25))
    # Actually re-derive Z for clarity: 25° below horizontal pointing back-left
    zang = math.radians(180 - 30)   # 150°
    zx = cx + L * math.cos(zang)
    zy = cy + L * math.sin(zang)
    # tweak X downward perspective
    xang = math.radians(-10)
    xx = cx + L * math.cos(xang)
    xy = cy + L * math.sin(xang)

    triad = f"""
      <line x1="{cx}" y1="{cy}" x2="{yx}" y2="{yy}"
            stroke="{Y_COL}" stroke-width="38" stroke-linecap="round"
            marker-end="url(#arr-y)"/>
      <line x1="{cx}" y1="{cy}" x2="{xx:.1f}" y2="{xy:.1f}"
            stroke="{X_COL}" stroke-width="38" stroke-linecap="round"
            marker-end="url(#arr-x)"/>
      <line x1="{cx}" y1="{cy}" x2="{zx:.1f}" y2="{zy:.1f}"
            stroke="{Z_COL}" stroke-width="38" stroke-linecap="round"
            marker-end="url(#arr-z)"/>
    """
    # AR cube floating at top-right
    cube_cx, cube_cy = 720, 360
    s = 110
    rx, ry = math.cos(math.radians(30)), math.sin(math.radians(30))
    top = (cube_cx, cube_cy - s)
    right = (cube_cx + s * rx, cube_cy - s + s * ry)
    left = (cube_cx - s * rx, cube_cy - s + s * ry)
    midR = (cube_cx + s * rx, cube_cy + s * ry)
    midL = (cube_cx - s * rx, cube_cy + s * ry)
    bottom = (cube_cx, cube_cy + 2 * s * ry)
    center = (cube_cx, cube_cy - s + 2 * s * ry)
    cube = f"""
      <g stroke="{NAVY}" stroke-width="14" stroke-linejoin="round" fill="none">
        <polygon points="{top[0]},{top[1]} {right[0]:.0f},{right[1]:.0f} {midR[0]:.0f},{midR[1]:.0f} {bottom[0]},{bottom[1]} {midL[0]:.0f},{midL[1]:.0f} {left[0]:.0f},{left[1]:.0f}"/>
        <line x1="{top[0]}" y1="{top[1]}" x2="{center[0]:.0f}" y2="{center[1]:.0f}" opacity="0.5"/>
        <line x1="{left[0]:.0f}" y1="{left[1]:.0f}" x2="{center[0]:.0f}" y2="{center[1]:.0f}" opacity="0.5"/>
        <line x1="{right[0]:.0f}" y1="{right[1]:.0f}" x2="{center[0]:.0f}" y2="{center[1]:.0f}" opacity="0.5"/>
      </g>
      <polygon points="{top[0]},{top[1]} {right[0]:.0f},{right[1]:.0f} {center[0]:.0f},{center[1]:.0f} {left[0]:.0f},{left[1]:.0f}"
               fill="{X_COL}" opacity="0.55"/>
    """
    # tap dot at origin
    dot = f'<circle cx="{cx}" cy="{cy}" r="36" fill="{NAVY}"/>'
    return svg(triad + cube + dot)


# ---------------------------------------------------------------------------
# AX5 — A in AR Cube: a bold A floats inside an iso cube wireframe
# ---------------------------------------------------------------------------
def mark_ax5_a_in_cube() -> str:
    cx, cy = 512, 530
    s = 320
    rx, ry = math.cos(math.radians(30)), math.sin(math.radians(30))
    top = (cx, cy - s)
    right = (cx + s * rx, cy - s + s * ry)
    left = (cx - s * rx, cy - s + s * ry)
    midR = (cx + s * rx, cy + s * ry)
    midL = (cx - s * rx, cy + s * ry)
    bottom = (cx, cy + 2 * s * ry)
    center = (cx, cy - s + 2 * s * ry)
    cube = f"""
      <g stroke="{NAVY}" stroke-width="20" stroke-linejoin="round"
         stroke-linecap="round" fill="none">
        <polygon points="{top[0]},{top[1]} {right[0]:.0f},{right[1]:.0f} {midR[0]:.0f},{midR[1]:.0f} {bottom[0]},{bottom[1]} {midL[0]:.0f},{midL[1]:.0f} {left[0]:.0f},{left[1]:.0f}"/>
        <line x1="{top[0]}" y1="{top[1]}" x2="{center[0]:.0f}" y2="{center[1]:.0f}" opacity="0.4" stroke-width="14"/>
        <line x1="{left[0]:.0f}" y1="{left[1]:.0f}" x2="{center[0]:.0f}" y2="{center[1]:.0f}" opacity="0.4" stroke-width="14"/>
        <line x1="{right[0]:.0f}" y1="{right[1]:.0f}" x2="{center[0]:.0f}" y2="{center[1]:.0f}" opacity="0.4" stroke-width="14"/>
      </g>
    """
    # bold A inside cube — use axis-A primitive scaled into cube space
    a_apex = (cx, cy - 200)
    a_bl   = (cx - 160, cy + 200)
    a_br   = (cx + 160, cy + 200)
    a = axis_a(apex=a_apex, bl=a_bl, br=a_br, crossbar_y=cy + 70, stroke_w=34)
    return svg(cube + a)


# ---------------------------------------------------------------------------
# AX6 — Pivot A: letter A with a curved rotation arrow (axis = pivot point)
# ---------------------------------------------------------------------------
def mark_ax6_pivot_a() -> str:
    apex = (512, 260)
    body = axis_a(apex=apex, bl=(280, 820), br=(744, 820),
                  crossbar_y=640, stroke_w=42)
    ax, ay = apex
    # curved rotation arrow circling the apex (origin = axis of rotation)
    rot = f"""
      <path d="M {ax+170} {ay-40}
               A 180 180 0 1 1 {ax-170} {ay-40}"
            fill="none" stroke="{NAVY}" stroke-width="22"
            stroke-linecap="round" marker-end="url(#arr-navy)"/>
    """
    return svg(body + rot)


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
    cell, pad, label_h, title_h = 700, 40, 60, 100
    cols, rows = 3, 2
    width = cols * cell + (cols + 1) * pad
    height = title_h + rows * (cell + label_h) + (rows + 1) * pad
    canvas = Image.new("RGB", (width, height), color="#FAFAF7")
    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 44)
    label_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 26)
    draw.text((width // 2, title_h // 2),
              "AXIS Lab — Symbol Marks v3 (axis-A identity)",
              font=title_font, fill="#0A0A0A", anchor="mm")
    for i, (p, label) in enumerate(zip(paths, labels)):
        col = i % cols
        row = i // cols
        x = pad + col * (cell + pad)
        y = title_h + pad + row * (cell + label_h + pad)
        img = Image.open(p).convert("RGBA").resize((cell, cell), Image.LANCZOS)
        canvas.paste(img, (x, y), img)
        draw.rectangle([x, y, x + cell - 1, y + cell - 1], outline="#E0E0E0", width=2)
        draw.text((x + cell // 2, y + cell + label_h // 2), label,
                  font=label_font, fill="#0A0A0A", anchor="mm")
    canvas.save(out_path, "PNG")


def main() -> None:
    print("Generating AXIS Lab v3 marks (axis-A identity) ...")
    marks = [
        ("ax1_axis_a",        mark_ax1_axis_a,        "AX1 · Axis-A"),
        ("ax2_axis_a_touch",  mark_ax2_axis_a_touch,  "AX2 · Axis-A + Touch"),
        ("ax3_axis_a_hand",   mark_ax3_axis_a_hand,   "AX3 · Axis-A + Hand"),
        ("ax4_triad_origin",  mark_ax4_triad_origin,  "AX4 · 3D Triad + Cube"),
        ("ax5_a_in_cube",     mark_ax5_a_in_cube,     "AX5 · A in AR Cube"),
        ("ax6_pivot_a",       mark_ax6_pivot_a,       "AX6 · Pivot A"),
    ]
    paths, labels = [], []
    for slug, fn, label in marks:
        paths.append(write_pair(f"axis_{slug}", fn()))
        labels.append(label)
    build_contact_sheet(paths, labels, OUT / "_v3_contact_sheet.png")
    print(f"  contact sheet → {(OUT / '_v3_contact_sheet.png').relative_to(ROOT)}")
    print("done.")


if __name__ == "__main__":
    main()
