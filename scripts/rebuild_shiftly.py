"""Build shiftly shorts (TU Wien VR&AR Group, IEEE TVCG @ IEEE VR 2025)."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import SCRIPTS_DIR
from src.pipeline import _generate_video, _run_tts_and_merge

SLUG = "shiftly-shorts"

def main() -> None:
    t = time.time()
    json_path = SCRIPTS_DIR / f"{SLUG}.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    print("=" * 70)
    print(f"Build: {SLUG}  ({len(data['script'])} lines)")
    print("=" * 70)
    for i, ln in enumerate(data["script"]):
        print(f"  [{i}] {ln['text']}")
    print("\n[1/2] CLOVA TTS...", flush=True)
    mp3, wavs, _ = _run_tts_and_merge(data, SLUG)
    print(f"      {len(wavs)} wavs / {mp3}", flush=True)
    print("\n[2/2] Build shorts...", flush=True)
    out = _generate_video(SLUG, json_path, mp3, is_shorts=True, subtitle_style="hype", sticky_visuals=False)
    print(f"\nDONE in {time.time() - t:.1f}s\nVideo: {out}")

if __name__ == "__main__":
    main()
