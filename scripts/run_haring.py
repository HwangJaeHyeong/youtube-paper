"""HaRing -> shorts (local only)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import AUDIO_DIR, PAPERS_DIR, SCRIPTS_DIR, VIDEOS_DIR, SHORTS_RESOLUTION
from src.ingest import pdf_parser
from src.script import shorts_generator
from src import tts
from src.video import audio_merger, composer, figure_cropper, figure_indexer, slide_maker, subtitle, title_card


def main() -> None:
    pdf = PAPERS_DIR / "3772318.3791663.pdf"
    slug = "haring-uist2025"
    shorts_slug = f"{slug}-shorts"

    paper = pdf_parser.parse(pdf)
    cleaned = "".join(
        ch for ch in paper.text
        if not (0xE000 <= ord(ch) <= 0xF8FF) and not (0xD800 <= ord(ch) <= 0xDFFF)
    )
    paper.text = cleaned

    title = "HaRing: A Haptic Ring Interface for One-Handed Interaction with High-Dimensional Spatial Information"
    authors = ["Suheon Nam", "Juhyung Son", "Seungmoon Choi", "Chaeyong Park"]
    venue = "UIST 2025 / POSTECH + Korea University"

    print("1/3 script (rounds=1)", flush=True)
    data = shorts_generator.generate_from_paper_iterative(
        paper_title=title, authors=authors, venue=venue,
        paper_text=paper.text, slug=slug, rounds=1, lang="ko",
    )
    data.setdefault("metadata", {})["official_url"] = "https://dl.acm.org/doi/10.1145/3772318.3791663"

    # Inject title intro line
    lines_ = data["script"]
    if lines_ and lines_[0].get("visual_ref") == "__TITLE__":
        lines_.pop(0)
    host = lines_[0].get("speaker", "민재")
    intro_text = data.get("title_hook") or title
    lines_.insert(0, {
        "section": "intro", "speaker": host, "text": intro_text,
        "emotion": "neutral", "pause_after_ms": 400,
        "visual_ref": "__TITLE__", "skip_subtitle": True,
    })
    (SCRIPTS_DIR / f"{shorts_slug}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("2/3 TTS", flush=True)
    line_dir = AUDIO_DIR / shorts_slug / "lines"
    line_dir.mkdir(parents=True, exist_ok=True)
    wavs, pairs = [], []
    for i, line in enumerate(data["script"]):
        wav = line_dir / f"{i:03d}_{line['speaker']}.wav"
        if not wav.exists():
            tts.synthesize(line["text"], line["speaker"], wav, emotion=line.get("emotion", "neutral"))
        wavs.append(wav); pairs.append((wav, int(line.get("pause_after_ms", 200))))
    mp3 = AUDIO_DIR / shorts_slug / f"{shorts_slug}.mp3"
    audio_merger.merge(pairs, mp3)

    print("3/3 video", flush=True)
    pages_dir = AUDIO_DIR / shorts_slug / "pages"
    pages = slide_maker.render_pages(pdf, pages_dir, dpi=150) if not list(pages_dir.glob("*.png")) else sorted(pages_dir.glob("*.png"))
    fig_index = figure_indexer.build_index(pdf)
    print(f"  figures: {fig_index}", flush=True)

    crops_dir = AUDIO_DIR / shorts_slug / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    crops = {}
    for line in data["script"]:
        ref = figure_cropper.normalize_ref(line.get("visual_ref"))
        if not ref or ref in crops or ref == "__TITLE__":
            continue
        if not fig_index.get(ref):
            continue
        out_png = crops_dir / f"{ref.replace(' ', '_')}.png"
        if not out_png.exists():
            figure_cropper.crop_visual(pdf, fig_index[ref], ref, out_png)
        crops[ref] = out_png

    cover = AUDIO_DIR / shorts_slug / "cover.png"
    title_card.render_cover(cover)
    tc = crops_dir / "__TITLE__.png"
    intro_line = next((l for l in data["script"] if l.get("visual_ref") == "__TITLE__"), None)
    card_text = (intro_line["text"] if intro_line else None) or intro_text
    title_card.render_title_card(card_text, tc, size=SHORTS_RESOLUTION)
    crops["__TITLE__"] = tc

    line_is_cover = [figure_cropper.normalize_ref(l.get("visual_ref")) not in crops for l in data["script"]]
    ass = AUDIO_DIR / shorts_slug / f"{shorts_slug}.ass"
    subtitle.build_ass(data["script"], wavs, ass, line_is_cover=line_is_cover)
    segments = composer.build_segments_v2(data["script"], wavs, pages, fig_index, crops, fallback_img=cover)
    out_mp4 = VIDEOS_DIR / f"{shorts_slug}.mp4"
    composer.compose_shorts(mp3, ass, pages, segments, out_mp4)
    print(f"  mp4: {out_mp4}", flush=True)


if __name__ == "__main__":
    main()
