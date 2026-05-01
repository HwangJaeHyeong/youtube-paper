"""One-off: augmenting.pdf -> shorts with rounds=5 -> schedule tomorrow 21:00."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import AUDIO_DIR, PAPERS_DIR, SCRIPTS_DIR, VIDEOS_DIR
from src.ingest import pdf_parser
from src.script import shorts_generator
from src.video import audio_merger, composer, figure_cropper, figure_indexer, slide_maker, subtitle, title_card
from src import tts
from src.upload import youtube as yt_upload


def main() -> None:
    pdf = PAPERS_DIR / "augmenting.pdf"
    slug = "augmenting-length-chi2026"
    shorts_slug = f"{slug}-shorts"

    paper = pdf_parser.parse(pdf)
    # Strip PDF math-symbol private-use chars + lone surrogates that crash Claude CLI encoding.
    cleaned = "".join(
        ch for ch in paper.text
        if not (0xE000 <= ord(ch) <= 0xF8FF) and not (0xD800 <= ord(ch) <= 0xDFFF)
    )
    paper.text = cleaned
    title = "Augmenting Perceived Length of Handheld Controllers: Effects of Object Handle Properties"
    authors = ["Chaeyong Park", "Seungmoon Choi"]
    venue = "CHI 2026 / POSTECH Interaction Lab"

    print("1/4 script (rounds=1)", flush=True)
    data = shorts_generator.generate_from_paper_iterative(
        paper_title=title, authors=authors, venue=venue,
        paper_text=paper.text, slug=slug, rounds=1, lang="ko",
    )

    # Post-process: fill null visual_refs by heuristic mapping against line text.
    from src.video import figure_indexer
    fig_index = figure_indexer.build_index(pdf)
    available = [r for r in fig_index.keys() if r in {f"Figure {i}" for i in range(1, 11)} or r == "Table 1"]
    keyword_map = [
        (["길이", "teaser", "재질", "컨트롤러", "소개"], "Figure 1"),
        (["실험 구조", "물체", "구조", "같은 막대"], "Figure 2"),
        (["부드러", "softness", "실험 1", "exp 1"], "Figure 5"),
        (["열", "thermal", "conductivity", "차가", "실험 2"], "Figure 7"),
        (["거친", "texture", "범프", "돌기", "실험 3"], "Figure 9"),
        (["전체", "요약", "종합", "비교", "순위"], "Figure 10"),
        (["효과 크기", "effect size", "세다", "제일"], "Table 1"),
        (["참가자", "손", "잡고", "설정"], "Figure 4"),
    ]
    used_round_robin = [r for r in ["Figure 1","Figure 2","Figure 3","Figure 4","Figure 5","Figure 6","Figure 7","Figure 8","Figure 9","Figure 10","Table 1"] if r in fig_index]
    rr_idx = 0
    for line in data["script"]:
        if line.get("visual_ref"):
            continue
        text = line.get("text", "")
        assigned = None
        for kws, ref in keyword_map:
            if any(kw in text for kw in kws) and ref in fig_index:
                assigned = ref; break
        if not assigned and used_round_robin:
            assigned = used_round_robin[rr_idx % len(used_round_robin)]
            rr_idx += 1
        line["visual_ref"] = assigned
    from src.config import SCRIPTS_DIR as _SD
    (_SD / f"{slug}-shorts.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    data.setdefault("metadata", {})["official_url"] = "https://dl.acm.org/doi/10.1145/3706598.3714014"

    # Inject title intro
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

    print("2/4 TTS")
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

    print("3/4 video")
    pages_dir = AUDIO_DIR / shorts_slug / "pages"
    pages = slide_maker.render_pages(pdf, pages_dir, dpi=150) if not list(pages_dir.glob("*.png")) else sorted(pages_dir.glob("*.png"))
    fig_index = figure_indexer.build_index(pdf)
    print(f"  figures: {fig_index}")

    crops_dir = AUDIO_DIR / shorts_slug / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    crops = {}
    for line in data["script"]:
        ref = figure_cropper.normalize_ref(line.get("visual_ref"))
        if not ref or ref in crops or not fig_index.get(ref):
            continue
        out_png = crops_dir / f"{ref.replace(' ', '_')}.png"
        if not out_png.exists():
            figure_cropper.crop_visual(pdf, fig_index[ref], ref, out_png)
        crops[ref] = out_png

    from src.config import SHORTS_RESOLUTION
    cover = AUDIO_DIR / shorts_slug / "cover.png"
    title_card.render_cover(cover)
    tc = crops_dir / "__TITLE__.png"
    title_card.render_title_card(intro_text, tc, size=SHORTS_RESOLUTION)
    crops["__TITLE__"] = tc

    line_is_cover = [figure_cropper.normalize_ref(l.get("visual_ref")) not in crops for l in data["script"]]
    ass = AUDIO_DIR / shorts_slug / f"{shorts_slug}.ass"
    subtitle.build_ass(data["script"], wavs, ass, line_is_cover=line_is_cover)
    segments = composer.build_segments_v2(data["script"], wavs, pages, fig_index, crops, fallback_img=cover)
    out_mp4 = VIDEOS_DIR / f"{shorts_slug}.mp4"
    composer.compose_shorts(mp3, ass, pages, segments, out_mp4)
    print(f"  mp4: {out_mp4}")

    print("4/4 upload scheduled 2026-04-26 21:00 KST")
    title_hook = data.get("title_hook") or title
    primary_tag = (data.get("primary_tag") or "HCI").replace(" ", "")
    hashtag_line = f"#논문리뷰 #HCI #햅틱스 #VR #{primary_tag} #Shorts"
    verdict = data.get("rating", {}).get("verdict", "")
    description = (
        f"{title}\n\n"
        f"한줄평: {verdict}\n\n"
        f"📄 논문 원문: {data['metadata']['official_url']}\n\n"
        f"{hashtag_line}\n\n"
        f"Generated by PaperCast."
    )
    tags = ["논문리뷰", "HCI", "햅틱스", "VR", "CHI", "POSTECH", primary_tag, "Shorts"]
    vid = yt_upload.upload(
        out_mp4, title_hook, description, tags,
        privacy_status="public", is_shorts=True,
        publish_at="2026-04-26T21:00:00+09:00",
    )
    print(f"video_id: {vid}")


if __name__ == "__main__":
    main()
