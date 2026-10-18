"""Generate AI background images for romance-baiting-shorts null visual_refs.

Uses Gemini 2.5 Flash Image (Nano Banana) — ~$0.04 per image.
Saves PNGs to crops dir as scene_l{idx}.png and rewrites JSON visual_refs.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from google.genai import types
from PIL import Image
import io

from src.config import GOOGLE_API_KEY, SCRIPTS_DIR, AUDIO_DIR

SLUG = "romance-baiting-shorts"
MODEL = "gemini-2.5-flash-image"

PROMPTS = {
    2: "Vertical 9:16 cinematic photograph of a dim crowded sweatshop room with tired workers hunched over many smartphones and laptops typing scam messages, fluorescent lighting, gritty documentary mood, slightly desaturated, no readable text on screens, no overlays, leaves bottom third visually calmer for subtitle.",
    6: "Vertical 9:16 cinematic dark moody background, deep red and black gradient with subtle smoke and fog, ominous suspense reveal aesthetic, no characters, no text, slow horror movie vibe, leaves bottom third calmer for subtitle.",
    7: "Vertical 9:16 illustration of broken AI safety alarm, red warning lights flashing, abstract digital glitch aesthetic with shattered shield icons, dark cybersecurity vibe, no readable text or logos, leaves bottom calmer for subtitle.",
    8: "Vertical 9:16 photograph of countless glowing chat message bubbles flooding a dark navy background, neon pink and blue accents, abstract data visualization mood, no readable text, leaves bottom calmer for subtitle.",
    9: "Vertical 9:16 cinematic shot of a smartphone screen showing a dating app profile with a faceless silhouette where the photo should be, replaced with a glowing question mark, soft pink purple bokeh lighting, melancholy suspicious mood, no readable text, leaves bottom calmer for subtitle.",
}


def gen_image(client: genai.Client, prompt: str, out: Path) -> None:
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
            )
            for part in resp.candidates[0].content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    img = Image.open(io.BytesIO(part.inline_data.data))
                    # ensure 1080x1920 vertical
                    img = img.convert("RGB")
                    target_w, target_h = 1080, 1920
                    img.thumbnail((target_w, target_h), Image.LANCZOS)
                    canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
                    px = (target_w - img.width) // 2
                    py = (target_h - img.height) // 2
                    canvas.paste(img, (px, py))
                    out.parent.mkdir(parents=True, exist_ok=True)
                    canvas.save(out, "PNG")
                    return
            raise RuntimeError("no image part in response")
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "429" in msg or "rate" in msg or "quota" in msg or "resource_exhausted" in msg:
                wait = 20 + 5 * attempt
                print(f"  rate limited, sleep {wait}s")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"image gen exhausted retries: {last_err}")


def main() -> None:
    if not GOOGLE_API_KEY:
        raise SystemExit("GOOGLE_API_KEY missing in .env")
    client = genai.Client(api_key=GOOGLE_API_KEY)

    json_path = SCRIPTS_DIR / f"{SLUG}.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    crops_dir = AUDIO_DIR / SLUG / "crops"

    for idx, prompt in PROMPTS.items():
        line_text = data["script"][idx]["text"]
        out = crops_dir / f"scene_l{idx}.png"
        print(f"[{idx}] {line_text[:50]}...")
        print(f"     -> {out.name}")
        gen_image(client, prompt, out)
        data["script"][idx]["visual_ref"] = f"scene_l{idx}"

    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nupdated: {json_path}")
    print(f"images : {crops_dir}")


if __name__ == "__main__":
    main()
