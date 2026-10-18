"""AXIS Lab — 12 mark concepts beyond the letter A.

Two batches × 6 marks. P1 palette (ink + crimson pop).

Batch S — spatial / axis without leaning on the letter A:
  S1 · Vector Triad     — XYZ arrows in 3D perspective from origin
  S2 · Iso Cube         — wireframe cube with crimson vertex highlight
  S3 · Wireframe Sphere — globe with polar axis (3D / spatial)
  S4 · Lens Aperture    — 6-blade camera iris (perception / observation)
  S5 · Iso Layer Stack  — 3 stacked iso planes (AR / spatial layers)
  S6 · Constellation    — 3 connected nodes (graph / axis triad)

Batch I — interaction / sensory:
  I1 · Radial Pulse     — center tap + concentric haptic rings
  I2 · Tuning Fork      — fork with vibration arcs (resonance / haptic)
  I3 · Cursor Cross     — pointer at coordinate cross intersection
  I4 · Eye Reticle      — eye with crosshair pupil (gaze / AR)
  I5 · Hand + Sphere    — hand cradling a wireframe sphere
  I6 · Swipe Trail      — motion trail of fading touch dots (gesture)
"""
from __future__ import annotations

import math
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "logos" / "ideas2"
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


# =============================================================================
# Batch S — Spatial / Geometric
# =============================================================================

# S1 · Vector Triad — three coordinate-axis arrows from origin in perspective.
def s1_vector_triad() -> str:
    cx, cy = 512, 580
    L = 360
    # Y up
    yx, yy = cx, cy - L
    # X right (slight downward perspective)
    xang = math.radians(-12)
    xx = cx + L * math.cos(xang)
    xy = cy + L * math.sin(xang)
    # Z back-left
    zang = math.radians(180 - 30)
    zx = cx + L * math.cos(zang)
    zy = cy + L * math.sin(zang)
    body = f"""
      <line x1="{cx}" y1="{cy}" x2="{yx}" y2="{yy}"
            stroke="{INK}" stroke-width="42" stroke-linecap="round"
            marker-end="url(#arr)"/>
      <line x1="{cx}" y1="{cy}" x2="{xx:.1f}" y2="{xy:.1f}"
            stroke="{INK}" stroke-width="42" stroke-linecap="round"
            marker-end="url(#arr)"/>
      <line x1="{cx}" y1="{cy}" x2="{zx:.1f}" y2="{zy:.1f}"
            stroke="{INK}" stroke-width="42" stroke-linecap="round"
            marker-end="url(#arr)"/>
      <circle cx="{cx}" cy="{cy}" r="38" fill="{CRIM}"/>
    """
    return svg(body)


# S2 · Iso Cube — wireframe cube with crimson vertex highlight.
def s2_iso_cube() -> str:
    cx, cy = 512, 540
    s = 320
    rx, ry = math.cos(math.radians(30)), math.sin(math.radians(30))
    top = (cx, cy - s)
    right = (cx + s * rx, cy - s + s * ry)
    left = (cx - s * rx, cy - s + s * ry)
    midR = (cx + s * rx, cy + s * ry)
    midL = (cx - s * rx, cy + s * ry)
    bottom = (cx, cy + 2 * s * ry)
    center = (cx, cy - s + 2 * s * ry)
    body = f"""
      <g stroke="{INK}" stroke-width="34" stroke-linejoin="round"
         stroke-linecap="round" fill="none">
        <polygon points="{top[0]},{top[1]} {right[0]:.0f},{right[1]:.0f}
                         {midR[0]:.0f},{midR[1]:.0f} {bottom[0]},{bottom[1]}
                         {midL[0]:.0f},{midL[1]:.0f} {left[0]:.0f},{left[1]:.0f}"/>
        <line x1="{top[0]}" y1="{top[1]}" x2="{center[0]:.0f}" y2="{center[1]:.0f}"
              stroke-width="22" opacity="0.55"/>
        <line x1="{left[0]:.0f}" y1="{left[1]:.0f}" x2="{center[0]:.0f}" y2="{center[1]:.0f}"
              stroke-width="22" opacity="0.55"/>
        <line x1="{right[0]:.0f}" y1="{right[1]:.0f}" x2="{center[0]:.0f}" y2="{center[1]:.0f}"
              stroke-width="22" opacity="0.55"/>
      </g>
      <circle cx="{center[0]:.0f}" cy="{center[1]:.0f}" r="40" fill="{CRIM}"/>
    """
    return svg(body)


# S3 · Wireframe Sphere — globe with polar axis line.
def s3_sphere() -> str:
    cx, cy = 512, 512
    r = 340
    body = f"""
      <g fill="none" stroke="{INK}" stroke-linecap="round">
        <circle cx="{cx}" cy="{cy}" r="{r}" stroke-width="26"/>
        <ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r*0.34}" stroke-width="14"/>
        <ellipse cx="{cx}" cy="{cy}" rx="{r*0.55}" ry="{r}" stroke-width="14" opacity="0.6"/>
        <ellipse cx="{cx}" cy="{cy}" rx="{r*0.34}" ry="{r}" stroke-width="14" opacity="0.4"/>
      </g>
      <line x1="{cx}" y1="{cy-r-60}" x2="{cx}" y2="{cy+r+60}"
            stroke="{INK}" stroke-width="20" stroke-linecap="round"/>
      <circle cx="{cx}" cy="{cy-r-60}" r="32" fill="{CRIM}"/>
    """
    return svg(body)


# S4 · Lens Aperture — 6 triangular blades arranged in iris pattern.
def s4_aperture() -> str:
    cx, cy = 512, 512
    inner = 110     # central opening radius
    outer = 380     # outer reach
    blades = []
    for i in range(6):
        a0 = math.radians(-90 + i * 60)
        a1 = math.radians(-90 + (i + 1) * 60)
        ax = cx + inner * math.cos(a0)
        ay = cy + inner * math.sin(a0)
        bx = cx + outer * math.cos(a0 + math.radians(20))
        by = cy + outer * math.sin(a0 + math.radians(20))
        cxp = cx + inner * math.cos(a1)
        cyp = cy + inner * math.sin(a1)
        blades.append(
            f'<polygon points="{ax:.1f},{ay:.1f} {bx:.1f},{by:.1f} '
            f'{cxp:.1f},{cyp:.1f}" fill="{INK}"/>'
        )
    # central hexagonal opening (white) — make sure aperture eye is visible
    hex_pts = []
    for i in range(6):
        a = math.radians(-90 + i * 60)
        hex_pts.append(f"{cx + inner * math.cos(a):.1f},{cy + inner * math.sin(a):.1f}")
    body = (
        "".join(blades)
        + f'<polygon points="{" ".join(hex_pts)}" fill="white" stroke="{INK}" stroke-width="6"/>'
        + f'<circle cx="{cx}" cy="{cy}" r="34" fill="{CRIM}"/>'
    )
    return svg(body)


# S5 · Iso Layer Stack — 3 stacked iso parallelograms (AR layers).
def s5_layer_stack() -> str:
    cx = 512
    cys = [380, 520, 660]   # 3 layer y-centers
    w = 380
    h = 130
    body = []
    rx = math.cos(math.radians(30))
    ry = math.sin(math.radians(30))
    for i, ccy in enumerate(cys):
        # parallelogram (top-down iso plate)
        top = (cx, ccy - h / 2)
        right = (cx + w / 2 * rx, ccy - h / 2 + w / 2 * ry * 0.5)
        bottom = (cx, ccy + h / 2)
        left = (cx - w / 2 * rx, ccy + h / 2 - w / 2 * ry * 0.5)
        body.append(
            f'<polygon points="{top[0]:.0f},{top[1]:.0f} '
            f'{right[0]:.0f},{right[1]:.0f} '
            f'{bottom[0]:.0f},{bottom[1]:.0f} '
            f'{left[0]:.0f},{left[1]:.0f}" '
            f'fill="white" stroke="{INK}" stroke-width="22" stroke-linejoin="round"/>'
        )
    body.append(f'<circle cx="{cx}" cy="{cys[0]}" r="34" fill="{CRIM}"/>')
    return svg("".join(body))


# S6 · Constellation Triad — 3 connected nodes (graph + axis).
def s6_constellation() -> str:
    cx, cy = 512, 540
    r = 280
    pts = []
    for i in range(3):
        a = math.radians(-90 + i * 120)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    edges = "".join(
        f'<line x1="{pts[i][0]:.1f}" y1="{pts[i][1]:.1f}" '
        f'x2="{pts[(i+1)%3][0]:.1f}" y2="{pts[(i+1)%3][1]:.1f}" '
        f'stroke="{INK}" stroke-width="22" stroke-linecap="round"/>'
        for i in range(3)
    )
    nodes = (
        f'<circle cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}" r="56" fill="{CRIM}"/>'
        + f'<circle cx="{pts[1][0]:.1f}" cy="{pts[1][1]:.1f}" r="56" fill="{INK}"/>'
        + f'<circle cx="{pts[2][0]:.1f}" cy="{pts[2][1]:.1f}" r="56" fill="{INK}"/>'
        + f'<circle cx="{cx}" cy="{cy}" r="20" fill="{INK}"/>'
    )
    # spokes from center to each node
    spokes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{p[0]:.1f}" y2="{p[1]:.1f}" '
        f'stroke="{INK}" stroke-width="10" opacity="0.35" stroke-linecap="round"/>'
        for p in pts
    )
    return svg(spokes + edges + nodes)


# =============================================================================
# Batch I — Interaction / Sensory
# =============================================================================

# I1 · Radial Pulse — concentric haptic rings around a tap point.
def i1_radial_pulse() -> str:
    cx, cy = 512, 512
    body = f"""
      <g fill="none" stroke="{INK}" stroke-linecap="round">
        <circle cx="{cx}" cy="{cy}" r="160" stroke-width="26"/>
        <circle cx="{cx}" cy="{cy}" r="260" stroke-width="22" opacity="0.65"/>
        <circle cx="{cx}" cy="{cy}" r="360" stroke-width="18" opacity="0.35"/>
      </g>
      <circle cx="{cx}" cy="{cy}" r="78" fill="{CRIM}"/>
    """
    return svg(body)


# I2 · Tuning Fork — vibration source.
def i2_tuning_fork() -> str:
    cx = 512
    body = f"""
      <g stroke="{INK}" stroke-linecap="round" stroke-linejoin="round" fill="none">
        <!-- two tines -->
        <line x1="{cx-90}" y1="170" x2="{cx-90}" y2="640" stroke-width="42"/>
        <line x1="{cx+90}" y1="170" x2="{cx+90}" y2="640" stroke-width="42"/>
        <!-- joining base U -->
        <path d="M {cx-90} 640 Q {cx-90} 720 {cx-30} 720
                 L {cx+30} 720 Q {cx+90} 720 {cx+90} 640" stroke-width="42"/>
        <!-- handle -->
        <line x1="{cx}" y1="720" x2="{cx}" y2="850" stroke-width="42"/>
        <!-- vibration arcs -->
        <path d="M {cx-180} 280 Q {cx-220} 380 {cx-180} 480" stroke-width="20" opacity="0.55"/>
        <path d="M {cx+180} 280 Q {cx+220} 380 {cx+180} 480" stroke-width="20" opacity="0.55"/>
        <path d="M {cx-240} 240 Q {cx-300} 380 {cx-240} 520" stroke-width="16" opacity="0.3"/>
        <path d="M {cx+240} 240 Q {cx+300} 380 {cx+240} 520" stroke-width="16" opacity="0.3"/>
      </g>
      <circle cx="{cx}" cy="850" r="38" fill="{CRIM}"/>
    """
    return svg(body)


# I3 · Cursor Cross — pointer at coordinate cross intersection.
def i3_cursor_cross() -> str:
    cx, cy = 512, 512
    cross = f"""
      <g stroke="{INK}" stroke-width="26" stroke-linecap="round">
        <line x1="160" y1="{cy}" x2="864" y2="{cy}"/>
        <line x1="{cx}" y1="160" x2="{cx}" y2="864"/>
      </g>
    """
    cur = f"""
      <path d="M {cx} {cy}
               L {cx+200} {cy+86}
               L {cx+108} {cy+102}
               L {cx+170} {cy+250}
               L {cx+118} {cy+270}
               L {cx+58} {cy+126}
               L {cx-22} {cy+186}
               Z"
            fill="{CRIM}" stroke="{INK}" stroke-width="14"
            stroke-linejoin="round"/>
    """
    return svg(cross + cur)


# I4 · Eye Reticle — eye with crosshair pupil.
def i4_eye_reticle() -> str:
    cx, cy = 512, 512
    eye = f"""
      <path d="M 180 {cy} Q 512 250 844 {cy} Q 512 774 180 {cy} Z"
            fill="none" stroke="{INK}" stroke-width="30" stroke-linejoin="round"/>
      <circle cx="{cx}" cy="{cy}" r="150" fill="white" stroke="{INK}" stroke-width="22"/>
      <g stroke="{INK}" stroke-width="14" stroke-linecap="round">
        <line x1="{cx-110}" y1="{cy}" x2="{cx-50}" y2="{cy}"/>
        <line x1="{cx+50}" y1="{cy}" x2="{cx+110}" y2="{cy}"/>
        <line x1="{cx}" y1="{cy-110}" x2="{cx}" y2="{cy-50}"/>
        <line x1="{cx}" y1="{cy+50}" x2="{cx}" y2="{cy+110}"/>
      </g>
      <circle cx="{cx}" cy="{cy}" r="32" fill="{CRIM}"/>
    """
    return svg(eye)


# I5 · Hand + Sphere — hand cradling a wireframe sphere.
def _open_hand(cx, cy, scale=1.0, fill=INK):
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


def i5_hand_sphere() -> str:
    hand = _open_hand(512, 760, scale=0.78, fill=INK)
    cx, cy = 512, 360
    r = 180
    sphere = f"""
      <g fill="none" stroke="{INK}" stroke-linecap="round">
        <circle cx="{cx}" cy="{cy}" r="{r}" stroke-width="18"/>
        <ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r*0.32}" stroke-width="10"/>
        <ellipse cx="{cx}" cy="{cy}" rx="{r*0.5}" ry="{r}" stroke-width="10" opacity="0.55"/>
      </g>
      <circle cx="{cx}" cy="{cy-r-30}" r="26" fill="{CRIM}"/>
    """
    return svg(hand + sphere)


# I6 · Swipe Trail — fading dots along a curved gesture path.
def i6_swipe_trail() -> str:
    # 5 dots along a left-to-right arc, fading
    pts = [(220, 660), (340, 540), (480, 460), (640, 440), (820, 480)]
    body = []
    sizes = [22, 30, 38, 50, 70]
    opacities = [0.25, 0.4, 0.6, 0.8, 1.0]
    for i, (p, sz, op) in enumerate(zip(pts, sizes, opacities)):
        col = CRIM if i == len(pts) - 1 else INK
        body.append(
            f'<circle cx="{p[0]}" cy="{p[1]}" r="{sz}" fill="{col}" '
            f'opacity="{op}"/>'
        )
    # subtle curve through the points
    path_d = "M " + " L ".join(f"{p[0]} {p[1]}" for p in pts)
    body.insert(
        0,
        f'<path d="{path_d}" fill="none" stroke="{INK}" stroke-width="14" '
        f'stroke-linecap="round" opacity="0.18"/>'
    )
    # arrow head at trailing end (right)
    body.append(
        f'<path d="M 820 480 L 760 440 L 760 520 Z" fill="{CRIM}"/>'
    )
    return svg("".join(body))


# =============================================================================
# Contact sheets
# =============================================================================
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
                        title: str, out_path: Path,
                        cols: int = 3, rows: int = 2) -> None:
    cell, pad, label_h, title_h = 700, 40, 60, 100
    width = cols * cell + (cols + 1) * pad
    height = title_h + rows * (cell + label_h) + (rows + 1) * pad
    canvas = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 44)
    label_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 26)
    draw.text((width // 2, title_h // 2), title,
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
    print("Generating AXIS Lab v4 ideas (no letter A) ...")
    batch_s = [
        ("s1_vector_triad",  s1_vector_triad,  "S1 · Vector Triad"),
        ("s2_iso_cube",      s2_iso_cube,      "S2 · Iso Cube"),
        ("s3_sphere",        s3_sphere,        "S3 · Wireframe Sphere"),
        ("s4_aperture",      s4_aperture,      "S4 · Lens Aperture"),
        ("s5_layer_stack",   s5_layer_stack,   "S5 · Iso Layer Stack"),
        ("s6_constellation", s6_constellation, "S6 · Constellation"),
    ]
    batch_i = [
        ("i1_radial_pulse",  i1_radial_pulse,  "I1 · Radial Pulse"),
        ("i2_tuning_fork",   i2_tuning_fork,   "I2 · Tuning Fork"),
        ("i3_cursor_cross",  i3_cursor_cross,  "I3 · Cursor Cross"),
        ("i4_eye_reticle",   i4_eye_reticle,   "I4 · Eye Reticle"),
        ("i5_hand_sphere",   i5_hand_sphere,   "I5 · Hand + Sphere"),
        ("i6_swipe_trail",   i6_swipe_trail,   "I6 · Swipe Trail"),
    ]

    s_paths, s_labels = [], []
    for slug, fn, label in batch_s:
        s_paths.append(write_pair(f"axis_{slug}", fn()))
        s_labels.append(label)
    build_contact_sheet(s_paths, s_labels,
                        "AXIS · Spatial concepts (Batch S)",
                        OUT / "_batch_S_contact.png")

    i_paths, i_labels = [], []
    for slug, fn, label in batch_i:
        i_paths.append(write_pair(f"axis_{slug}", fn()))
        i_labels.append(label)
    build_contact_sheet(i_paths, i_labels,
                        "AXIS · Interaction concepts (Batch I)",
                        OUT / "_batch_I_contact.png")
    print(f"  → {(OUT / '_batch_S_contact.png').relative_to(ROOT)}")
    print(f"  → {(OUT / '_batch_I_contact.png').relative_to(ROOT)}")
    print("done.")


if __name__ == "__main__":
    main()
