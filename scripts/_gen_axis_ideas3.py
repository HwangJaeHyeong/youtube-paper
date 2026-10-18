"""AXIS Lab — 30 fresh marks (5 batches × 6), nothing overlapping prior runs.

Already-used primitives I am NOT touching here (consult each prior contact
sheet before adding to this list):
  · concentric-ring ripple (M1, I1)        · letter A in any form (AX*, C*)
  · classic mouse cursor   (M2, I3, C3)    · sine wave to right (M5, B)
  · two-finger pinch dots  (M3)            · 3-axis triad arrows (S1, AX4)
  · iso cube outline       (M4, S2, AX5,   · orbital ring + 3 dots (N4, S6)
                            E, C4)         · open hand silhouette (N1-3, AX3, I5)
  · AR reticle / corner brackets (M6, C6)  · two hands handshake (N6)
  · 3 abstract people (N5)                 · wireframe sphere (S3, I5)
  · lens aperture (S4)                     · iso layer stack (S5)
  · tuning fork (I2)                       · eye+crosshair (I4)
  · swipe trail dots (I6)                  · triangle frame / atom orbit (C7,C8)

Five new families of primitives explored here:
  B1 · Math/coordinate diagrams (vector field, polar grid, …)
  B2 · Topology / curves        (Möbius, DNA, Bezier, knot, …)
  B3 · HCI devices              (VR headset, haptic glove, stylus, slider…)
  B4 · Pattern / lattice        (perspective grid, honeycomb, particles…)
  B5 · Korean distinctive       (taegeuk-axis, bow arc, mountain triad,…)

Palette: P1 (ink #0A0A0A + crimson #862633 pop). 1024×1024 SVG + PNG each.
"""
from __future__ import annotations

import math
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "logos" / "ideas3"
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
      <marker id="arrSm" viewBox="0 0 10 10" refX="9" refY="5"
              markerWidth="3" markerHeight="3" orient="auto-start-reverse">
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
    print(f"  {sp.relative_to(ROOT)}")
    return pp


# =============================================================================
# B1 — Math / coordinate diagrams
# =============================================================================

def b1_1_vector_field() -> str:
    """Grid of small curved arrows flowing toward a focal crimson dot."""
    cx, cy = 512, 512
    rows = cols = 5
    spacing = 140
    body = []
    for i in range(cols):
        for j in range(rows):
            x = cx + (i - (cols - 1) / 2) * spacing
            y = cy + (j - (rows - 1) / 2) * spacing
            # curve toward focal: arrow tangent to circle around focal
            dx, dy = cx - x, cy - y
            d = math.hypot(dx, dy) + 1e-6
            # tangent direction (perpendicular to radial)
            tx, ty = -dy / d, dx / d
            length = 70
            x2 = x + tx * length
            y2 = y + ty * length
            if abs(dx) < 1 and abs(dy) < 1:
                continue   # skip center
            body.append(
                f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
                f'stroke="{INK}" stroke-width="9" stroke-linecap="round" '
                f'marker-end="url(#arrSm)"/>'
            )
    body.append(f'<circle cx="{cx}" cy="{cy}" r="50" fill="{CRIM}"/>')
    return svg("".join(body))


def b1_2_polar_grid() -> str:
    """Concentric circles + radial spokes, crimson focal dot."""
    cx, cy = 512, 512
    body = []
    for r in (110, 220, 330, 440):
        body.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
            f'stroke="{INK}" stroke-width="10" opacity="0.55"/>'
        )
    for i in range(8):
        a = math.radians(i * 45)
        x2 = cx + 460 * math.cos(a)
        y2 = cy + 460 * math.sin(a)
        body.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{INK}" stroke-width="10" stroke-linecap="round" opacity="0.55"/>'
        )
    body.append(f'<circle cx="{cx}" cy="{cy}" r="38" fill="{CRIM}"/>')
    return svg("".join(body))


def b1_3_quadrant_grid() -> str:
    """A single 2D quadrant with grid lines, X & Y axis arrows, origin dot."""
    ox, oy = 220, 800   # origin (lower-left)
    span = 600
    body = []
    # grid lines
    for k in range(1, 6):
        d = (span / 6) * k
        body.append(
            f'<line x1="{ox+d:.0f}" y1="{oy}" x2="{ox+d:.0f}" y2="{oy-span}" '
            f'stroke="{INK}" stroke-width="6" opacity="0.25"/>'
        )
        body.append(
            f'<line x1="{ox}" y1="{oy-d:.0f}" x2="{ox+span}" y2="{oy-d:.0f}" '
            f'stroke="{INK}" stroke-width="6" opacity="0.25"/>'
        )
    # axes
    body.append(
        f'<line x1="{ox}" y1="{oy}" x2="{ox+span+40}" y2="{oy}" '
        f'stroke="{INK}" stroke-width="22" stroke-linecap="round" '
        f'marker-end="url(#arr)"/>'
    )
    body.append(
        f'<line x1="{ox}" y1="{oy}" x2="{ox}" y2="{oy-span-40}" '
        f'stroke="{INK}" stroke-width="22" stroke-linecap="round" '
        f'marker-end="url(#arr)"/>'
    )
    body.append(f'<circle cx="{ox}" cy="{oy}" r="34" fill="{CRIM}"/>')
    return svg("".join(body))


def b1_4_bounding_box() -> str:
    """Wireframe rectangular prism (NOT cube) with crimson corner."""
    cx, cy = 512, 540
    w, h, d = 460, 280, 200
    rx = math.cos(math.radians(30))
    ry = math.sin(math.radians(30))
    # 8 corners
    half_w, half_h = w / 2, h / 2
    front_tl = (cx - half_w, cy - half_h)
    front_tr = (cx + half_w, cy - half_h)
    front_bl = (cx - half_w, cy + half_h)
    front_br = (cx + half_w, cy + half_h)
    back_tl = (front_tl[0] + d * rx, front_tl[1] - d * ry)
    back_tr = (front_tr[0] + d * rx, front_tr[1] - d * ry)
    back_bl = (front_bl[0] + d * rx, front_bl[1] - d * ry)
    back_br = (front_br[0] + d * rx, front_br[1] - d * ry)

    def line(p1, p2, sw=22, op=1.0):
        return (
            f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" '
            f'x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" stroke="{INK}" '
            f'stroke-width="{sw}" stroke-linecap="round" opacity="{op}"/>'
        )
    body = []
    # front face
    for p1, p2 in [(front_tl, front_tr), (front_tr, front_br),
                   (front_br, front_bl), (front_bl, front_tl)]:
        body.append(line(p1, p2))
    # back face (lighter)
    for p1, p2 in [(back_tl, back_tr), (back_tr, back_br),
                   (back_br, back_bl), (back_bl, back_tl)]:
        body.append(line(p1, p2, op=0.45))
    # connectors
    for p1, p2 in [(front_tl, back_tl), (front_tr, back_tr),
                   (front_br, back_br), (front_bl, back_bl)]:
        body.append(line(p1, p2, op=0.45))
    body.append(
        f'<circle cx="{front_tl[0]:.1f}" cy="{front_tl[1]:.1f}" r="34" fill="{CRIM}"/>'
    )
    return svg("".join(body))


def b1_5_topographic() -> str:
    """Concentric irregular contour curves (topo map)."""
    cx, cy = 512, 540
    body = []
    for i, (r, op) in enumerate([(140, 1.0), (220, 0.7), (310, 0.5), (400, 0.3)]):
        # build a gently irregular closed curve via cubic path
        pts = []
        for k in range(12):
            a = math.radians(k * 30)
            wobble = 1 + 0.06 * math.sin(3 * a + i)
            pts.append((cx + r * wobble * math.cos(a),
                        cy + r * 0.78 * wobble * math.sin(a)))
        d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
        body.append(
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="14" '
            f'stroke-linejoin="round" opacity="{op}"/>'
        )
    body.append(f'<circle cx="{cx}" cy="{cy}" r="38" fill="{CRIM}"/>')
    return svg("".join(body))


def b1_6_phase_spiral() -> str:
    """Archimedean spiral wound around origin."""
    cx, cy = 512, 512
    pts = []
    for i in range(401):
        t = i / 40   # turns
        r = 16 * t
        a = t
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a)
        pts.append((x, y))
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    body = (
        f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="22" '
        f'stroke-linecap="round"/>'
        f'<circle cx="{cx}" cy="{cy}" r="32" fill="{CRIM}"/>'
    )
    return svg(body)


# =============================================================================
# B2 — Topology / curves
# =============================================================================

def b2_1_mobius() -> str:
    """Möbius-strip stylized infinity loop with twist shading."""
    cx, cy = 512, 512
    rx, ry = 280, 160
    # left lobe
    left = (
        f'<ellipse cx="{cx - rx*0.6}" cy="{cy}" rx="{rx*0.7}" ry="{ry}" '
        f'fill="none" stroke="{INK}" stroke-width="32"/>'
    )
    right = (
        f'<ellipse cx="{cx + rx*0.6}" cy="{cy}" rx="{rx*0.7}" ry="{ry}" '
        f'fill="none" stroke="{INK}" stroke-width="32"/>'
    )
    # twist crossing band in the middle (creates Möbius illusion)
    twist = (
        f'<path d="M {cx-50} {cy-40} Q {cx} {cy-110} {cx+50} {cy-40}" '
        f'fill="none" stroke="white" stroke-width="40"/>'
        f'<path d="M {cx-50} {cy+40} Q {cx} {cy+110} {cx+50} {cy+40}" '
        f'fill="none" stroke="white" stroke-width="40"/>'
    )
    dot = f'<circle cx="{cx}" cy="{cy}" r="34" fill="{CRIM}"/>'
    return svg(left + right + twist + dot)


def b2_2_dna_helix() -> str:
    """Vertical double-helix — two threads weaving."""
    cx = 512
    samples = 80
    body = []
    for thread, phase in enumerate([0, math.pi]):
        pts = []
        for i in range(samples + 1):
            t = i / samples
            y = 160 + t * 700
            x = cx + 130 * math.sin(2 * math.pi * 2 * t + phase)
            pts.append((x, y))
        d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        sw = 24 if thread == 0 else 24
        body.append(
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw}" '
            f'stroke-linecap="round"/>'
        )
    # rungs
    for k in range(8):
        t = (k + 0.5) / 8
        y = 160 + t * 700
        x1 = cx + 130 * math.sin(2 * math.pi * 2 * t)
        x2 = cx + 130 * math.sin(2 * math.pi * 2 * t + math.pi)
        body.append(
            f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" '
            f'stroke="{INK}" stroke-width="10" opacity="0.55"/>'
        )
    body.append(f'<circle cx="{cx}" cy="510" r="34" fill="{CRIM}"/>')
    return svg("".join(body))


def b2_3_bezier_curve() -> str:
    """Cubic Bezier with 2 control-point dots and handle lines."""
    p0 = (180, 760)
    p3 = (844, 280)
    p1 = (380, 200)
    p2 = (700, 820)
    body = (
        f'<line x1="{p0[0]}" y1="{p0[1]}" x2="{p1[0]}" y2="{p1[1]}" '
        f'stroke="{INK}" stroke-width="6" opacity="0.45" stroke-dasharray="14 14"/>'
        f'<line x1="{p3[0]}" y1="{p3[1]}" x2="{p2[0]}" y2="{p2[1]}" '
        f'stroke="{INK}" stroke-width="6" opacity="0.45" stroke-dasharray="14 14"/>'
        f'<path d="M {p0[0]} {p0[1]} C {p1[0]} {p1[1]} {p2[0]} {p2[1]} {p3[0]} {p3[1]}" '
        f'fill="none" stroke="{INK}" stroke-width="28" stroke-linecap="round"/>'
        f'<circle cx="{p0[0]}" cy="{p0[1]}" r="32" fill="{INK}"/>'
        f'<circle cx="{p3[0]}" cy="{p3[1]}" r="32" fill="{INK}"/>'
        f'<circle cx="{p1[0]}" cy="{p1[1]}" r="32" fill="{CRIM}"/>'
        f'<circle cx="{p2[0]}" cy="{p2[1]}" r="32" fill="{CRIM}"/>'
    )
    return svg(body)


def b2_4_trefoil_knot() -> str:
    """Parametric trefoil knot rendered as continuous curve."""
    cx, cy = 512, 512
    pts = []
    samples = 360
    for i in range(samples + 1):
        t = i / samples * 2 * math.pi
        r = 220
        x = cx + r * (math.sin(t) + 2 * math.sin(2 * t))
        y = cy + r * (math.cos(t) - 2 * math.cos(2 * t))
        # scale down because formula goes large
        x = cx + (x - cx) * 0.55
        y = cy + (y - cy) * 0.55
        pts.append((x, y))
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"
    body = (
        f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="32" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{cx}" cy="{cy}" r="40" fill="{CRIM}"/>'
    )
    return svg(body)


def b2_5_lemniscate() -> str:
    """Figure-8 lemniscate (Bernoulli)."""
    cx, cy = 512, 512
    pts = []
    samples = 400
    a = 320
    for i in range(samples + 1):
        t = -math.pi / 4 + i / samples * 2 * math.pi
        denom = 1 + math.sin(t) ** 2
        x = cx + (a * math.cos(t)) / denom
        y = cy + (a * math.sin(t) * math.cos(t)) / denom
        pts.append((x, y))
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    body = (
        f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="36" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{cx}" cy="{cy}" r="36" fill="{CRIM}"/>'
    )
    return svg(body)


def b2_6_echo_wave() -> str:
    """Three parallel sinusoids stacked vertically (NOT one sine + dot)."""
    body = []
    samples = 200
    for k, (yc, op, sw) in enumerate([(380, 0.4, 18),
                                      (512, 0.7, 24),
                                      (644, 1.0, 30)]):
        pts = []
        for i in range(samples + 1):
            t = i / samples
            x = 160 + t * 704
            y = yc - 80 * math.sin(2 * math.pi * 2.5 * t)
            pts.append((x, y))
        d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        body.append(
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{sw}" '
            f'stroke-linecap="round" opacity="{op}"/>'
        )
    body.append(f'<circle cx="160" cy="644" r="36" fill="{CRIM}"/>')
    return svg("".join(body))


# =============================================================================
# B3 — HCI devices
# =============================================================================

def b3_1_vr_headset() -> str:
    """VR / mixed-reality headset silhouette."""
    body = (
        # main body — rounded rect with split lens slits
        f'<rect x="180" y="380" width="664" height="280" rx="60" ry="60" '
        f'fill="{INK}"/>'
        # nose bridge
        f'<path d="M 480 660 Q 512 700 544 660" fill="{INK}"/>'
        # lens slits (eyeholes)
        f'<rect x="260" y="450" width="220" height="140" rx="40" ry="40" '
        f'fill="white"/>'
        f'<rect x="544" y="450" width="220" height="140" rx="40" ry="40" '
        f'fill="white"/>'
        # head strap
        f'<path d="M 180 480 Q 100 380 100 300 L 100 280" fill="none" '
        f'stroke="{INK}" stroke-width="22" stroke-linecap="round"/>'
        f'<path d="M 844 480 Q 924 380 924 300 L 924 280" fill="none" '
        f'stroke="{INK}" stroke-width="22" stroke-linecap="round"/>'
        # crimson indicator
        f'<circle cx="512" cy="425" r="20" fill="{CRIM}"/>'
    )
    return svg(body)


def b3_2_haptic_glove() -> str:
    """Glove silhouette with sensor dots on each fingertip."""
    cx, cy = 512, 600
    s = 1.0
    palm = (
        f'<rect x="{cx - 160*s}" y="{cy - 40*s}" width="{320*s}" '
        f'height="{300*s}" rx="{90*s}" ry="{90*s}" fill="{INK}"/>'
    )
    finger_specs = [(-130, 200, 30), (-50, 290, 0), (30, 320, -20), (110, 250, 10)]
    fingers = []
    sensor_pts = []
    fw = 64 * s
    for dx, h, top_off in finger_specs:
        fx = cx + dx * s - fw / 2
        fy = (cy - 40 * s) - h * s + top_off * s
        fh = (cy + 40 * s) - fy
        fingers.append(
            f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" '
            f'rx="{fw/2}" ry="{fw/2}" fill="{INK}"/>'
        )
        sensor_pts.append((cx + dx * s, fy + 30))
    thumb_cx = cx - 180 * s
    thumb_cy = cy + 140 * s
    thumb = (
        f'<g transform="translate({thumb_cx} {thumb_cy}) rotate(-25)">'
        f'<rect x="{-100*s}" y="{-50*s}" width="{180*s}" height="{100*s}" '
        f'rx="{50*s}" ry="{50*s}" fill="{INK}"/></g>'
    )
    sensors = "".join(
        f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="20" fill="{CRIM}"/>'
        for p in sensor_pts
    )
    return svg(thumb + palm + "".join(fingers) + sensors)


def b3_3_stylus() -> str:
    """Stylus pen tilted at angle, tap dot at the tip."""
    body = (
        f'<g transform="translate(512 512) rotate(-30)">'
        # body
        f'<rect x="-260" y="-30" width="500" height="60" rx="30" ry="30" '
        f'fill="{INK}"/>'
        # cone tip
        f'<polygon points="240,-30 320,0 240,30" fill="{INK}"/>'
        # back end
        f'<rect x="-280" y="-22" width="22" height="44" rx="10" ry="10" '
        f'fill="{INK}" opacity="0.6"/>'
        f'</g>'
        # tap point at tip — compute end-of-stylus position
    )
    # tip in world coords: rotate (320, 0) around (512, 512) by -30°
    a = math.radians(-30)
    tip_x = 512 + 320 * math.cos(a) - 0 * math.sin(a)
    tip_y = 512 + 320 * math.sin(a) + 0 * math.cos(a)
    body += f'<circle cx="{tip_x:.1f}" cy="{tip_y:.1f}" r="34" fill="{CRIM}"/>'
    # small ripple at tip
    body += (
        f'<circle cx="{tip_x:.1f}" cy="{tip_y:.1f}" r="70" fill="none" '
        f'stroke="{INK}" stroke-width="10" opacity="0.4"/>'
    )
    return svg(body)


def b3_4_smartphone() -> str:
    """Phone outline with finger touching screen (horizontal layout)."""
    body = (
        # phone body
        f'<rect x="220" y="260" width="584" height="280" rx="44" ry="44" '
        f'fill="none" stroke="{INK}" stroke-width="22"/>'
        # speaker / camera
        f'<circle cx="270" cy="400" r="14" fill="{INK}"/>'
        # screen content lines
        f'<rect x="320" y="320" width="380" height="20" rx="10" fill="{INK}" opacity="0.3"/>'
        f'<rect x="320" y="360" width="280" height="20" rx="10" fill="{INK}" opacity="0.3"/>'
        f'<rect x="320" y="400" width="320" height="20" rx="10" fill="{INK}" opacity="0.3"/>'
        # finger pointing down
        f'<rect x="660" y="540" width="80" height="280" rx="40" ry="40" fill="{INK}"/>'
        f'<rect x="640" y="780" width="160" height="100" rx="40" ry="40" fill="{INK}"/>'
        # tap point on screen
        f'<circle cx="700" cy="540" r="34" fill="{CRIM}"/>'
        f'<circle cx="700" cy="540" r="64" fill="none" stroke="{INK}" '
        f'stroke-width="10" opacity="0.45"/>'
    )
    return svg(body)


def b3_5_controller() -> str:
    """XR / game controller silhouette (twin-grip)."""
    body = (
        # left grip
        f'<path d="M 200 460 Q 160 460 160 540 Q 160 720 240 720 '
        f'Q 320 720 360 600 Z" fill="{INK}"/>'
        # right grip
        f'<path d="M 824 460 Q 864 460 864 540 Q 864 720 784 720 '
        f'Q 704 720 664 600 Z" fill="{INK}"/>'
        # body
        f'<path d="M 360 600 Q 360 380 512 380 Q 664 380 664 600 Z" fill="{INK}"/>'
        # stick / button
        f'<circle cx="380" cy="500" r="50" fill="white" stroke="{INK}" stroke-width="14"/>'
        f'<circle cx="380" cy="500" r="22" fill="{INK}"/>'
        # right buttons
        f'<circle cx="640" cy="470" r="22" fill="{CRIM}"/>'
        f'<circle cx="690" cy="510" r="22" fill="white" stroke="{INK}" stroke-width="10"/>'
        f'<circle cx="600" cy="510" r="22" fill="white" stroke="{INK}" stroke-width="10"/>'
        f'<circle cx="640" cy="550" r="22" fill="white" stroke="{INK}" stroke-width="10"/>'
    )
    return svg(body)


def b3_6_slider() -> str:
    """UI slider — track + handle, value tick marks."""
    body = (
        # filled track (left of handle)
        f'<line x1="180" y1="512" x2="640" y2="512" stroke="{INK}" '
        f'stroke-width="34" stroke-linecap="round"/>'
        # empty track (right of handle)
        f'<line x1="640" y1="512" x2="844" y2="512" stroke="{INK}" '
        f'stroke-width="34" stroke-linecap="round" opacity="0.25"/>'
        # tick marks
    )
    ticks = "".join(
        f'<line x1="{180 + i*166:.0f}" y1="430" x2="{180 + i*166:.0f}" y2="470" '
        f'stroke="{INK}" stroke-width="8" stroke-linecap="round" opacity="0.45"/>'
        for i in range(5)
    )
    handle = (
        f'<circle cx="640" cy="512" r="60" fill="{CRIM}"/>'
        f'<circle cx="640" cy="512" r="60" fill="none" stroke="{INK}" stroke-width="10"/>'
    )
    return svg(body + ticks + handle)


# =============================================================================
# B4 — Pattern / lattice
# =============================================================================

def b4_1_perspective_grid() -> str:
    """Receding 3D mesh grid plane converging to a vanishing point."""
    vp = (512, 380)
    body = []
    # horizontal lines
    for k in range(8):
        t = k / 7
        y = 540 + t * 320
        body.append(
            f'<line x1="100" y1="{y:.0f}" x2="924" y2="{y:.0f}" '
            f'stroke="{INK}" stroke-width="{6 + k*1.5:.0f}" opacity="{0.3 + t*0.6:.2f}"/>'
        )
    # vertical lines converging to vanishing point
    for k in range(-6, 7):
        x_bottom = 512 + k * 110
        body.append(
            f'<line x1="{x_bottom:.0f}" y1="860" x2="{vp[0]}" y2="{vp[1]}" '
            f'stroke="{INK}" stroke-width="8" opacity="0.55"/>'
        )
    body.append(f'<circle cx="{vp[0]}" cy="{vp[1]}" r="34" fill="{CRIM}"/>')
    return svg("".join(body))


def b4_2_honeycomb() -> str:
    """7-cell hex tiling cluster, central cell crimson."""
    cx, cy = 512, 512
    R = 130
    body = []
    centers = [(cx, cy)]
    for k in range(6):
        a = math.radians(k * 60)
        centers.append((cx + math.sqrt(3) * R * math.cos(a),
                        cy + math.sqrt(3) * R * math.sin(a)))
    for i, (hx, hy) in enumerate(centers):
        pts = []
        for k in range(6):
            a = math.radians(k * 60 - 30)
            pts.append(f"{hx + R * math.cos(a):.1f},{hy + R * math.sin(a):.1f}")
        fill = CRIM if i == 0 else "white"
        body.append(
            f'<polygon points="{" ".join(pts)}" fill="{fill}" '
            f'stroke="{INK}" stroke-width="14" stroke-linejoin="round"/>'
        )
    return svg("".join(body))


def b4_3_particle_burst() -> str:
    """Dense scatter of small dots radiating from a central crimson core."""
    cx, cy = 512, 512
    body = []
    for i in range(160):
        # uniform angle, biased radius (more in middle band)
        a = (i * 137.5) * math.pi / 180   # golden-angle scatter
        # distribute radii so density looks natural
        r = 80 + 360 * math.sqrt((i % 40) / 40 + (i // 40) * 0.05)
        if r > 460:
            continue
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a)
        sz = max(4, 12 - r / 60)
        body.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{sz:.1f}" fill="{INK}" '
            f'opacity="{1 - r/520:.2f}"/>'
        )
    body.append(f'<circle cx="{cx}" cy="{cy}" r="44" fill="{CRIM}"/>')
    return svg("".join(body))


def b4_4_voronoi_cells() -> str:
    """Stylised irregular cell pattern — hand-laid polygons."""
    body = []
    cells = [
        [(140, 200), (380, 160), (430, 350), (270, 420), (140, 360)],
        [(380, 160), (640, 200), (650, 380), (430, 350)],
        [(640, 200), (884, 240), (860, 460), (650, 380)],
        [(140, 360), (270, 420), (320, 620), (170, 600)],
        [(270, 420), (430, 350), (530, 520), (440, 660), (320, 620)],
        [(430, 350), (650, 380), (700, 540), (530, 520)],
        [(650, 380), (860, 460), (880, 660), (700, 540)],
        [(170, 600), (320, 620), (380, 820), (180, 820)],
        [(320, 620), (440, 660), (560, 820), (380, 820)],
        [(440, 660), (530, 520), (700, 540), (760, 820), (560, 820)],
        [(700, 540), (880, 660), (880, 820), (760, 820)],
    ]
    crim_idx = 4
    for i, poly in enumerate(cells):
        fill = CRIM if i == crim_idx else "white"
        pts = " ".join(f"{x},{y}" for x, y in poly)
        body.append(
            f'<polygon points="{pts}" fill="{fill}" stroke="{INK}" '
            f'stroke-width="10" stroke-linejoin="round"/>'
        )
    return svg("".join(body))


def b4_5_concentric_hex() -> str:
    """Nested hexagon outlines, crimson center fill."""
    cx, cy = 512, 512
    body = []
    for i, R in enumerate([400, 320, 240, 160]):
        pts = " ".join(
            f"{cx + R * math.cos(math.radians(k * 60 - 30)):.1f},"
            f"{cy + R * math.sin(math.radians(k * 60 - 30)):.1f}"
            for k in range(6)
        )
        body.append(
            f'<polygon points="{pts}" fill="none" stroke="{INK}" '
            f'stroke-width="22" stroke-linejoin="round" '
            f'opacity="{0.3 + 0.2 * i:.2f}"/>'
        )
    # innermost filled crimson
    pts = " ".join(
        f"{cx + 80 * math.cos(math.radians(k * 60 - 30)):.1f},"
        f"{cy + 80 * math.sin(math.radians(k * 60 - 30)):.1f}"
        for k in range(6)
    )
    body.append(f'<polygon points="{pts}" fill="{CRIM}"/>')
    return svg("".join(body))


def b4_6_triangular_mesh() -> str:
    """Triangulated surface — interlocked triangles, one crimson."""
    body = []
    # 4-row triangle strip
    rows = 4
    cols = 5
    sx, sy = 200, 240
    dx, dy = 120, 130
    crim_tri = (1, 1)   # which triangle to highlight
    for r in range(rows):
        for c in range(cols):
            x0 = sx + c * dx + (r % 2) * (dx / 2)
            y0 = sy + r * dy
            # upward triangle
            tri_up = [(x0, y0), (x0 + dx, y0), (x0 + dx / 2, y0 + dy)]
            fill = CRIM if (r, c) == crim_tri else "white"
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in tri_up)
            body.append(
                f'<polygon points="{pts}" fill="{fill}" stroke="{INK}" '
                f'stroke-width="10" stroke-linejoin="round"/>'
            )
            if c < cols - 1:
                tri_dn = [(x0 + dx, y0), (x0 + dx + dx / 2, y0 + dy),
                          (x0 + dx / 2, y0 + dy)]
                pts2 = " ".join(f"{x:.1f},{y:.1f}" for x, y in tri_dn)
                body.append(
                    f'<polygon points="{pts2}" fill="white" stroke="{INK}" '
                    f'stroke-width="10" stroke-linejoin="round"/>'
                )
    return svg("".join(body))


# =============================================================================
# B5 — Korean / distinctive symbolic
# =============================================================================

def b5_1_taegeuk_axis() -> str:
    """Korean taegeuk (yin-yang) bisected by a horizontal axis line."""
    cx, cy = 512, 512
    R = 320
    # outer circle
    outer = f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="white" stroke="{INK}" stroke-width="20"/>'
    # the yin-yang S-curve (two semicircles on the diameter, one each side)
    # draw a path: upper half ⊃ + small reverse ⊂ + lower half ⊂
    yy = (
        f'<path d="M {cx} {cy-R} '
        f'A {R} {R} 0 0 1 {cx} {cy+R} '
        f'A {R/2} {R/2} 0 0 1 {cx} {cy} '
        f'A {R/2} {R/2} 0 0 0 {cx} {cy-R} Z" '
        f'fill="{INK}"/>'
    )
    # axis line through center
    ax = (
        f'<line x1="{cx-R-50}" y1="{cy}" x2="{cx+R+50}" y2="{cy}" '
        f'stroke="{CRIM}" stroke-width="22" stroke-linecap="round" '
        f'marker-end="url(#arr)"/>'
    )
    # small dots (eyes of yin-yang)
    eyes = (
        f'<circle cx="{cx}" cy="{cy-R/2}" r="20" fill="white"/>'
        f'<circle cx="{cx}" cy="{cy+R/2}" r="20" fill="{INK}"/>'
    )
    return svg(outer + yy + eyes + ax)


def b5_2_bow_arc() -> str:
    """Korean traditional bow (활) — arc + string + center grip."""
    cx, cy = 512, 512
    body = (
        # bow (curved arc — a thick C-shape)
        f'<path d="M 320 200 Q 760 200 760 512 Q 760 824 320 824" '
        f'fill="none" stroke="{INK}" stroke-width="38" stroke-linecap="round"/>'
        # bow string (vertical taut line)
        f'<line x1="320" y1="200" x2="320" y2="824" stroke="{INK}" '
        f'stroke-width="10"/>'
        # arrow nocked at center
        f'<line x1="120" y1="{cy}" x2="900" y2="{cy}" stroke="{CRIM}" '
        f'stroke-width="22" stroke-linecap="round" marker-end="url(#arr)"/>'
        # grip wrap
        f'<rect x="740" y="{cy-60}" width="40" height="120" rx="14" fill="{INK}"/>'
    )
    return svg(body)


def b5_3_three_mountains() -> str:
    """Three peaks (산) — Korean mountain motif, central peak crimson."""
    body = (
        f'<polygon points="180,800 360,400 540,800" fill="{INK}"/>'
        f'<polygon points="380,800 600,260 820,800" fill="{CRIM}"/>'
        f'<polygon points="660,800 800,440 940,800" fill="{INK}"/>'
        # ground line
        f'<line x1="120" y1="800" x2="940" y2="800" stroke="{INK}" '
        f'stroke-width="14" stroke-linecap="round"/>'
    )
    return svg(body)


def b5_4_hanji_stamp() -> str:
    """Korean seal-stamp — square with internal grid + center mark."""
    body = (
        f'<rect x="232" y="232" width="560" height="560" rx="20" ry="20" '
        f'fill="{CRIM}"/>'
        # inner border
        f'<rect x="280" y="280" width="464" height="464" rx="6" ry="6" '
        f'fill="none" stroke="white" stroke-width="14"/>'
        # 田 grid (4 squares)
        f'<line x1="512" y1="280" x2="512" y2="744" stroke="white" stroke-width="14"/>'
        f'<line x1="280" y1="512" x2="744" y2="512" stroke="white" stroke-width="14"/>'
        # corner ticks
        f'<g fill="white">'
        f'<rect x="320" y="320" width="40" height="40"/>'
        f'<rect x="664" y="320" width="40" height="40"/>'
        f'<rect x="320" y="664" width="40" height="40"/>'
        f'<rect x="664" y="664" width="40" height="40"/>'
        f'</g>'
        # central dot
        f'<circle cx="512" cy="512" r="46" fill="white"/>'
    )
    return svg(body)


def b5_5_brush_stroke() -> str:
    """Single tapered calligraphic arc — ink brush gesture."""
    # Build a tapered stroke as a closed path that thickens then thins.
    samples = 60
    pts_top, pts_bot = [], []
    for i in range(samples + 1):
        t = i / samples
        # arc center + radial offset
        cx = 200 + t * 624
        cy = 720 - 280 * math.sin(t * math.pi)
        # taper width: thick in middle, thin at ends
        w = 70 * math.sin(t * math.pi) ** 0.6 + 6
        # tangent angle for perpendicular offset
        # (numerical derivative)
        eps = 1e-3
        cx2 = 200 + (t + eps) * 624
        cy2 = 720 - 280 * math.sin((t + eps) * math.pi)
        dx, dy = cx2 - cx, cy2 - cy
        L = math.hypot(dx, dy) + 1e-9
        nx, ny = -dy / L, dx / L
        pts_top.append((cx + nx * w, cy + ny * w))
        pts_bot.append((cx - nx * w, cy - ny * w))
    d = ("M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts_top)
         + " L " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in reversed(pts_bot))
         + " Z")
    body = (
        f'<path d="{d}" fill="{INK}"/>'
        # crimson stamp dot at the start
        f'<circle cx="200" cy="720" r="42" fill="{CRIM}"/>'
    )
    return svg(body)


def b5_6_pottery_axis() -> str:
    """Profile of a Korean ceramic vessel cut by a vertical axis line."""
    body = (
        # left silhouette of bottle (mirror across vertical axis at x=512)
        f'<path d="M 380 280 '
        f'C 380 320 320 360 320 480 '
        f'C 320 600 420 700 420 800 '
        f'L 604 800 '
        f'C 604 700 704 600 704 480 '
        f'C 704 360 644 320 644 280 '
        f'C 644 250 580 240 512 240 '
        f'C 444 240 380 250 380 280 Z" fill="{INK}"/>'
        # mouth opening
        f'<ellipse cx="512" cy="280" rx="100" ry="20" fill="white"/>'
        # central rotation axis (crimson dotted)
        f'<line x1="512" y1="160" x2="512" y2="880" stroke="{CRIM}" '
        f'stroke-width="14" stroke-dasharray="20 16" stroke-linecap="round"/>'
        # spinning indicator dot
        f'<circle cx="512" cy="160" r="32" fill="{CRIM}"/>'
    )
    return svg(body)


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
                        title: str, out_path: Path) -> None:
    cell, pad, label_h, title_h = 700, 40, 60, 100
    cols, rows = 3, 2
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
    print("Generating 30 fresh AXIS marks (no overlap with prior batches) ...")
    batches = [
        ("B1 · Math/Coordinate", "b1", [
            (b1_1_vector_field,    "B1.1 · Vector Field"),
            (b1_2_polar_grid,      "B1.2 · Polar Grid"),
            (b1_3_quadrant_grid,   "B1.3 · Quadrant Grid"),
            (b1_4_bounding_box,    "B1.4 · Bounding Box 3D"),
            (b1_5_topographic,     "B1.5 · Topographic Map"),
            (b1_6_phase_spiral,    "B1.6 · Phase Spiral"),
        ]),
        ("B2 · Topology/Curves", "b2", [
            (b2_1_mobius,          "B2.1 · Möbius Loop"),
            (b2_2_dna_helix,       "B2.2 · DNA Helix"),
            (b2_3_bezier_curve,    "B2.3 · Bezier Curve"),
            (b2_4_trefoil_knot,    "B2.4 · Trefoil Knot"),
            (b2_5_lemniscate,      "B2.5 · Lemniscate"),
            (b2_6_echo_wave,       "B2.6 · Stacked Sinusoids"),
        ]),
        ("B3 · HCI Devices", "b3", [
            (b3_1_vr_headset,      "B3.1 · VR Headset"),
            (b3_2_haptic_glove,    "B3.2 · Haptic Glove"),
            (b3_3_stylus,          "B3.3 · Stylus"),
            (b3_4_smartphone,      "B3.4 · Phone Touch"),
            (b3_5_controller,      "B3.5 · XR Controller"),
            (b3_6_slider,          "B3.6 · UI Slider"),
        ]),
        ("B4 · Pattern/Lattice", "b4", [
            (b4_1_perspective_grid,"B4.1 · Perspective Grid"),
            (b4_2_honeycomb,       "B4.2 · Honeycomb"),
            (b4_3_particle_burst,  "B4.3 · Particle Burst"),
            (b4_4_voronoi_cells,   "B4.4 · Voronoi Cells"),
            (b4_5_concentric_hex,  "B4.5 · Concentric Hex"),
            (b4_6_triangular_mesh, "B4.6 · Triangular Mesh"),
        ]),
        ("B5 · Korean Distinctive", "b5", [
            (b5_1_taegeuk_axis,    "B5.1 · Taegeuk + Axis"),
            (b5_2_bow_arc,         "B5.2 · Korean Bow"),
            (b5_3_three_mountains, "B5.3 · Three Mountains"),
            (b5_4_hanji_stamp,     "B5.4 · Hanji Seal"),
            (b5_5_brush_stroke,    "B5.5 · Brush Stroke"),
            (b5_6_pottery_axis,    "B5.6 · Pottery + Axis"),
        ]),
    ]
    for title, prefix, items in batches:
        paths, labels = [], []
        for fn, label in items:
            slug = fn.__name__
            paths.append(write_pair(f"axis_{slug}", fn()))
            labels.append(label)
        sheet_path = OUT / f"_sheet_{prefix}.png"
        build_contact_sheet(paths, labels, title, sheet_path)
        print(f"  → {sheet_path.relative_to(ROOT)}")
    print("done.")


if __name__ == "__main__":
    main()
