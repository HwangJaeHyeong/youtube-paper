"""Generate an LLM logo collage (2x2 grid of brand-colored name pills) for the
'ChatGPT, 제미나이, 클로드' line. Saved as LLM.png in the slug's crops folder."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import AUDIO_DIR

W, H = 1080, 1920
OUT = AUDIO_DIR / "attention-mental-shorts" / "crops" / "LLM.png"
OUT.parent.mkdir(parents=True, exist_ok=True)
FONT_PATH = "/Library/Fonts/Pretendard-Black.otf"

# AI assistants with their canonical brand colors.
LABELS = [
    ("ChatGPT",  (16, 163, 127)),    # OpenAI green
    ("Gemini",   (66, 133, 244)),    # Google blue
    ("Claude",   (204, 120, 92)),    # Anthropic copper
    ("Llama",    (29, 78, 216)),     # Meta blue
]

img = Image.new("RGB", (W, H), (12, 14, 24))   # near-black background
draw = ImageDraw.Draw(img)

# 2x2 grid layout, vertically centered
cols, rows = 2, 2
margin_top = int(H * 0.18)
margin_bot = int(H * 0.18)
grid_h = H - margin_top - margin_bot
cell_w = W // cols
cell_h = grid_h // rows

font = ImageFont.truetype(FONT_PATH, 90)

for i, (name, color) in enumerate(LABELS):
    col = i % cols
    row = i // cols
    cx = col * cell_w + cell_w // 2
    cy = margin_top + row * cell_h + cell_h // 2

    bbox = draw.textbbox((0, 0), name, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 38, 26

    # Colored pill background
    rect = (cx - tw // 2 - pad_x, cy - th // 2 - pad_y,
            cx + tw // 2 + pad_x, cy + th // 2 + pad_y)
    draw.rounded_rectangle(rect, radius=60, fill=color)

    # White text
    draw.text((cx - tw // 2, cy - th // 2 - 8), name, font=font, fill=(255, 255, 255))

img.save(OUT, "PNG")
print(f"OK: {OUT} ({OUT.stat().st_size} bytes)")
