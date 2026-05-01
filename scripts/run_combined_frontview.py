"""Combined shorts: D-SDS (Janus) + PreciseCam (frontal bias)."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
from src.config import AUDIO_DIR, CLAUDE_MODEL, PAPERS_DIR, SCRIPTS_DIR, SHORTS_RESOLUTION, VIDEOS_DIR
from src.ingest import arxiv_fetcher, pdf_parser
from src.script.shorts_generator import POLISH_SYSTEM, SHORTS_SYSTEM, _opus_polish, _parse_first_json
from src import tts
from src.video import audio_merger, composer, figure_cropper, figure_indexer, slide_maker, subtitle, title_card


async def _generate(combined_text: str) -> dict:
    prompt = (
        "두 논문이 같은 문제(텍스트→이미지 디퓨전이 정면뷰에 과적합)를 다른 각도로 해결합니다. "
        "한 쇼츠로 묶어서, '문제 정의 + 해결법 2가지' 구조로 작성하세요. "
        "두 논문 모두 인용 + 구체 수치 활용. paper_id 는 'frontview-combined' 로.\n\n"
        f"[합본 본문]\n{combined_text[:40000]}"
    )
    options = ClaudeAgentOptions(system_prompt=SHORTS_SYSTEM, model=CLAUDE_MODEL, allowed_tools=[])
    chunks = []
    async for m in query(prompt=prompt, options=options):
        if isinstance(m, AssistantMessage):
            for b in m.content:
                if isinstance(b, TextBlock):
                    chunks.append(b.text)
    data = _parse_first_json("".join(chunks))
    print("  [opus polish]...", flush=True)
    data = await _opus_polish(data)
    return data


def main() -> None:
    slug = "frontview-combined"
    shorts_slug = f"{slug}-shorts"

    # Fetch both papers
    pdf1 = arxiv_fetcher.fetch_by_id("2303.15413", dest_dir=PAPERS_DIR, slug="d-sds")
    pdf2 = arxiv_fetcher.fetch_by_id("2501.12910", dest_dir=PAPERS_DIR, slug="precisecam")

    # Combine PDF text
    p1 = pdf_parser.parse(pdf1)
    p2 = pdf_parser.parse(pdf2)
    cleaned = lambda s: "".join(
        ch for ch in s if not (0xE000 <= ord(ch) <= 0xF8FF) and not (0xD800 <= ord(ch) <= 0xDFFF)
    )
    combined = (
        f"=== Paper A: D-SDS (Hong 2023, arXiv:2303.15413) — Janus 정의 + Score Distillation 디바이아싱 ===\n"
        f"{cleaned(p1.text)[:18000]}\n\n"
        f"=== Paper B: PreciseCam (Lim 2025, arXiv:2501.12910) — 카메라 viewpoint 정밀 제어 ===\n"
        f"{cleaned(p2.text)[:18000]}"
    )

    print("1/3 script", flush=True)
    data = asyncio.run(_generate(combined))
    data["paper_id"] = slug
    data.setdefault("metadata", {})
    data["metadata"]["target_length"] = "shorts"
    data["metadata"]["lang"] = "ko"
    data["metadata"]["official_url"] = "https://arxiv.org/abs/2303.15413"

    # Inject title intro line
    lines_ = data["script"]
    if lines_ and lines_[0].get("visual_ref") == "__TITLE__":
        lines_.pop(0)
    host = lines_[0].get("speaker", "민재")
    intro_text = data.get("title_hook") or "AI 그림이 정면만 그리는 진짜 이유"
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
    # Use paper A as primary visual source (Janus figures are recognizable).
    pages_dir = AUDIO_DIR / shorts_slug / "pages"
    pages = slide_maker.render_pages(pdf1, pages_dir, dpi=150) if not list(pages_dir.glob("*.png")) else sorted(pages_dir.glob("*.png"))
    fig_index = figure_indexer.build_index(pdf1)

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
            figure_cropper.crop_visual(pdf1, fig_index[ref], ref, out_png)
        crops[ref] = out_png

    cover = AUDIO_DIR / shorts_slug / "cover.png"
    title_card.render_cover(cover)
    tc = crops_dir / "__TITLE__.png"
    teaser = crops_dir / "teaser.png"
    title_card.render_title_card(intro_text, tc, size=SHORTS_RESOLUTION,
                                 teaser_path=teaser if teaser.exists() else None)
    crops["__TITLE__"] = tc

    line_is_cover = [figure_cropper.normalize_ref(l.get("visual_ref")) not in crops for l in data["script"]]
    ass = AUDIO_DIR / shorts_slug / f"{shorts_slug}.ass"
    subtitle.build_ass(data["script"], wavs, ass, line_is_cover=line_is_cover)
    segments = composer.build_segments_v2(data["script"], wavs, pages, fig_index, crops, fallback_img=cover)

    header_png = crops_dir / "__HEADER__.png"
    title_card.render_header_strip(intro_text, header_png, width=SHORTS_RESOLUTION[0])

    out_mp4 = VIDEOS_DIR / f"{shorts_slug}.mp4"
    composer.compose_shorts(mp3, ass, pages, segments, out_mp4, header_png=header_png)
    print(f"  mp4: {out_mp4}", flush=True)


if __name__ == "__main__":
    main()
