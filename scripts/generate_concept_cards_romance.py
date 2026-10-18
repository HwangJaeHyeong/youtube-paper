"""Render PIL concept cards for romance-baiting null-visual lines.

Free, instant — no API calls. Each null line gets a themed keyword card
saved as crops/scene_l{idx}.png and the JSON's visual_ref is rewritten.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import SCRIPTS_DIR, AUDIO_DIR
from src.video.concept_card import render_concept

SLUG = "romance-baiting-shorts"

# (line_idx, keyword, bg_top, bg_bottom, accent, glow_color)
CARDS = [
    (
        2,
        "인신매매\n피해자",
        (16, 8, 8), (66, 14, 12),
        (255, 220, 80), (160, 30, 30),
    ),
    (
        6,
        "근데...",
        (8, 6, 14), (90, 12, 20),
        (255, 80, 80), (140, 0, 0),
    ),
    (
        7,
        "안전 필터\n0건",
        (24, 14, 4), (110, 60, 0),
        (255, 200, 60), (200, 100, 0),
    ),
    (
        8,
        "87%",
        (6, 16, 32), (10, 60, 100),
        (110, 220, 255), (40, 110, 220),
    ),
    (
        9,
        "진짜 사람\n맞아요?",
        (22, 8, 28), (80, 14, 70),
        (255, 180, 220), (160, 40, 140),
    ),
]


def main() -> None:
    json_path = SCRIPTS_DIR / f"{SLUG}.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    crops_dir = AUDIO_DIR / SLUG / "crops"

    for idx, kw, bg_top, bg_bot, accent, glow in CARDS:
        out = crops_dir / f"scene_l{idx}.png"
        render_concept(
            kw, out,
            bg_top=bg_top, bg_bottom=bg_bot,
            accent=accent, glow=glow, seed=idx,
        )
        kw_compact = kw.replace("\n", " ")
        line_text = data["script"][idx]["text"]
        print(f"[{idx}] {kw_compact:18s} -> {out.name}  ({line_text[:40]}...)")
        data["script"][idx]["visual_ref"] = f"scene_l{idx}"

    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nupdated: {json_path}")
    print(f"images : {crops_dir}")


if __name__ == "__main__":
    main()
