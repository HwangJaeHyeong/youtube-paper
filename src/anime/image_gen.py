"""Per-scene image generation.

Primary: Pollinations.ai (free, no key, Flux backend).
Fallback: Gemini Nano Banana (paid, needs billing).
"""
from __future__ import annotations

import io
import time
import urllib.parse
from pathlib import Path

import requests
from PIL import Image

from src.config import SHORTS_RESOLUTION


def _pad_to(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    w, h = size
    img = img.convert("RGB")
    img.thumbnail((w, h), Image.LANCZOS)
    canvas = Image.new("RGB", size, (20, 22, 30))
    canvas.paste(img, ((w - img.width) // 2, (h - img.height) // 2))
    return canvas


def generate(prompt: str, out_path: Path, size: tuple[int, int] = SHORTS_RESOLUTION) -> Path:
    """Pollinations.ai /prompt endpoint — 9:16 vertical, anime-biased prompt."""
    w, h = size
    full_prompt = (
        f"{prompt}, cinematic anime illustration, high contrast, "
        "no text, no watermark, no logos, no signatures"
    )
    url = (
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(full_prompt)}"
        f"?width={w}&height={h}&model=flux&nologo=true&enhance=true"
    )
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            resp = requests.get(url, timeout=90)
            if resp.status_code == 200 and resp.content:
                img = Image.open(io.BytesIO(resp.content))
                out_path.parent.mkdir(parents=True, exist_ok=True)
                _pad_to(img, size).save(out_path, "PNG")
                return out_path
            last_err = RuntimeError(f"status={resp.status_code}, body={resp.text[:200]}")
        except Exception as e:
            last_err = e
        time.sleep(6 + 4 * attempt)
    raise RuntimeError(f"Pollinations failed: {last_err}")
