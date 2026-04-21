"""Run Gemini TTS for all lines of an existing script JSON, then merge to MP3.

Resumable — skips lines whose WAV already exists.

Usage:
    python scripts/tts_run.py attention-is-all-you-need
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import tts
from src.config import AUDIO_DIR, SCRIPTS_DIR
from src.video.audio_merger import merge


def run(slug: str) -> None:
    script_path = SCRIPTS_DIR / f"{slug}.json"
    data = json.loads(script_path.read_text(encoding="utf-8"))
    lines = data["script"]
    line_dir = AUDIO_DIR / slug / "lines"
    line_dir.mkdir(parents=True, exist_ok=True)

    line_files: list[tuple[Path, int]] = []
    total = len(lines)
    for i, line in enumerate(lines):
        out = line_dir / f"{i:03d}_{line['speaker']}.wav"
        pause = int(line.get("pause_after_ms", 200))
        line_files.append((out, pause))
        if out.exists():
            continue
        preview = line["text"][:50].replace("\n", " ")
        print(f"[{i+1:>3}/{total}] {line['speaker']}: {preview}", flush=True)
        for attempt in range(5):
            try:
                tts.synthesize(line["text"], line["speaker"], out, emotion=line.get("emotion", "neutral"))
                break
            except Exception as e:
                wait = 2 ** attempt
                print(f"    retry in {wait}s ({type(e).__name__}: {str(e)[:120]})", flush=True)
                time.sleep(wait)
        else:
            print(f"    FAILED after 5 attempts, skipping")

    merged = AUDIO_DIR / slug / f"{slug}.mp3"
    merge(line_files, merged)
    print(f"\nMerged: {merged} ({merged.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "attention-is-all-you-need")
