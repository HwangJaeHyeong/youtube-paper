"""Generate AXIS Lab symbol-only marks (no wordmark).

Each mark targets a clearly-readable HCI motif so the viewer instantly
understands "human–computer interaction" from the icon alone:

  M1 · Touch Ripple      — fingertip + concentric haptic rings
  M2 · Cursor on Origin  — pointer landing at axis intersection
  M3 · Pinch Gesture     — two fingertips + arc trail
  M4 · Reach into Cube   — pointer finger entering an iso cube (AR)
  M5 · Haptic Pulse      — fingertip + sine wave emanating
  M6 · AR Reticle        — crosshair inside ring (spatial targeting)

All marks: 1024x1024 transparent SVG + PNG, ink/crimson palette.
"""
from __future__ import annotations

import math
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "logos" / "marks"
OUT.mkdir(parents=True, exist_ok=True)

KU_CRIMSON = "#862633"
INK = "#0A0A0A"
DIM = "#5A5A5A"


def svg(body: str, w: int = 1024, h: int = 1024) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">{body}</svg>'
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
# M1 — Touch Ripple
#   Crimson fingertip dot at center; 3 concentric ink rings expanding outward
#   = the universal "touch input + haptic feedback" symbol.
# ---------------------------------------------------------------------------
def mark_touch_ripple() -> str:
    cx, cy = 512, 512
    body = f"""
    <g fill="none" stroke="{INK}" stroke-linecap="round">
      <circle cx="{cx}" cy="{cy}" r="170" stroke-width="22"/>
      <circle cx="{cx}" cy="{cy}" r="270" stroke-width="18" opacity="0.7"/>
      <circle cx="{cx}" cy="{cy}" r="380" stroke-width="14" opacity="0.4"/>
    </g>
    <circle cx="{cx}" cy="{cy}" r="78" fill="{KU_CRIMSON}"/>
    """
    return svg(body)


# ---------------------------------------------------------------------------
# M2 — Cursor on Origin
#   A classic arrow cursor whose tip lands precisely at the origin of a
#   coordinate cross. "Pointer interacting with axes" — pure HCI iconography.
# ---------------------------------------------------------------------------
def mark_cursor_origin() -> str:
    # axes
    axes = f"""
      <line x1="180" y1="512" x2="844" y2="512" stroke="{INK}"
            stroke-width="22" stroke-linecap="round"/>
      <line x1="512" y1="180" x2="512" y2="844" stroke="{INK}"
            stroke-width="22" stroke-linecap="round"/>
    """
    # arrow cursor — classic shape, tip at (512, 512), pointing up-left
    # Path drawn so the tip is at origin and the body extends down-right
    cursor = f"""
      <path d="M 512 512
               L 720 596
               L 622 612
               L 690 770
               L 638 798
               L 568 638
               L 488 700
               Z"
            fill="{KU_CRIMSON}" stroke="{INK}" stroke-width="14"
            stroke-linejoin="round"/>
    """
    return svg(axes + cursor)


# ---------------------------------------------------------------------------
# M3 — Pinch Gesture
#   Two fingertip dots with a curved dashed arc between them, suggesting
#   pinch-to-zoom / two-finger gesture.
# ---------------------------------------------------------------------------
def mark_pinch() -> str:
    # two fingertip circles
    p1 = (320, 700)
    p2 = (704, 324)
    # dashed arc connecting them (control point pulled outward)
    arc = (
        f'<path d="M {p1[0]} {p1[1]} Q 380 320 {p2[0]} {p2[1]}" '
        f'fill="none" stroke="{INK}" stroke-width="14" '
        f'stroke-dasharray="6 22" stroke-linecap="round"/>'
    )
    # small expand arrows at midpoint
    mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    expand = f"""
      <g stroke="{INK}" stroke-width="14" stroke-linecap="round" fill="none">
        <line x1="{mid[0]-50}" y1="{mid[1]+50}" x2="{mid[0]-110}" y2="{mid[1]+110}"/>
        <line x1="{mid[0]-110}" y1="{mid[1]+110}" x2="{mid[0]-110}" y2="{mid[1]+60}"/>
        <line x1="{mid[0]-110}" y1="{mid[1]+110}" x2="{mid[0]-60}" y2="{mid[1]+110}"/>
        <line x1="{mid[0]+50}" y1="{mid[1]-50}" x2="{mid[0]+110}" y2="{mid[1]-110}"/>
        <line x1="{mid[0]+110}" y1="{mid[1]-110}" x2="{mid[0]+110}" y2="{mid[1]-60}"/>
        <line x1="{mid[0]+110}" y1="{mid[1]-110}" x2="{mid[0]+60}" y2="{mid[1]-110}"/>
      </g>
    """
    body = f"""
    {arc}
    {expand}
    <circle cx="{p1[0]}" cy="{p1[1]}" r="68" fill="{KU_CRIMSON}"/>
    <circle cx="{p2[0]}" cy="{p2[1]}" r="68" fill="{KU_CRIMSON}"/>
    """
    return svg(body)


# ---------------------------------------------------------------------------
# M4 — Touch on Cube
#   Iso cube wireframe with a crimson tap-point + ripples on the top vertex.
#   Reads as "touch interaction with a 3D / spatial object" without the
#   colour-palette break that a literal hand silhouette introduces.
# ---------------------------------------------------------------------------
def mark_touch_cube() -> str:
    cx, cy = 512, 560
    s = 260
    rx, ry = math.cos(math.radians(30)), math.sin(math.radians(30))
    top = (cx, cy - s)
    right = (cx + s * rx, cy - s + s * ry)
    left = (cx - s * rx, cy - s + s * ry)
    midR = (cx + s * rx, cy + s * ry)
    midL = (cx - s * rx, cy + s * ry)
    bottom = (cx, cy + 2 * s * ry)
    center = (cx, cy - s + 2 * s * ry)
    cube = f"""
      <g fill="none" stroke="{INK}" stroke-width="22" stroke-linejoin="round"
         stroke-linecap="round">
        <polygon points="{top[0]},{top[1]} {right[0]:.0f},{right[1]:.0f} {midR[0]:.0f},{midR[1]:.0f} {bottom[0]},{bottom[1]} {midL[0]:.0f},{midL[1]:.0f} {left[0]:.0f},{left[1]:.0f}"/>
        <line x1="{top[0]}" y1="{top[1]}" x2="{center[0]:.0f}" y2="{center[1]:.0f}" stroke-width="14" opacity="0.55"/>
        <line x1="{left[0]:.0f}" y1="{left[1]:.0f}" x2="{center[0]:.0f}" y2="{center[1]:.0f}" stroke-width="14" opacity="0.55"/>
        <line x1="{right[0]:.0f}" y1="{right[1]:.0f}" x2="{center[0]:.0f}" y2="{center[1]:.0f}" stroke-width="14" opacity="0.55"/>
      </g>
    """
    # touch point + ripple arcs at the top vertex
    tap_x, tap_y = top
    ripples = f"""
      <g fill="none" stroke="{INK}" stroke-linecap="round">
        <path d="M {tap_x-90} {tap_y-30} A 100 100 0 0 1 {tap_x+90} {tap_y-30}"
              stroke-width="14" opacity="0.7"/>
        <path d="M {tap_x-150} {tap_y-60} A 170 170 0 0 1 {tap_x+150} {tap_y-60}"
              stroke-width="12" opacity="0.4"/>
      </g>
      <circle cx="{tap_x}" cy="{tap_y}" r="40" fill="{KU_CRIMSON}"/>
    """
    return svg(cube + ripples)


# ---------------------------------------------------------------------------
# M5 — Haptic Pulse
#   Fingertip on left + sine wave emanating to the right. Explicit haptic
#   identity (matches AXIS lab's haptics focus).
# ---------------------------------------------------------------------------
def mark_haptic_pulse() -> str:
    # fingertip on left
    fx, fy = 280, 512
    # sine wave from x=fx to x=900 along baseline y=fy
    def sine_path(x0, y0, length, amp, cycles, samples=240):
        pts = []
        for i in range(samples + 1):
            t = i / samples
            x = x0 + t * length
            # ease-in amplitude (starts small near fingertip, grows)
            ramp = min(1.0, t * 1.6)
            y = y0 - amp * ramp * math.sin(2 * math.pi * cycles * t)
            pts.append(f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}")
        return " ".join(pts)
    wave = sine_path(fx + 80, fy, 600, amp=120, cycles=2.5)
    # tap rings around fingertip
    body = f"""
      <g fill="none" stroke="{INK}" stroke-width="14" stroke-linecap="round">
        <circle cx="{fx}" cy="{fy}" r="120" opacity="0.55"/>
        <circle cx="{fx}" cy="{fy}" r="180" opacity="0.25"/>
      </g>
      <circle cx="{fx}" cy="{fy}" r="70" fill="{KU_CRIMSON}"/>
      <path d="{wave}" fill="none" stroke="{INK}" stroke-width="22"
            stroke-linecap="round"/>
    """
    return svg(body)


# ---------------------------------------------------------------------------
# M6 — AR Reticle
#   Crosshair inside a ring with corner brackets — the camera/AR targeting
#   reticle motif. Spatial computing identity.
# ---------------------------------------------------------------------------
def mark_ar_reticle() -> str:
    cx, cy = 512, 512
    body = f"""
      <g fill="none" stroke="{INK}" stroke-linecap="round">
        <!-- outer ring -->
        <circle cx="{cx}" cy="{cy}" r="280" stroke-width="22"/>
        <!-- crosshair -->
        <line x1="{cx-200}" y1="{cy}" x2="{cx-90}" y2="{cy}" stroke-width="22"/>
        <line x1="{cx+90}"  y1="{cy}" x2="{cx+200}" y2="{cy}" stroke-width="22"/>
        <line x1="{cx}" y1="{cy-200}" x2="{cx}" y2="{cy-90}" stroke-width="22"/>
        <line x1="{cx}" y1="{cy+90}"  x2="{cx}" y2="{cy+200}" stroke-width="22"/>
        <!-- AR corner brackets -->
        <polyline points="{cx-380},{cy-300} {cx-380},{cy-380} {cx-300},{cy-380}" stroke-width="22"/>
        <polyline points="{cx+300},{cy-380} {cx+380},{cy-380} {cx+380},{cy-300}" stroke-width="22"/>
        <polyline points="{cx-380},{cy+300} {cx-380},{cy+380} {cx-300},{cy+380}" stroke-width="22"/>
        <polyline points="{cx+300},{cy+380} {cx+380},{cy+380} {cx+380},{cy+300}" stroke-width="22"/>
      </g>
      <!-- center crimson dot -->
      <circle cx="{cx}" cy="{cy}" r="40" fill="{KU_CRIMSON}"/>
    """
    return svg(body)


# ---------------------------------------------------------------------------
# Contact sheet — composite all 6 marks
# ---------------------------------------------------------------------------
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
              "AXIS Lab — Symbol Marks (HCI motifs)",
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
    print("Generating AXIS Lab symbol marks ...")
    marks = [
        ("m1_touch_ripple",  mark_touch_ripple,  "M1 · Touch Ripple"),
        ("m2_cursor_origin", mark_cursor_origin, "M2 · Cursor on Origin"),
        ("m3_pinch",         mark_pinch,         "M3 · Pinch Gesture"),
        ("m4_touch_cube",    mark_touch_cube,    "M4 · Touch on Cube"),
        ("m5_haptic_pulse",  mark_haptic_pulse,  "M5 · Haptic Pulse"),
        ("m6_ar_reticle",    mark_ar_reticle,    "M6 · AR Reticle"),
    ]
    paths, labels = [], []
    for slug, fn, label in marks:
        paths.append(write_pair(f"axis_{slug}", fn()))
        labels.append(label)
    build_contact_sheet(paths, labels, OUT / "_marks_contact_sheet.png")
    print(f"  contact sheet → {(OUT / '_marks_contact_sheet.png').relative_to(ROOT)}")
    print("done.")


if __name__ == "__main__":
    main()
