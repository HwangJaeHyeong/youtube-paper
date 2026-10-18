"""AXIS Lab — 18 people / human-centred marks (6 batches × 3).

Korea University AXIS Lab is HCI, so the brief is "person-centric" symbols.
Avoiding primitives already used in prior batches:
  · 3 abstract people (N5)               · two-finger pinch dots (M3)
  · two hands handshake (N6)             · haptic glove (B3.2)
  · open hand silhouette (N1-3, AX3,I5)  · hand + sphere (I5)

Six fresh person-centric families:
  P1 · Body + Axis        (Vitruvian-style body in coordinate frame)
  P2 · Head & Mind        (profile, gaze, dialogue)
  P3 · Crowd / Network    (people clusters + edges)
  P4 · Gesture            (pointing, OK/pinch ring, multi-touch — distinct
                           from prior open-hand & 2-dot pinch)
  P5 · Body Sensing       (mocap skeleton, heartbeat, anatomical eye)
  P6 · Korean Person      (Hangul ㅅ, bowing figure, hanbok pair)

Palette: P1 (ink #0A0A0A + KU crimson #862633 pop). 1024×1024 SVG + PNG.
"""
from __future__ import annotations

import math
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "logos" / "people"
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
      <marker id="arrCrim" viewBox="0 0 10 10" refX="9" refY="5"
              markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 Z" fill="{CRIM}"/>
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
# P1 · Body + Axis  (Vitruvian / coordinate-figure)
# =============================================================================

def p1_1_vitruvian_axis() -> str:
    """Vitruvian-style figure: torso + head, arms/legs extended along
    diagonals, inscribed in a circle. Crimson axis cross through center.
    """
    cx, cy = 512, 540
    R = 360
    body = []
    # outer circle
    body.append(
        f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{INK}" '
        f'stroke-width="14" opacity="0.55"/>'
    )
    # crimson axis cross
    body.append(
        f'<line x1="{cx-R-30}" y1="{cy}" x2="{cx+R+30}" y2="{cy}" '
        f'stroke="{CRIM}" stroke-width="14" stroke-linecap="round" opacity="0.85"/>'
    )
    body.append(
        f'<line x1="{cx}" y1="{cy-R-30}" x2="{cx}" y2="{cy+R+30}" '
        f'stroke="{CRIM}" stroke-width="14" stroke-linecap="round" opacity="0.85"/>'
    )
    # head
    body.append(f'<circle cx="{cx}" cy="{cy-260}" r="58" fill="{INK}"/>')
    # torso (vertical)
    body.append(
        f'<line x1="{cx}" y1="{cy-200}" x2="{cx}" y2="{cy+120}" '
        f'stroke="{INK}" stroke-width="44" stroke-linecap="round"/>'
    )
    # arms (diagonals up-out)
    for sign in (-1, 1):
        body.append(
            f'<line x1="{cx}" y1="{cy-140}" x2="{cx + sign*240}" y2="{cy-300}" '
            f'stroke="{INK}" stroke-width="34" stroke-linecap="round"/>'
        )
    # legs (diagonals down-out)
    for sign in (-1, 1):
        body.append(
            f'<line x1="{cx}" y1="{cy+120}" x2="{cx + sign*180}" y2="{cy+340}" '
            f'stroke="{INK}" stroke-width="34" stroke-linecap="round"/>'
        )
    # crimson dot at navel (centre of figure)
    body.append(f'<circle cx="{cx}" cy="{cy}" r="26" fill="{CRIM}"/>')
    return svg("".join(body))


def p1_2_figure_triad() -> str:
    """Single standing figure whose two raised arms + head form a 3-axis
    triad. Three arrows in INK with a crimson hub at the chest.
    """
    cx, cy = 512, 540
    body = []
    # head
    body.append(f'<circle cx="{cx}" cy="{cy-280}" r="56" fill="{INK}"/>')
    # torso (vertical Y axis ends at head)
    body.append(
        f'<line x1="{cx}" y1="{cy-220}" x2="{cx}" y2="{cy+120}" '
        f'stroke="{INK}" stroke-width="38" stroke-linecap="round"/>'
    )
    # legs
    body.append(
        f'<line x1="{cx}" y1="{cy+120}" x2="{cx-110}" y2="{cy+330}" '
        f'stroke="{INK}" stroke-width="32" stroke-linecap="round"/>'
    )
    body.append(
        f'<line x1="{cx}" y1="{cy+120}" x2="{cx+110}" y2="{cy+330}" '
        f'stroke="{INK}" stroke-width="32" stroke-linecap="round"/>'
    )
    # left arm = X axis (arrow, slightly down-out)
    body.append(
        f'<line x1="{cx}" y1="{cy-130}" x2="{cx-300}" y2="{cy-30}" '
        f'stroke="{INK}" stroke-width="30" stroke-linecap="round" '
        f'marker-end="url(#arr)"/>'
    )
    # right arm = Z axis (arrow, up-out)
    body.append(
        f'<line x1="{cx}" y1="{cy-130}" x2="{cx+260}" y2="{cy-280}" '
        f'stroke="{INK}" stroke-width="30" stroke-linecap="round" '
        f'marker-end="url(#arr)"/>'
    )
    # crimson chest dot (origin)
    body.append(f'<circle cx="{cx}" cy="{cy-130}" r="32" fill="{CRIM}"/>')
    return svg("".join(body))


def p1_3_pivot_figure() -> str:
    """Figure mid-rotation around a dashed vertical axis: torso angled,
    motion arc behind it.
    """
    cx, cy = 512, 540
    body = []
    # vertical pivot axis (crimson dashed)
    body.append(
        f'<line x1="{cx}" y1="{cy-360}" x2="{cx}" y2="{cy+340}" '
        f'stroke="{CRIM}" stroke-width="12" stroke-dasharray="20 16" '
        f'stroke-linecap="round"/>'
    )
    # motion arc (curved arrow indicating rotation around axis)
    body.append(
        f'<path d="M {cx-200} {cy-280} A 200 70 0 1 0 {cx+200} {cy-280}" '
        f'fill="none" stroke="{INK}" stroke-width="14" opacity="0.55" '
        f'stroke-linecap="round" marker-end="url(#arr)"/>'
    )
    # tilted figure to right of axis
    fx = cx + 60   # offset of body off axis
    # head
    body.append(
        f'<g transform="rotate(15 {cx} {cy})">'
        f'<circle cx="{fx}" cy="{cy-260}" r="56" fill="{INK}"/>'
        # torso
        f'<line x1="{fx}" y1="{cy-200}" x2="{fx}" y2="{cy+120}" '
        f'stroke="{INK}" stroke-width="40" stroke-linecap="round"/>'
        # arms outstretched horizontally
        f'<line x1="{fx-180}" y1="{cy-90}" x2="{fx+200}" y2="{cy-110}" '
        f'stroke="{INK}" stroke-width="32" stroke-linecap="round"/>'
        # legs
        f'<line x1="{fx}" y1="{cy+120}" x2="{fx-90}" y2="{cy+320}" '
        f'stroke="{INK}" stroke-width="32" stroke-linecap="round"/>'
        f'<line x1="{fx}" y1="{cy+120}" x2="{fx+90}" y2="{cy+320}" '
        f'stroke="{INK}" stroke-width="32" stroke-linecap="round"/>'
        f'</g>'
    )
    # crimson pivot dot at base (intersection of axis and ground)
    body.append(f'<circle cx="{cx}" cy="{cy+340}" r="28" fill="{CRIM}"/>')
    return svg("".join(body))


# =============================================================================
# P2 · Head & Mind  (profile / gaze / dialogue)
# =============================================================================

def _profile_path(cx: int, cy: int, mirror: bool = False) -> str:
    """A simplified left-facing head silhouette path centered around (cx,cy)."""
    # path expressed for facing-left (nose at left); mirror via transform if needed
    d = (
        f"M {cx+120} {cy-260} "
        f"C {cx+170} {cy-250} {cx+200} {cy-180} {cx+200} {cy-100} "      # crown to back of skull
        f"C {cx+200} {cy-30} {cx+180} {cy+40} {cx+150} {cy+90} "          # back of head
        f"L {cx+150} {cy+200} "                                           # neck back
        f"L {cx+90} {cy+200} "                                            # neck front
        f"L {cx+90} {cy+120} "
        f"C {cx+50} {cy+120} {cx-30} {cy+90} {cx-90} {cy+30} "            # chin to lip
        f"L {cx-110} {cy-10} "                                            # under nose
        f"L {cx-150} {cy-30} "                                            # nose tip
        f"L {cx-110} {cy-70} "
        f"L {cx-90} {cy-90} "                                             # bridge
        f"L {cx-40} {cy-160} "                                            # forehead
        f"C {cx-20} {cy-220} {cx+50} {cy-270} {cx+120} {cy-260} Z"
    )
    return d


def p2_1_profile_brainwave() -> str:
    """Side profile head (left-facing) with sinusoidal brainwave inside."""
    cx, cy = 512, 540
    body = []
    body.append(f'<path d="{_profile_path(cx, cy)}" fill="{INK}"/>')
    # sine wave inside head, tinted crimson
    samples = 60
    pts = []
    for i in range(samples + 1):
        t = i / samples
        x = (cx - 80) + t * 230
        y = (cy - 130) + 50 * math.sin(2 * math.pi * 2.2 * t)
        pts.append((x, y))
    d_wave = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    body.append(
        f'<path d="{d_wave}" fill="none" stroke="{CRIM}" stroke-width="18" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    return svg("".join(body))


def p2_2_gaze_cone() -> str:
    """Head silhouette with cone of gaze rays + target dot."""
    cx, cy = 380, 540
    body = []
    body.append(f'<path d="{_profile_path(cx, cy)}" fill="{INK}"/>')
    # gaze cone emerging from nose tip (~ cx-150, cy-30)
    eye_x, eye_y = cx - 90, cy - 110   # eye location
    target = (900, 380)
    # cone outer rays
    spread = 80
    for sign in (-1, 1):
        # offset target endpoint perpendicular to ray
        dx, dy = target[0] - eye_x, target[1] - eye_y
        L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L
        tx = target[0] + sign * spread * nx
        ty = target[1] + sign * spread * ny
        body.append(
            f'<line x1="{eye_x}" y1="{eye_y}" x2="{tx:.1f}" y2="{ty:.1f}" '
            f'stroke="{INK}" stroke-width="10" opacity="0.4" '
            f'stroke-linecap="round"/>'
        )
    # central gaze ray
    body.append(
        f'<line x1="{eye_x}" y1="{eye_y}" x2="{target[0]}" y2="{target[1]}" '
        f'stroke="{INK}" stroke-width="14" opacity="0.7" stroke-dasharray="22 14" '
        f'stroke-linecap="round"/>'
    )
    # target dot
    body.append(
        f'<circle cx="{target[0]}" cy="{target[1]}" r="46" fill="{CRIM}"/>'
        f'<circle cx="{target[0]}" cy="{target[1]}" r="78" fill="none" '
        f'stroke="{CRIM}" stroke-width="10" opacity="0.55"/>'
    )
    return svg("".join(body))


def p2_3_facing_profiles() -> str:
    """Two profiles facing each other across a vertical crimson axis (HCI =
    human-computer dialogue).
    """
    body = []
    cy = 540
    # left profile (faces right, so mirror the helper)
    cx_l = 360
    body.append(
        f'<g transform="translate({2*cx_l},0) scale(-1,1)">'
        f'<path d="{_profile_path(cx_l, cy)}" fill="{INK}"/></g>'
    )
    # right profile (faces left, original)
    cx_r = 664
    body.append(f'<path d="{_profile_path(cx_r, cy)}" fill="{INK}"/>')
    # crimson dialogue axis between them
    body.append(
        f'<line x1="512" y1="220" x2="512" y2="860" stroke="{CRIM}" '
        f'stroke-width="14" stroke-dasharray="20 16" stroke-linecap="round"/>'
    )
    # crimson interaction node at center
    body.append(f'<circle cx="512" cy="540" r="42" fill="{CRIM}"/>')
    return svg("".join(body))


# =============================================================================
# P3 · Crowd / Network
# =============================================================================

def _figure_glyph(cx: float, cy: float, scale: float = 1.0,
                  fill: str = INK) -> str:
    """A compact head + body glyph centered horizontally at cx, vertical
    `cy` is the *top* of head."""
    head_r = 30 * scale
    body_w = 70 * scale
    body_h = 110 * scale
    head = f'<circle cx="{cx}" cy="{cy + head_r}" r="{head_r}" fill="{fill}"/>'
    body = (
        f'<path d="M {cx - body_w/2} {cy + 2*head_r + body_h} '
        f'L {cx - body_w/2} {cy + 2*head_r + 28} '
        f'A {body_w/2} {body_w/2} 0 0 1 {cx + body_w/2} {cy + 2*head_r + 28} '
        f'L {cx + body_w/2} {cy + 2*head_r + body_h} Z" fill="{fill}"/>'
    )
    return head + body


def p3_1_pentagon_crowd() -> str:
    """5 figures arranged in a regular pentagon, connected by edges."""
    cx, cy = 512, 540
    R = 280
    figs = []
    for k in range(5):
        a = math.radians(-90 + k * 72)
        fx = cx + R * math.cos(a)
        # cy is top-of-head; place so figure centres roughly at radius
        fy = cy + R * math.sin(a) - 60
        figs.append((fx, fy, k))
    # edges first (so they sit behind figures)
    edge_lines = []
    for i in range(5):
        for j in range(i + 1, 5):
            ax, ay = figs[i][0], figs[i][1] + 60
            bx, by = figs[j][0], figs[j][1] + 60
            edge_lines.append(
                f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
                f'stroke="{INK}" stroke-width="6" opacity="0.35"/>'
            )
    body = "".join(edge_lines)
    for fx, fy, k in figs:
        # one figure crimson (top)
        col = CRIM if k == 0 else INK
        body += _figure_glyph(fx, fy, scale=1.0, fill=col)
    return svg(body)


def p3_2_ring_crowd() -> str:
    """6 figures around a ring with arms pointing toward a central crimson
    hub. Renders here as an outer ring of figures + inner spokes."""
    cx, cy = 512, 540
    R = 320
    body = []
    # spokes
    for k in range(6):
        a = math.radians(-90 + k * 60)
        x = cx + (R - 110) * math.cos(a)
        y = cy + (R - 110) * math.sin(a)
        body.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{INK}" stroke-width="10" opacity="0.4"/>'
        )
    # ring (faint)
    body.append(
        f'<circle cx="{cx}" cy="{cy}" r="{R-50}" fill="none" stroke="{INK}" '
        f'stroke-width="8" opacity="0.25"/>'
    )
    # figures
    for k in range(6):
        a = math.radians(-90 + k * 60)
        x = cx + R * math.cos(a)
        y = cy + R * math.sin(a) - 90   # top-of-head offset
        body.append(_figure_glyph(x, y, scale=0.85))
    # central crimson hub
    body.append(f'<circle cx="{cx}" cy="{cy}" r="48" fill="{CRIM}"/>')
    return svg("".join(body))


def p3_3_people_graph() -> str:
    """Network graph: 4 people (heads-only) as nodes, connected by edges,
    one node crimson."""
    cx, cy = 512, 540
    nodes = [
        (cx - 240, cy - 180, INK),
        (cx + 240, cy - 180, INK),
        (cx - 220, cy + 200, INK),
        (cx + 220, cy + 220, CRIM),
    ]
    body = []
    # edges
    for i in range(4):
        for j in range(i + 1, 4):
            ax, ay, _ = nodes[i]
            bx, by, _ = nodes[j]
            body.append(
                f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" '
                f'stroke="{INK}" stroke-width="10" opacity="0.45"/>'
            )
    # nodes — head + tiny shoulders glyph
    for nx, ny, col in nodes:
        body.append(f'<circle cx="{nx}" cy="{ny}" r="64" fill="{col}"/>')
        body.append(
            f'<path d="M {nx-86} {ny+148} '
            f'A 86 70 0 0 1 {nx+86} {ny+148} Z" fill="{col}"/>'
        )
    return svg("".join(body))


# =============================================================================
# P4 · Gesture  (pointing, OK ring, multi-touch — distinct from prior pinch
# and open-hand silhouettes)
# =============================================================================

def p4_1_pointing_finger() -> str:
    """Hand pointing right with index finger; arrow extends from tip."""
    body = []
    # palm/fist (rounded rect at left)
    body.append(
        f'<rect x="240" y="380" width="240" height="280" rx="60" ry="60" '
        f'fill="{INK}"/>'
    )
    # thumb
    body.append(
        f'<rect x="260" y="320" width="120" height="90" rx="44" ry="44" '
        f'fill="{INK}"/>'
    )
    # curled fingers (small bumps on top)
    for i, x in enumerate((400, 440, 460)):
        body.append(
            f'<rect x="{x-18}" y="345" width="36" height="60" rx="18" '
            f'ry="18" fill="{INK}"/>'
        )
    # extended index finger pointing right
    body.append(
        f'<rect x="460" y="490" width="240" height="60" rx="30" ry="30" '
        f'fill="{INK}"/>'
    )
    # arrow continuing from fingertip
    body.append(
        f'<line x1="700" y1="520" x2="900" y2="520" stroke="{CRIM}" '
        f'stroke-width="22" stroke-linecap="round" marker-end="url(#arrCrim)"/>'
    )
    # crimson tip dot at fingertip
    body.append(f'<circle cx="700" cy="520" r="22" fill="{CRIM}"/>')
    return svg("".join(body))


def p4_2_ok_ring() -> str:
    """Thumb–index OK / pinch ring, with three remaining fingers extended.
    Distinct from the M3 'two dots' pinch — this is the full ring shape.
    """
    cx, cy = 460, 540
    body = []
    # ring made of thumb + index curl
    ring_r = 130
    body.append(
        f'<circle cx="{cx}" cy="{cy}" r="{ring_r}" fill="none" stroke="{INK}" '
        f'stroke-width="58" stroke-linecap="round"/>'
    )
    # three extended fingers (right of ring)
    for i, off in enumerate(((40, 70), (100, 30), (160, 50))):
        dx, length = off
        body.append(
            f'<rect x="{cx + ring_r - 20 + dx}" '
            f'y="{cy - 30 - i*55}" '
            f'width="{180 + length}" height="42" rx="21" ry="21" fill="{INK}"/>'
        )
    # palm base (lower right)
    body.append(
        f'<path d="M {cx + ring_r - 20} {cy + 60} '
        f'L {cx + ring_r + 220} {cy + 60} '
        f'L {cx + ring_r + 220} {cy + 220} '
        f'L {cx + ring_r - 60} {cy + 220} Z" fill="{INK}"/>'
    )
    # crimson dot in centre of OK ring (the "approved" point)
    body.append(f'<circle cx="{cx}" cy="{cy}" r="42" fill="{CRIM}"/>')
    return svg("".join(body))


def p4_3_multitouch_dots() -> str:
    """Multi-touch fingerprint: three fingertip ovals fanning out, each
    with a concentric ripple. Different from M3 (only two dots, no ripples
    no ovals)."""
    body = []
    # three fingertip ovals at different angles
    cx, cy = 512, 540
    specs = [
        (-30, -200, -25),    # left fingertip (dx, dy, rotation deg)
        (0,   -260,   0),
        (220, -180,  25),
    ]
    for dx, dy, rot in specs:
        x = cx + dx
        y = cy + dy
        body.append(
            f'<g transform="translate({x} {y}) rotate({rot})">'
            f'<ellipse cx="0" cy="0" rx="80" ry="120" fill="{INK}"/>'
            # fingerprint arcs (lighter)
            f'<ellipse cx="0" cy="-20" rx="40" ry="60" fill="none" '
            f'stroke="white" stroke-width="6" opacity="0.55"/>'
            f'<ellipse cx="0" cy="-30" rx="22" ry="36" fill="none" '
            f'stroke="white" stroke-width="6" opacity="0.55"/>'
            f'</g>'
        )
    # concentric ripples below the trio (touch surface)
    surf_y = 760
    for r, op in ((60, 1.0), (120, 0.55), (190, 0.3)):
        body.append(
            f'<ellipse cx="{cx}" cy="{surf_y}" rx="{r*1.6}" ry="{r*0.45}" '
            f'fill="none" stroke="{INK}" stroke-width="10" opacity="{op}"/>'
        )
    # crimson tap dot at centre of surface
    body.append(f'<ellipse cx="{cx}" cy="{surf_y}" rx="42" ry="14" fill="{CRIM}"/>')
    return svg("".join(body))


# =============================================================================
# P5 · Body Sensing  (mocap, heartbeat, anatomical eye)
# =============================================================================

def p5_1_mocap_skeleton() -> str:
    """Stick-figure with motion-capture joint dots; one dot crimson."""
    body = []
    # joint coordinates: head, neck, l-shoulder, r-shoulder, elbows, hands,
    # hips, knees, feet
    joints = {
        "head":   (512, 240),
        "neck":   (512, 340),
        "lsh":    (412, 360),
        "rsh":    (612, 360),
        "lel":    (340, 480),
        "rel":    (684, 480),
        "lhand":  (300, 620),
        "rhand":  (720, 620),
        "hip":    (512, 540),
        "lhip":   (470, 555),
        "rhip":   (554, 555),
        "lknee":  (440, 720),
        "rknee":  (584, 720),
        "lfoot":  (420, 870),
        "rfoot":  (604, 870),
    }
    bones = [
        ("neck", "lsh"), ("neck", "rsh"),
        ("lsh", "lel"), ("lel", "lhand"),
        ("rsh", "rel"), ("rel", "rhand"),
        ("neck", "hip"),
        ("hip", "lhip"), ("hip", "rhip"),
        ("lhip", "lknee"), ("lknee", "lfoot"),
        ("rhip", "rknee"), ("rknee", "rfoot"),
    ]
    # head circle
    body.append(
        f'<circle cx="{joints["head"][0]}" cy="{joints["head"][1]}" r="56" '
        f'fill="none" stroke="{INK}" stroke-width="14"/>'
    )
    # bones
    for a, b in bones:
        ax, ay = joints[a]
        bx, by = joints[b]
        body.append(
            f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{INK}" '
            f'stroke-width="14" stroke-linecap="round"/>'
        )
    # joint dots
    crim_joint = "rhand"
    for name, (x, y) in joints.items():
        if name == "head":
            continue
        col = CRIM if name == crim_joint else INK
        r = 22 if name == crim_joint else 16
        body.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
    return svg("".join(body))


def p5_2_heartbeat_body() -> str:
    """Front-facing body silhouette with ECG line crossing the chest."""
    cx = 512
    body = []
    # head
    body.append(f'<circle cx="{cx}" cy="280" r="80" fill="{INK}"/>')
    # torso (rounded shoulders + tapered waist)
    body.append(
        f'<path d="M {cx-160} 380 '
        f'C {cx-180} 380 {cx-220} 420 {cx-220} 480 '
        f'L {cx-180} 700 '
        f'L {cx+180} 700 '
        f'L {cx+220} 480 '
        f'C {cx+220} 420 {cx+180} 380 {cx+160} 380 Z" fill="{INK}"/>'
    )
    # ECG line through chest (white over body, then continues crimson outside)
    ecg_y = 540
    # draw an ECG segment as polyline
    pts = [
        (160, ecg_y),
        (300, ecg_y),
        (340, ecg_y),
        (380, ecg_y - 30),
        (420, ecg_y + 50),
        (450, ecg_y - 110),
        (480, ecg_y + 80),
        (520, ecg_y - 30),
        (560, ecg_y),
        (864, ecg_y),
    ]
    d = "M " + " L ".join(f"{x} {y}" for x, y in pts)
    body.append(
        f'<path d="{d}" fill="none" stroke="{CRIM}" stroke-width="18" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    # small crimson heart dot at peak
    body.append(f'<circle cx="450" cy="{ecg_y - 110}" r="22" fill="{CRIM}"/>')
    return svg("".join(body))


def p5_3_anatomical_eye() -> str:
    """Anatomical eye: outer almond shape, iris, pupil, with crosshair axis."""
    cx, cy = 512, 540
    body = []
    # outer eye almond
    body.append(
        f'<path d="M {cx-360} {cy} '
        f'Q {cx} {cy-220} {cx+360} {cy} '
        f'Q {cx} {cy+220} {cx-360} {cy} Z" '
        f'fill="white" stroke="{INK}" stroke-width="22"/>'
    )
    # iris
    body.append(
        f'<circle cx="{cx}" cy="{cy}" r="140" fill="none" stroke="{INK}" '
        f'stroke-width="22"/>'
    )
    # iris radial lines
    for k in range(16):
        a = math.radians(k * 22.5)
        x1 = cx + 60 * math.cos(a)
        y1 = cy + 60 * math.sin(a)
        x2 = cx + 130 * math.cos(a)
        y2 = cy + 130 * math.sin(a)
        body.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{INK}" stroke-width="6" opacity="0.55"/>'
        )
    # pupil (crimson)
    body.append(f'<circle cx="{cx}" cy="{cy}" r="48" fill="{CRIM}"/>')
    # crosshair axis through pupil (extends past eye)
    body.append(
        f'<line x1="{cx-440}" y1="{cy}" x2="{cx+440}" y2="{cy}" '
        f'stroke="{INK}" stroke-width="6" opacity="0.4" stroke-dasharray="14 12"/>'
    )
    body.append(
        f'<line x1="{cx}" y1="{cy-280}" x2="{cx}" y2="{cy+280}" '
        f'stroke="{INK}" stroke-width="6" opacity="0.4" stroke-dasharray="14 12"/>'
    )
    return svg("".join(body))


# =============================================================================
# P6 · Korean person motifs
# =============================================================================

def p6_1_hangul_siot() -> str:
    """Stylised Hangul ㅅ (siot) — the consonant in 사람 ('person') and
    visually a walking/standing human. Combined with a crimson axis dot
    at the apex.
    """
    cx, cy = 512, 540
    # ㅅ has two slanted strokes meeting at top, like an inverted V
    apex = (cx, cy - 280)
    left_foot = (cx - 280, cy + 280)
    right_foot = (cx + 280, cy + 280)
    body = []
    # left stroke (slightly thicker, calligraphic)
    body.append(
        f'<line x1="{apex[0]}" y1="{apex[1]}" x2="{left_foot[0]}" '
        f'y2="{left_foot[1]}" stroke="{INK}" stroke-width="62" '
        f'stroke-linecap="round"/>'
    )
    # right stroke starts a tiny bit below apex (traditional ㅅ shape)
    right_apex = (cx + 14, cy - 250)
    body.append(
        f'<line x1="{right_apex[0]}" y1="{right_apex[1]}" '
        f'x2="{right_foot[0]}" y2="{right_foot[1]}" stroke="{INK}" '
        f'stroke-width="62" stroke-linecap="round"/>'
    )
    # crimson dot at apex (head)
    body.append(f'<circle cx="{apex[0]}" cy="{apex[1]}" r="48" fill="{CRIM}"/>')
    # ground line
    body.append(
        f'<line x1="180" y1="{cy + 320}" x2="844" y2="{cy + 320}" '
        f'stroke="{INK}" stroke-width="10" stroke-linecap="round" opacity="0.4"/>'
    )
    return svg("".join(body))


def p6_2_bowing_figure() -> str:
    """Korean bowing figure (절) — torso bent forward, head down."""
    body = []
    # head (forward and down)
    body.append(f'<circle cx="600" cy="380" r="60" fill="{INK}"/>')
    # torso curving from hips up to head
    body.append(
        f'<path d="M 360 700 '
        f'Q 380 600 460 520 '
        f'Q 540 440 600 420 '
        f'L 600 380 '
        f'Q 540 420 460 500 '
        f'Q 380 580 320 700 Z" fill="{INK}"/>'
    )
    # arm hanging forward
    body.append(
        f'<path d="M 480 480 '
        f'Q 500 600 540 700 '
        f'Q 560 720 580 700 '
        f'Q 540 600 510 470 Z" fill="{INK}" opacity="0.85"/>'
    )
    # legs (kneeling)
    body.append(
        f'<rect x="320" y="700" width="380" height="80" rx="40" ry="40" '
        f'fill="{INK}"/>'
    )
    # ground line
    body.append(
        f'<line x1="180" y1="800" x2="900" y2="800" stroke="{INK}" '
        f'stroke-width="10" stroke-linecap="round"/>'
    )
    # crimson direction arc — the bow gesture from upright to bent
    body.append(
        f'<path d="M 760 300 A 220 220 0 0 1 600 380" fill="none" '
        f'stroke="{CRIM}" stroke-width="14" stroke-linecap="round" '
        f'stroke-dasharray="18 14" marker-end="url(#arrCrim)"/>'
    )
    return svg("".join(body))


def p6_3_hanbok_pair() -> str:
    """Two figures in stylised hanbok stance — wide A-line lower bodies,
    one rendered in INK, one in CRIM, mirrored."""
    body = []
    cy = 580

    def hanbok(cx: int, fill: str) -> str:
        # head
        s = f'<circle cx="{cx}" cy="{cy-220}" r="56" fill="{fill}"/>'
        # upper body (jeogori — boxy with wide collar)
        s += (
            f'<path d="M {cx-110} {cy-160} '
            f'L {cx-130} {cy-30} '
            f'L {cx+130} {cy-30} '
            f'L {cx+110} {cy-160} '
            f'C {cx+80} {cy-180} {cx-80} {cy-180} {cx-110} {cy-160} Z" '
            f'fill="{fill}"/>'
        )
        # collar line (white V)
        s += (
            f'<path d="M {cx-30} {cy-160} L {cx} {cy-110} L {cx+30} {cy-160}" '
            f'fill="none" stroke="white" stroke-width="10" stroke-linejoin="round"/>'
        )
        # waist sash (lighter band)
        s += (
            f'<rect x="{cx-130}" y="{cy-40}" width="260" height="22" fill="white" '
            f'opacity="0.85"/>'
        )
        # skirt (chima) — wide A-line
        s += (
            f'<path d="M {cx-140} {cy-18} '
            f'L {cx-220} {cy+260} '
            f'L {cx+220} {cy+260} '
            f'L {cx+140} {cy-18} Z" fill="{fill}"/>'
        )
        return s

    body.append(hanbok(360, INK))
    body.append(hanbok(664, CRIM))
    # connecting axis at center (vertical dotted)
    body.append(
        f'<line x1="512" y1="240" x2="512" y2="860" stroke="{INK}" '
        f'stroke-width="10" stroke-dasharray="14 12" opacity="0.45"/>'
    )
    # ground
    body.append(
        f'<line x1="120" y1="840" x2="904" y2="840" stroke="{INK}" '
        f'stroke-width="10" stroke-linecap="round"/>'
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
                        title: str, out_path: Path) -> None:
    cell, pad, label_h, title_h = 700, 40, 60, 100
    cols, rows = 3, 1
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


def build_master_sheet(all_paths: list[Path], all_labels: list[str],
                       out_path: Path) -> None:
    cell, pad, label_h, title_h = 520, 30, 50, 80
    cols, rows = 6, 3
    width = cols * cell + (cols + 1) * pad
    height = title_h + rows * (cell + label_h) + (rows + 1) * pad
    canvas = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 50)
    label_font = _load_font(["Helvetica.ttc", "Arial Bold.ttf"], 22)
    draw.text((width // 2, title_h // 2),
              "AXIS Lab · 18 People-Centred Marks (6×3)",
              font=title_font, fill="#0A0A0A", anchor="mm")
    # arrange rows = batches, cols = variants
    for i, (p, label) in enumerate(zip(all_paths, all_labels)):
        # i runs 0..17 in order P1.1, P1.2, P1.3, P2.1, ...
        row = i // 3
        col = i % 3 + (i // 3 % 1) * 0   # placeholder, we'll group differently
        # Actually layout: batches as rows, variants as cols → row = batch idx,
        # col = variant idx (0..2) within batch. Place 2 batches per master row
        # so we get 6 cols × 3 rows total.
        batch = i // 3
        variant = i % 3
        col = (batch % 2) * 3 + variant
        row = batch // 2
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
    print("Generating 18 AXIS people-centred marks (6 batches × 3) ...")
    batches = [
        ("P1 · Body + Axis", "p1", [
            (p1_1_vitruvian_axis,  "P1.1 · Vitruvian Axis"),
            (p1_2_figure_triad,    "P1.2 · Figure Triad"),
            (p1_3_pivot_figure,    "P1.3 · Pivot Figure"),
        ]),
        ("P2 · Head & Mind", "p2", [
            (p2_1_profile_brainwave, "P2.1 · Profile + Brainwave"),
            (p2_2_gaze_cone,         "P2.2 · Gaze Cone"),
            (p2_3_facing_profiles,   "P2.3 · Facing Profiles"),
        ]),
        ("P3 · Crowd / Network", "p3", [
            (p3_1_pentagon_crowd,  "P3.1 · Pentagon Crowd"),
            (p3_2_ring_crowd,      "P3.2 · Ring Crowd"),
            (p3_3_people_graph,    "P3.3 · People Graph"),
        ]),
        ("P4 · Gesture", "p4", [
            (p4_1_pointing_finger,  "P4.1 · Pointing Finger"),
            (p4_2_ok_ring,          "P4.2 · OK Ring"),
            (p4_3_multitouch_dots,  "P4.3 · Multi-Touch Trio"),
        ]),
        ("P5 · Body Sensing", "p5", [
            (p5_1_mocap_skeleton,   "P5.1 · Mocap Skeleton"),
            (p5_2_heartbeat_body,   "P5.2 · Heartbeat Body"),
            (p5_3_anatomical_eye,   "P5.3 · Anatomical Eye"),
        ]),
        ("P6 · Korean Person", "p6", [
            (p6_1_hangul_siot,      "P6.1 · Hangul ㅅ"),
            (p6_2_bowing_figure,    "P6.2 · Bowing Figure"),
            (p6_3_hanbok_pair,      "P6.3 · Hanbok Pair"),
        ]),
    ]
    all_paths: list[Path] = []
    all_labels: list[str] = []
    for title, prefix, items in batches:
        paths, labels = [], []
        for fn, label in items:
            slug = fn.__name__
            paths.append(write_pair(f"axis_{slug}", fn()))
            labels.append(label)
        sheet_path = OUT / f"_sheet_{prefix}.png"
        build_contact_sheet(paths, labels, title, sheet_path)
        print(f"  → {sheet_path.relative_to(ROOT)}")
        all_paths.extend(paths)
        all_labels.extend(labels)
    master = OUT / "_people_master_sheet.png"
    build_master_sheet(all_paths, all_labels, master)
    print(f"  → {master.relative_to(ROOT)}")
    print("done.")


if __name__ == "__main__":
    main()
