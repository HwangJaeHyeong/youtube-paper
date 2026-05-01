"""Generic local-only shorts builder. Usage: run_local_shorts.py <pdf-name> <slug> <title>"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import AUDIO_DIR, PAPERS_DIR, SCRIPTS_DIR, VIDEOS_DIR, SHORTS_RESOLUTION
from src.ingest import pdf_parser
from src.script import shorts_generator
from src import tts
from src.video import audio_merger, composer, figure_cropper, figure_indexer, slide_maker, subtitle, title_card


def main(pdf_name: str, slug: str, title: str, authors: list[str], venue: str, official_url: str = "") -> None:
    pdf = PAPERS_DIR / pdf_name
    shorts_slug = f"{slug}-shorts"

    paper = pdf_parser.parse(pdf)
    cleaned = "".join(
        ch for ch in paper.text
        if not (0xE000 <= ord(ch) <= 0xF8FF) and not (0xD800 <= ord(ch) <= 0xDFFF)
    )
    paper.text = cleaned

    print(f"1/3 script (rounds=1) — {slug}", flush=True)
    data = shorts_generator.generate_from_paper_iterative(
        paper_title=title, authors=authors, venue=venue,
        paper_text=paper.text, slug=slug, rounds=1, lang="ko",
    )
    if official_url:
        data.setdefault("metadata", {})["official_url"] = official_url

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
    paper_id = sys.argv[1]
    if paper_id == "c5":
        main(
            "c5-Augmenting Physical Buttons.pdf",
            "c5-augmenting-buttons",
            "Augmenting Physical Buttons with Vibrotactile Feedback for Programmable Feels",
            ["Chaeyong Park", "Jinhyuk Yoon", "Seungjae Oh", "Seungmoon Choi"],
            "POSTECH Interaction Lab",
        )
    elif paper_id == "c7":
        main(
            "c7-Vibration-Augmented Buttons.pdf",
            "c7-vibration-buttons",
            "Vibration-Augmented Buttons: Information Transmission Capacity and Application to Interaction Design",
            ["Chaeyong Park", "Jeongwoo Kim", "Dong-Geun Kim", "Seungjae Oh"],
            "POSTECH Interaction Lab",
        )
    elif paper_id == "c9":
        main(
            "c9-Visuo-haptic Crossmodal Shape Perception Model.pdf",
            "c9-visuohaptic-shape",
            "Visuo-haptic Crossmodal Shape Perception Model for Shape-Changing Handheld Controllers Bridged by Inertial Tensor",
            ["Chaeyong Park", "Jeongwoo Kim", "Seungmoon Choi"],
            "POSTECH Interaction Lab",
        )
    elif paper_id == "alexnet":
        main(
            "alexnet-nips2012.pdf",
            "alexnet-nips2012",
            "ImageNet Classification with Deep Convolutional Neural Networks",
            ["Alex Krizhevsky", "Ilya Sutskever", "Geoffrey E. Hinton"],
            "NeurIPS 2012, University of Toronto",
            "https://papers.nips.cc/paper_files/paper/2012/hash/c399862d3b9d6b76c8436e924a68c45b-Abstract.html",
        )
    elif paper_id == "zerocash":
        main(
            "zerocash-2014.pdf",
            "zerocash-2014",
            "Zerocash: Decentralized Anonymous Payments from Bitcoin",
            ["Eli Ben-Sasson", "Alessandro Chiesa", "Christina Garman", "Matthew Green", "Ian Miers", "Eran Tromer", "Madars Virza"],
            "IEEE S&P 2014, Zcash 원조 논문",
            "https://eprint.iacr.org/2014/349",
        )
