"""AXIS Lab symbol marks v2 — hand/people motifs + richer color.

References supplied:
  · Image 1 (cyan-teal gradient open hand + motion arcs) — modern, friendly
  · Image 2 (Yonsei HCI: orange line-art people at workstations) — collab
  · Image 3 (SNU hci lab: pastel mint, lowercase serif) — soft academic
  · Image 4 (Inha HCI: orbital ring with multi-color dots) — scientific

Design directions distilled:
  • Hand is the most universal HCI symbol — make it the hero mark
  • Use a 2-stop gradient as primary brand color (cyan → teal) plus a
    warm accent (amber/crimson) for a friendly-but-credible feel
  • People-triad and orbital-triad as alternate concepts

All marks: 1024x1024 transparent SVG + PNG.
"""
from __future__ import annotations

import math
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "logos" / "marks_v2"
OUT.mkdir(parents=True, exist_ok=True)

# Palette
TEAL_HI = "#5EEAD4"      # gradient top
TEAL_LO = "#0891B2"      # gradient bottom
NAVY    = "#0F2A44"      # ink replacement, more brand-y
AMBER   = "#F59E0B"      # warm accent
CRIMSON = "#862633"      # KU crimson (kept available)
MINT_BG = "#E6F4F1"      # optional soft bg

# Reusable gradient defs
DEFS = f"""
<defs>
  <linearGradient id="grad-teal" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{TEAL_HI}"/>
    <stop offset="1" stop-color="{TEAL_LO}"/>
  </linearGradient>
  <linearGradient id="grad-teal-h" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{TEAL_HI}"/>
    <stop offset="1" stop-color="{TEAL_LO}"/>
  </linearGradient>
  <linearGradient id="grad-warm" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FCD34D"/>
    <stop offset="1" stop-color="{AMBER}"/>
  </linearGradient>
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
        output_width=2048,
        output_height=2048,
    )
    print(f"  {svg_path.relative_to(ROOT)}  +  {png_path.relative_to(ROOT)}")
    return png_path


# ---------------------------------------------------------------------------
# Hand silhouette helper — stylized 4-finger open hand, palm forward.
# Built from a palm rounded-rect + 4 finger rounded-rects + thumb blob,
# unioned visually (no need for an actual SVG union since fills overlap).
# ---------------------------------------------------------------------------
def open_hand(cx: float, cy: float, scale: float = 1.0,
              fill: str = "url(#grad-teal)") -> str:
    """Open hand pointing up (palm toward viewer).

    cx, cy roughly mark the centroid of the palm.
    Total bounding box ≈ 480x620 px at scale=1.
    """
    s = scale
    # palm
    palm_w, palm_h = 320 * s, 280 * s
    palm_x = cx - palm_w / 2
    palm_y = cy - 40 * s
    palm = (
        f'<rect x="{palm_x}" y="{palm_y}" width="{palm_w}" height="{palm_h}" '
        f'rx="{90*s}" ry="{90*s}" fill="{fill}"/>'
    )
    # 4 fingers (pinky, ring, middle, index — left to right)
    finger_w = 64 * s
    finger_gap = 8 * s
    finger_top_y = cy - 360 * s        # tallest tip
    finger_specs = [
        # (x_offset_from_center, height_above_palm, top_extra)
        (-130, 200, 30),  # pinky
        (-50,  290, 0),   # ring
        ( 30,  320, -20), # middle (longest)
        ( 110, 250, 10),  # index
    ]
    fingers = []
    for dx, h, top_off in finger_specs:
        fx = cx + dx * s - finger_w / 2
        fy = palm_y - h * s + top_off * s
        fh = (palm_y + 40 * s) - fy   # extend a bit into palm for clean union
        fingers.append(
            f'<rect x="{fx}" y="{fy}" width="{finger_w}" height="{fh}" '
            f'rx="{finger_w/2}" ry="{finger_w/2}" fill="{fill}"/>'
        )
    fingers_svg = "".join(fingers)
    # thumb — angled blob on the lower-left of palm
    thumb_cx = cx - 180 * s
    thumb_cy = cy + 140 * s
    thumb = (
        f'<g transform="translate({thumb_cx} {thumb_cy}) rotate(-25)">'
        f'<rect x="{-100*s}" y="{-50*s}" width="{180*s}" height="{100*s}" '
        f'rx="{50*s}" ry="{50*s}" fill="{fill}"/>'
        f'</g>'
    )
    return thumb + palm + fingers_svg


def pointing_hand(cx: float, cy: float, scale: float = 1.0,
                  rotate: float = 0.0,
                  fill: str = "url(#grad-teal)") -> str:
    """Hand silhouette with index finger extended, others curled.

    Anchor is roughly the wrist; finger points in the direction of `rotate`
    (0 = up, 90 = right, etc.).
    """
    s = scale
    body = []
    # palm/fist
    body.append(
        f'<rect x="{-130*s}" y="{-40*s}" width="{260*s}" height="{260*s}" '
        f'rx="{80*s}" ry="{80*s}" fill="{fill}"/>'
    )
    # extended index finger (going up)
    finger_w = 70 * s
    body.append(
        f'<rect x="{-finger_w/2}" y="{-380*s}" width="{finger_w}" height="{420*s}" '
        f'rx="{finger_w/2}" ry="{finger_w/2}" fill="{fill}"/>'
    )
    # thumb on side
    body.append(
        f'<g transform="rotate(-30) translate({-130*s} {30*s})">'
        f'<rect x="{-90*s}" y="{-40*s}" width="{160*s}" height="{80*s}" '
        f'rx="{40*s}" ry="{40*s}" fill="{fill}"/>'
        f'</g>'
    )
    inner = "".join(body)
    return f'<g transform="translate({cx} {cy}) rotate({rotate})">{inner}</g>'


# ---------------------------------------------------------------------------
# N1 — Open Hand + Haptic Waves   (homage to ref Image 1)
# ---------------------------------------------------------------------------
def mark_hand_waves() -> str:
    hand = open_hand(420, 540, scale=1.0, fill="url(#grad-teal)")
    # 3 wave arcs to the right — matching gradient
    waves = []
    for i, r in enumerate([90, 150, 210]):
        cx = 760
        cy = 480
        opacity = 0.95 - i * 0.18
        sw = 36 - i * 4
        waves.append(
            f'<path d="M {cx} {cy-r} A {r} {r} 0 0 1 {cx} {cy+r}" '
            f'fill="none" stroke="url(#grad-teal)" stroke-width="{sw}" '
            f'stroke-linecap="round" opacity="{opacity}"/>'
        )
    return svg(hand + "".join(waves))


# ---------------------------------------------------------------------------
# N2 — Pointing Finger Touching Cube  (proper hand into AR cube)
# ---------------------------------------------------------------------------
def mark_finger_cube() -> str:
    # cube at upper right
    cx, cy = 700, 380
    s = 200
    rx, ry = math.cos(math.radians(30)), math.sin(math.radians(30))
    top = (cx, cy - s)
    right = (cx + s * rx, cy - s + s * ry)
    left = (cx - s * rx, cy - s + s * ry)
    midR = (cx + s * rx, cy + s * ry)
    midL = (cx - s * rx, cy + s * ry)
    bottom = (cx, cy + 2 * s * ry)
    center = (cx, cy - s + 2 * s * ry)
    cube = f"""
      <g fill="none" stroke="{NAVY}" stroke-width="20" stroke-linejoin="round"
         stroke-linecap="round">
        <polygon points="{top[0]},{top[1]} {right[0]:.0f},{right[1]:.0f} {midR[0]:.0f},{midR[1]:.0f} {bottom[0]},{bottom[1]} {midL[0]:.0f},{midL[1]:.0f} {left[0]:.0f},{left[1]:.0f}"/>
        <polyline points="{top[0]},{top[1]} {center[0]:.0f},{center[1]:.0f} {left[0]:.0f},{left[1]:.0f}" stroke-width="14" opacity="0.45"/>
        <line x1="{right[0]:.0f}" y1="{right[1]:.0f}" x2="{center[0]:.0f}" y2="{center[1]:.0f}" stroke-width="14" opacity="0.45"/>
        <line x1="{center[0]:.0f}" y1="{center[1]:.0f}" x2="{bottom[0]}" y2="{bottom[1]}" stroke-width="14" opacity="0.45"/>
      </g>
    """
    # pointing hand from lower-left, index toward cube center
    # rotate so finger points up-right (~ -45°)
    hand = pointing_hand(380, 780, scale=0.85, rotate=35,
                         fill="url(#grad-teal)")
    # tap dot at the cube vertex the finger is heading toward
    tap = f'<circle cx="{center[0]:.0f}" cy="{center[1]:.0f}" r="28" fill="{AMBER}"/>'
    return svg(cube + hand + tap)


# ---------------------------------------------------------------------------
# N3 — Hand Cradling Cube  (haptic + AR, friendly)
# ---------------------------------------------------------------------------
def mark_hand_cradle() -> str:
    # open hand at bottom, palm-up (rotated)
    # easiest: draw open_hand pointing up but place cube above it
    hand = open_hand(512, 700, scale=0.95, fill="url(#grad-teal)")
    # iso cube cradled above palm
    cx, cy = 512, 320
    s = 140
    rx, ry = math.cos(math.radians(30)), math.sin(math.radians(30))
    top = (cx, cy - s)
    right = (cx + s * rx, cy - s + s * ry)
    left = (cx - s * rx, cy - s + s * ry)
    midR = (cx + s * rx, cy + s * ry)
    midL = (cx - s * rx, cy + s * ry)
    bottom = (cx, cy + 2 * s * ry)
    center = (cx, cy - s + 2 * s * ry)
    cube = f"""
      <g stroke="{NAVY}" stroke-width="14" stroke-linejoin="round" stroke-linecap="round">
        <polygon points="{top[0]},{top[1]} {right[0]:.0f},{right[1]:.0f} {midR[0]:.0f},{midR[1]:.0f} {bottom[0]},{bottom[1]} {midL[0]:.0f},{midL[1]:.0f} {left[0]:.0f},{left[1]:.0f}"
                 fill="white"/>
        <polygon points="{top[0]},{top[1]} {right[0]:.0f},{right[1]:.0f} {center[0]:.0f},{center[1]:.0f} {left[0]:.0f},{left[1]:.0f}"
                 fill="{AMBER}" opacity="0.85"/>
        <polygon points="{left[0]:.0f},{left[1]:.0f} {center[0]:.0f},{center[1]:.0f} {bottom[0]},{bottom[1]} {midL[0]:.0f},{midL[1]:.0f}"
                 fill="{NAVY}" opacity="0.18"/>
      </g>
    """
    return svg(hand + cube)


# ---------------------------------------------------------------------------
# N4 — Orbital Triad   (homage to ref Image 4 — multi-color dots)
# ---------------------------------------------------------------------------
def mark_orbital_triad() -> str:
    cx, cy = 512, 512
    r = 320
    # ring
    body = [
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
        f'stroke="{NAVY}" stroke-width="14"/>'
    ]
    # 3 orbital dots, 120° apart
    palette = [TEAL_LO, AMBER, CRIMSON]
    for i, col in enumerate(palette):
        a = math.radians(-90 + i * 120)
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a)
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="64" fill="{col}"/>')
    # center origin dot (axis = origin where 3 dimensions meet)
    body.append(f'<circle cx="{cx}" cy="{cy}" r="44" fill="{NAVY}"/>')
    # short axis spokes from center to each dot (subtle)
    for i in range(3):
        a = math.radians(-90 + i * 120)
        x2 = cx + (r - 70) * math.cos(a)
        y2 = cy + (r - 70) * math.sin(a)
        body.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{NAVY}" stroke-width="10" opacity="0.35" stroke-linecap="round"/>'
        )
    return svg("".join(body))


# ---------------------------------------------------------------------------
# N5 — Three Figures Triad   (homage to ref Image 2 — collaborative people)
# ---------------------------------------------------------------------------
def mark_three_figures() -> str:
    cx, cy = 512, 540
    out = []
    # central larger figure (back view at workstation) + 2 flanking
    figure_specs = [
        (cx - 280, cy + 30, 0.85, TEAL_LO),
        (cx,       cy,      1.05, NAVY),
        (cx + 280, cy + 30, 0.85, AMBER),
    ]
    for fx, fy, scale, color in figure_specs:
        head_r = 70 * scale
        head_y = fy - 160 * scale
        body_w = 220 * scale
        body_h = 260 * scale
        body_x = fx - body_w / 2
        body_y = fy - 60 * scale
        # head (ring) + body (rounded rect, open bottom)
        out.append(
            f'<circle cx="{fx}" cy="{head_y}" r="{head_r}" '
            f'fill="none" stroke="{color}" stroke-width="22"/>'
        )
        out.append(
            f'<path d="M {body_x} {body_y + body_h} '
            f'L {body_x} {body_y + 40*scale} '
            f'Q {body_x} {body_y} {body_x + 40*scale} {body_y} '
            f'L {body_x + body_w - 40*scale} {body_y} '
            f'Q {body_x + body_w} {body_y} {body_x + body_w} {body_y + 40*scale} '
            f'L {body_x + body_w} {body_y + body_h}" '
            f'fill="none" stroke="{color}" stroke-width="22" stroke-linejoin="round"/>'
        )
    # connecting "interaction" dots between figures (small + above)
    for i in range(2):
        x = cx - 140 + i * 280
        out.append(f'<circle cx="{x}" cy="{cy - 220}" r="12" fill="{CRIMSON}"/>')
    return svg("".join(out))


# ---------------------------------------------------------------------------
# N6 — Two-Hand Handshake (Human ↔ Computer)
#   One hand in teal gradient, one hand in amber, fingertips meeting at a
#   spark. The "human-computer" handshake — quintessential HCI.
# ---------------------------------------------------------------------------
def mark_two_hands() -> str:
    # left hand pointing right (rotate 90)
    left = pointing_hand(200, 540, scale=0.7, rotate=90,
                         fill="url(#grad-teal)")
    # right hand pointing left (rotate -90)
    right = pointing_hand(824, 484, scale=0.7, rotate=-90,
                          fill="url(#grad-warm)")
    # spark where fingertips meet (around x=512)
    spark = f"""
      <g>
        <circle cx="512" cy="512" r="60" fill="{NAVY}" opacity="0.08"/>
        <circle cx="512" cy="512" r="36" fill="{CRIMSON}"/>
        <g stroke="{CRIMSON}" stroke-width="10" stroke-linecap="round">
          <line x1="512" y1="430" x2="512" y2="400"/>
          <line x1="512" y1="594" x2="512" y2="624"/>
          <line x1="430" y1="512" x2="400" y2="512"/>
          <line x1="594" y1="512" x2="624" y2="512"/>
        </g>
      </g>
    """
    return svg(left + right + spark)


# ---------------------------------------------------------------------------
# Contact sheet
# ---------------------------------------------------------------------------
def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    search_dirs = [
        "/System/Library/Fonts/",
        "/System/Library/Fonts/Supplemental/",
        "/Library/Fonts/",
        str(Path.home() / "Library" / "Fonts"),
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
    cell = 700
    pad = 40
    cols, rows = 3, 2
    label_h = 60
    title_h = 100
    width = cols * cell + (cols + 1) * pad
    height = title_h + rows * (cell + label_h) + (rows + 1) * pad

    canvas = Image.new("RGB", (width, height), color="#FAFAF7")
    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 44)
    label_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 26)
    draw.text((width // 2, title_h // 2),
              "AXIS Lab — Symbol Marks v2 (hand · color)",
              font=title_font, fill="#0A0A0A", anchor="mm")
    for i, (p, label) in enumerate(zip(paths, labels)):
        col = i % cols
        row = i // cols
        x = pad + col * (cell + pad)
        y = title_h + pad + row * (cell + label_h + pad)
        img = Image.open(p).convert("RGBA")
        img = img.resize((cell, cell), Image.LANCZOS)
        canvas.paste(img, (x, y), img)
        draw.rectangle([x, y, x + cell - 1, y + cell - 1],
                       outline="#E0E0E0", width=2)
        draw.text((x + cell // 2, y + cell + label_h // 2), label,
                  font=label_font, fill="#0A0A0A", anchor="mm")
    canvas.save(out_path, "PNG")


def main() -> None:
    print("Generating AXIS Lab v2 marks ...")
    marks = [
        ("n1_hand_waves",      mark_hand_waves,     "N1 · Hand + Haptic Waves"),
        ("n2_finger_cube",     mark_finger_cube,    "N2 · Finger → Cube"),
        ("n3_hand_cradle",     mark_hand_cradle,    "N3 · Hand Cradling Cube"),
        ("n4_orbital_triad",   mark_orbital_triad,  "N4 · Orbital Triad"),
        ("n5_three_figures",   mark_three_figures,  "N5 · Three Figures"),
        ("n6_two_hands",       mark_two_hands,      "N6 · Human ↔ Computer"),
    ]
    paths, labels = [], []
    for slug, fn, label in marks:
        paths.append(write_pair(f"axis_{slug}", fn()))
        labels.append(label)
    build_contact_sheet(paths, labels, OUT / "_v2_contact_sheet.png")
    print(f"  contact sheet → {(OUT / '_v2_contact_sheet.png').relative_to(ROOT)}")
    print("done.")


if __name__ == "__main__":
    main()
