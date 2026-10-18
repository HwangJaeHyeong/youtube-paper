"""Generate RNN and CNN architecture diagrams via Pollinations.ai for the
Attention shorts. Drops PNGs into the slug's crops/ folder so the pipeline
picks them up automatically (no PDF index needed)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import AUDIO_DIR, SHORTS_RESOLUTION
from src.anime import image_gen

SLUG = "attention-mental-shorts"
crops_dir = AUDIO_DIR / SLUG / "crops"
crops_dir.mkdir(parents=True, exist_ok=True)

PROMPTS = [
    (
        "RNN.png",
        "minimalist flat infographic of recurrent neural network, "
        "a horizontal chain of five identical rounded squares connected by right-pointing arrows, "
        "small loop arrow on each square, blue and white color palette, "
        "thick clean outlines, pure white background, vector style, no text labels",
    ),
    (
        "CNN.png",
        "minimalist flat infographic of convolutional neural network, "
        "five stacked rectangular slices going from large to small left to right, "
        "each slice a different shade of blue, simple sliding-window box on the leftmost slice, "
        "thick clean outlines, pure white background, vector style, no text labels",
    ),
]

for fname, prompt in PROMPTS:
    out = crops_dir / fname
    print(f"Generating {fname}...", flush=True)
    try:
        image_gen.generate(prompt, out, size=SHORTS_RESOLUTION)
        print(f"  OK  {out}  ({out.stat().st_size} bytes)")
    except Exception as e:
        print(f"  FAIL  {e}")
