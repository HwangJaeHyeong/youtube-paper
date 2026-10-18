"""End-to-end orchestrator.

Commands:
    python -m src.pipeline run <arxiv_id>           # 롱폼 스크립트 + mp3
    python -m src.pipeline video <slug>             # 롱폼 mp4 (오디오+자막+페이지)
    python -m src.pipeline shorts <slug>            # 쇼츠: 스크립트 + mp3 + mp4
    python -m src.pipeline upload <slug> [--shorts] [--public]
    python -m src.pipeline all <arxiv_id>           # 위 전부
    python -m src.pipeline inbox                    # input/*.pdf -> output/*.mp4 (docker compose up)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import urllib.request
from pathlib import Path

import typer

from src import tts
from src.config import AUDIO_DIR, PAPERS_DIR, SCRIPTS_DIR, VIDEOS_DIR
from src.ingest import arxiv_fetcher, pdf_parser
from src.script import generator as script_gen
from src.script import shorts_generator
from src.video import audio_merger, composer, figure_cropper, figure_indexer, slide_maker, subtitle, title_card
from src.upload import youtube as yt_upload

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("papercast")

app = typer.Typer(add_completion=False, help="PaperCast CLI")


def _run_tts_and_merge(script: dict, slug: str) -> tuple[Path, list[Path], list[dict]]:
    line_dir = AUDIO_DIR / slug / "lines"
    line_dir.mkdir(parents=True, exist_ok=True)
    lines = script["script"]
    wavs: list[Path] = []
    file_pairs: list[tuple[Path, int]] = []
    paths = [line_dir / f"{i:03d}_{line['speaker']}.wav" for i, line in enumerate(lines)]
    # Synthesize all missing lines up front so batched providers (Qwen) can fill the GPU.
    tts.synthesize_many([
        (line["text"], line["speaker"], wav, line.get("emotion", "neutral"))
        for line, wav in zip(lines, paths)
        if not wav.exists() and line.get("visual_ref") != "__TITLE__"
    ])
    for line, wav in zip(lines, paths):
        if not wav.exists():
            # Title-card line is shown silently for 2 seconds (no TTS).
            from pydub import AudioSegment as _AS
            _AS.silent(duration=1000).export(str(wav), format="wav")
        wavs.append(wav)
        file_pairs.append((wav, int(line.get("pause_after_ms", 200))))
    merged = AUDIO_DIR / slug / f"{slug}.mp3"
    audio_merger.merge(file_pairs, merged)
    return merged, wavs, lines


def _generate_video(slug: str, script_json: Path, mp3: Path, is_shorts: bool, subtitle_style: str = "default", sticky_visuals: bool = False) -> Path:
    data = json.loads(script_json.read_text(encoding="utf-8"))
    line_dir = AUDIO_DIR / slug / "lines"
    wavs = sorted(line_dir.glob("*.wav"))
    assert len(wavs) == len(data["script"]), f"wav count {len(wavs)} != lines {len(data['script'])}"

    # Use the slug (which == arxiv_id in most cases) to find the PDF, NOT Claude's paper_id
    # (Claude sometimes writes things like "word2vec-arxiv1301" which won't match the file).
    base = slug.replace("-shorts", "")
    candidates = [
        PAPERS_DIR / f"{base}.pdf",
        *PAPERS_DIR.glob(f"{base}*.pdf"),
        *PAPERS_DIR.glob(f"*{base}*.pdf"),
    ]
    pdf_candidates = [p for p in candidates if p.exists()]
    if not pdf_candidates:
        raise RuntimeError(f"No PDF found in {PAPERS_DIR} matching slug={base!r}")
    pdf = pdf_candidates[0]

    pages_dir = AUDIO_DIR / slug / "pages"
    pages = slide_maker.render_pages(pdf, pages_dir, dpi=150) if not list(pages_dir.glob("*.png")) else sorted(pages_dir.glob("*.png"))

    fig_index = figure_indexer.build_index(pdf)
    log.info("figure index: %s", fig_index)

    # Render cropped Figure/Table images for any visual_ref that shows up in the script.
    crops_dir = AUDIO_DIR / slug / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    crops: dict[str, Path] = {}  # normalized ref -> crop PNG
    for line in data["script"]:
        ref = figure_cropper.normalize_ref(line.get("visual_ref"))
        if not ref or ref in crops:
            continue
        out_png = crops_dir / f"{ref.replace(' ', '_')}.png"
        # Path A: pre-existing PNG (PDF-cropped before, OR external image dropped
        # in by the user / generated for refs like "RNN", "CNN", "LLM_logos").
        if out_png.exists():
            crops[ref] = out_png
            continue
        # Path B: PDF-driven crop. Need page index from the figure_index.
        page_idx = fig_index.get(ref)
        if not page_idx:
            continue
        figure_cropper.crop_visual(pdf, page_idx, ref, out_png)
        crops[ref] = out_png
    log.info("crops rendered: %d (%s)", len(crops), list(crops.keys()))

    # Per-line flag: is this line shown over the plain cover (no figure)?
    # Subtitles get centered on cover lines so they don't float uselessly at the bottom.
    line_is_cover = [
        figure_cropper.normalize_ref(l.get("visual_ref")) not in crops
        for l in data["script"]
    ]

    ass = AUDIO_DIR / slug / f"{slug}.ass"
    subtitle.build_ass(data["script"], wavs, ass, line_is_cover=line_is_cover, style=subtitle_style)

    cover = AUDIO_DIR / slug / "cover.png"
    title_card.render_cover(cover)
    from src.config import SHORTS_RESOLUTION, LONGFORM_RESOLUTION
    size = SHORTS_RESOLUTION if is_shorts else LONGFORM_RESOLUTION
    intro_line = next((l for l in data["script"] if l.get("visual_ref") == "__TITLE__"), None)
    intro_title = (intro_line["text"] if intro_line else None) or data.get("title_hook") or data.get("paper_title", "")
    if intro_line is not None:
        tc = crops_dir / "__TITLE__.png"
        teaser = crops_dir / "teaser.png"
        title_card.render_title_card(intro_title, tc, size=size, teaser_path=teaser if teaser.exists() else None)
        crops["__TITLE__"] = tc
    segments = composer.build_segments_v2(
        data["script"], wavs, pages, fig_index, crops, fallback_img=cover, sticky=sticky_visuals
    )
    log.info("video segments: %d (fallback=%s)", len(segments), cover.name)

    out_mp4 = VIDEOS_DIR / f"{slug}.mp4"
    if is_shorts:
        header_png = crops_dir / "__HEADER__.png"
        title_card.render_header_strip(intro_title, header_png, width=size[0])
        composer.compose_shorts(
            mp3, ass, pages, segments, out_mp4,
            header_png=header_png,
        )
    else:
        composer.compose_longform(mp3, ass, pages, segments, out_mp4)
    return out_mp4


# ---------- commands ----------

@app.command()
def run(
    arxiv_id: str = typer.Argument(..., help="arXiv ID, e.g. 1706.03762"),
    paper_slug: str = typer.Option(None, help="Filename slug"),
    venue: str = typer.Option("arXiv", help="Venue label"),
) -> None:
    """arXiv PDF -> Claude 롱폼 스크립트 -> CLOVA TTS -> merged mp3."""
    slug = paper_slug or arxiv_id.replace("/", "_")
    log.info("1/3 arXiv: %s", arxiv_id)
    pdf = arxiv_fetcher.fetch_by_id(arxiv_id, dest_dir=PAPERS_DIR)
    paper = pdf_parser.parse(pdf)

    log.info("2/3 Claude script")
    script = script_gen.generate(
        paper_title=paper.title or arxiv_id,
        authors=paper.authors,
        venue=venue,
        paper_text=paper.text,
        paper_id=slug,
    )

    log.info("3/3 TTS %d lines", len(script["script"]))
    mp3, _, _ = _run_tts_and_merge(script, slug)
    typer.echo(json.dumps({"slug": slug, "script": str(SCRIPTS_DIR / f"{slug}.json"), "mp3": str(mp3)}))


@app.command()
def video(slug: str) -> None:
    """롱폼/쇼츠 mp4 만들기. 형식은 스크립트의 metadata.target_length 로 자동 판별."""
    script_json = SCRIPTS_DIR / f"{slug}.json"
    mp3 = AUDIO_DIR / slug / f"{slug}.mp3"
    data = json.loads(script_json.read_text(encoding="utf-8"))
    is_shorts = data.get("metadata", {}).get("target_length") == "shorts" or slug.endswith("-shorts")
    out = _generate_video(slug, script_json, mp3, is_shorts=is_shorts)
    typer.echo(json.dumps({"mp4": str(out), "orientation": "shorts" if is_shorts else "longform"}))


@app.command()
def shorts(slug: str) -> None:
    """롱폼 slug 로부터 쇼츠 스크립트 생성 -> TTS -> 세로 mp4."""
    log.info("쇼츠 스크립트 생성 (from longform: %s)", slug)
    shorts_data = shorts_generator.generate_from_longform(slug)
    shorts_slug = f"{slug}-shorts"

    log.info("쇼츠 TTS %d lines", len(shorts_data["script"]))
    mp3, _, _ = _run_tts_and_merge(shorts_data, shorts_slug)

    log.info("쇼츠 영상 조립")
    script_json = SCRIPTS_DIR / f"{shorts_slug}.json"
    out = _generate_video(shorts_slug, script_json, mp3, is_shorts=True)
    typer.echo(json.dumps({"shorts_slug": shorts_slug, "mp4": str(out)}))


@app.command("shorts-only")
def shorts_only(
    arxiv_id: str = typer.Argument(...),
    paper_slug: str = typer.Option(None),
    venue: str = typer.Option("arXiv"),
    official_url: str = typer.Option("", help="공식 논문 링크 (ACM/IEEE/proceedings DOI). 설명에 삽입됨."),
    lang: str = typer.Option("ko", help="ko | en"),
) -> None:
    """롱폼 없이 arxiv_id 에서 바로 쇼츠 생성 (스크립트 + TTS + mp4)."""
    base_slug = paper_slug or arxiv_id.replace("/", "_")
    if lang == "en":
        base_slug = f"{base_slug}-en"
    log.info("1/4 arXiv 다운: %s", arxiv_id)
    pdf = arxiv_fetcher.fetch_by_id(arxiv_id, dest_dir=PAPERS_DIR, slug=base_slug)
    out = _shorts_from_pdf(pdf, base_slug, venue, official_url, lang)
    typer.echo(json.dumps({"shorts_slug": f"{base_slug}-shorts", "mp4": str(out)}))


def _shorts_from_pdf(pdf: Path, base_slug: str, venue: str, official_url: str = "", lang: str = "ko") -> Path:
    """PDF (in PAPERS_DIR, named after base_slug) -> shorts script + TTS + mp4."""
    paper = pdf_parser.parse(pdf)

    shorts_slug = f"{base_slug}-shorts"
    cached_script = SCRIPTS_DIR / f"{shorts_slug}.json"
    if cached_script.exists():
        log.info("2/4 기존 쇼츠 스크립트 재사용: %s", cached_script.name)
        shorts_data = json.loads(cached_script.read_text(encoding="utf-8"))
    else:
        log.info("2/4 쇼츠 스크립트 (self-critique 5회 반복)")
        shorts_data = shorts_generator.generate_from_paper_iterative(
            paper_title=paper.title or base_slug,
            authors=paper.authors,
            venue=venue,
            paper_text=paper.text,
            slug=base_slug,
            rounds=1,
            lang=lang,
        )
        shorts_data.setdefault("metadata", {})["lang"] = lang
    # Inject official_url into metadata if given via CLI so upload step sees it.
    if official_url:
        shorts_data.setdefault("metadata", {})["official_url"] = official_url
    # Prepend title-intro line (centered title card + host reads title).
    lines_ = shorts_data.get("script", [])
    # If a stale intro line exists, drop it so we can reinject with latest title_hook.
    if lines_ and lines_[0].get("visual_ref") == "__TITLE__":
        lines_.pop(0)
    if lines_:
        host = lines_[0].get("speaker", "민재")
        intro_text = shorts_data.get("title_hook") or shorts_data.get("paper_title", "")
        intro_line = {
            "section": "intro",
            "speaker": host,
            "text": intro_text,
            "emotion": "neutral",
            "pause_after_ms": 400,
            "visual_ref": "__TITLE__",
            "skip_subtitle": True,
        }
        shorts_data["script"].insert(0, intro_line)
    cached_script.write_text(json.dumps(shorts_data, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("3/4 쇼츠 TTS %d lines", len(shorts_data["script"]))
    mp3, _, _ = _run_tts_and_merge(shorts_data, shorts_slug)

    log.info("4/4 쇼츠 영상 조립")
    script_json = SCRIPTS_DIR / f"{shorts_slug}.json"
    return _generate_video(shorts_slug, script_json, mp3, is_shorts=True)


@app.command()
def inbox(
    in_dir: Path = typer.Option(Path("input"), help="처리할 PDF 폴더"),
    out_dir: Path = typer.Option(Path("output"), help="완성 mp4 폴더"),
    venue: str = typer.Option("", help="학회 표기 (모든 PDF 공통)"),
) -> None:
    """input/*.pdf -> 쇼츠 mp4 를 output/ 에 (+ YOUTUBE_UPLOAD 설정 시 업로드), 끝난 PDF 는 input/finished/ 로. 실패한 PDF 는 그대로 둠."""
    done = in_dir / "finished"
    done.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(in_dir.glob("*.pdf"))
    log.info("inbox: %d PDF", len(pdfs))
    try:
        failed = _process_inbox(pdfs, done, out_dir, venue)
    finally:
        if os.getenv("QWEN_TTS_SHUTDOWN_AFTER"):  # docker compose: stop the GPU server too
            from src.config import QWEN_TTS_URL
            try:
                urllib.request.urlopen(urllib.request.Request(QWEN_TTS_URL.replace("/tts", "/shutdown"), b""), timeout=10)
            except OSError:
                pass
    if failed:
        raise typer.Exit(1)


def _process_inbox(pdfs: list[Path], done: Path, out_dir: Path, venue: str) -> int:
    failed = 0
    for pdf in pdfs:
        # Slug must be ASCII-safe (file globbing); hash keeps Korean-named PDFs unique.
        ascii_part = re.sub(r"[^a-z0-9]+", "-", pdf.stem.lower()).strip("-")[:40]
        slug = f"{ascii_part or 'paper'}-{hashlib.sha1(pdf.name.encode()).hexdigest()[:6]}"
        try:
            shutil.copy2(pdf, PAPERS_DIR / f"{slug}.pdf")
            mp4 = _shorts_from_pdf(PAPERS_DIR / f"{slug}.pdf", slug, venue)
            shutil.copy2(mp4, out_dir / f"{pdf.stem}.mp4")
            # YOUTUBE_UPLOAD=private|unlisted|public uploads as Shorts; empty = skip.
            # Marker file prevents re-uploading when the same PDF is processed again.
            uploaded = VIDEOS_DIR / f"{slug}-shorts.youtube"
            if (privacy := os.getenv("YOUTUBE_UPLOAD", "")) and not uploaded.exists():
                uploaded.write_text(upload(f"{slug}-shorts", privacy=privacy, shorts=True, channel="", publish_at=""))
            elif uploaded.exists():
                log.info("already uploaded: https://www.youtube.com/watch?v=%s (skip)", uploaded.read_text().strip())
            shutil.move(str(pdf), str(done / pdf.name))
            log.info("done: %s -> %s", pdf.name, out_dir / f"{pdf.stem}.mp4")
        except Exception:
            failed += 1
            log.exception("failed: %s (left in %s)", pdf.name, pdf.parent)
    return failed


@app.command("anime-shorts")
def anime_shorts(
    name: str = typer.Argument(..., help="애니메이션 작품명 (한글/영문)."),
    paper_slug: str = typer.Option(None, help="slug; 기본 = name을 소문자·언더스코어 변환."),
    extra_info: str = typer.Option("", help="Claude 에게 추가로 줄 정보 (방영년도·감독 등)."),
    official_url: str = typer.Option("", help="공식 링크 (AniList/MAL) — 설명란에 포함."),
) -> None:
    """애니메이션 이름 → 스크립트 → AI 이미지 → TTS → 쇼츠 mp4."""
    from src.anime import script_gen as anime_script_gen
    from src.anime import image_gen as anime_image_gen

    import re as _re
    slug = paper_slug or _re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    shorts_slug = f"{slug}-shorts"
    script_json = SCRIPTS_DIR / f"{shorts_slug}.json"
    if script_json.exists():
        log.info("1/4 기존 스크립트 재사용: %s", script_json.name)
        data = json.loads(script_json.read_text(encoding="utf-8"))
    else:
        log.info("1/4 Claude 스크립트: %s", name)
        data = anime_script_gen.generate(name, slug, extra_info)

    if official_url:
        data.setdefault("metadata", {})["official_url"] = official_url

    # Anime: skip the title-intro line (첫 화면 = 첫 장면 이미지). 기존 __TITLE__ 라인이 있으면 제거.
    lines_ = data.get("script", [])
    if lines_ and lines_[0].get("visual_ref") == "__TITLE__":
        lines_.pop(0)
    # Assign scene_{i} visual_ref for lines that have image_prompt.
    for i, ln in enumerate(data["script"]):
        if ln.get("image_prompt"):
            ln["visual_ref"] = f"scene_{i}"
    script_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("2/4 TTS %d lines", len(data["script"]))
    mp3, wavs, lines = _run_tts_and_merge(data, shorts_slug)

    log.info("3/4 Nano Banana 이미지 생성")
    scenes_dir = AUDIO_DIR / shorts_slug / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    crops: dict[str, Path] = {}
    for i, ln in enumerate(data["script"]):
        ref = ln.get("visual_ref")
        if not ref or not ref.startswith("scene_"):
            continue
        out_png = scenes_dir / f"{ref}.png"
        if not out_png.exists():
            try:
                anime_image_gen.generate(ln["image_prompt"], out_png)
            except Exception as e:
                log.warning("이미지 실패 (%s): %s — fallback to cover", ref, e)
                continue
        crops[ref] = out_png

    log.info("4/4 영상 조립")
    from src.config import SHORTS_RESOLUTION
    wavs = sorted((AUDIO_DIR / shorts_slug / "lines").glob("*.wav"))
    cover = AUDIO_DIR / shorts_slug / "cover.png"
    title_card.render_cover(cover)

    line_is_cover = [
        (ln.get("visual_ref") not in crops)
        for ln in data["script"]
    ]
    ass = AUDIO_DIR / shorts_slug / f"{shorts_slug}.ass"
    subtitle.build_ass(data["script"], wavs, ass, line_is_cover=line_is_cover)

    segments = composer.build_segments_v2(
        data["script"], wavs, pages=[cover], figure_index={}, crops=crops, fallback_img=cover,
    )
    log.info("segments: %d, scenes: %d", len(segments), len([k for k in crops if k.startswith('scene_')]))
    out_mp4 = VIDEOS_DIR / f"{shorts_slug}.mp4"
    composer.compose_shorts(mp3, ass, [cover], segments, out_mp4)
    typer.echo(json.dumps({"shorts_slug": shorts_slug, "mp4": str(out_mp4)}))


@app.command()
def upload(
    slug: str,
    privacy: str = typer.Option("private", help="private | unlisted | public"),
    shorts: bool = typer.Option(False, "--shorts", help="Mark as YouTube Shorts"),
    channel: str = typer.Option("", help="채널 별칭 (token file 접미사). 비우면 기본 채널."),
    publish_at: str = typer.Option("", help="RFC3339 예약 시각 (예: 2026-04-22T19:00:00+09:00)."),
) -> str:
    """생성된 mp4 를 YouTube 에 업로드. Returns video id."""
    mp4 = VIDEOS_DIR / f"{slug}.mp4"
    # Prefer the slug-exact JSON (e.g. "<slug>-shorts.json"); fall back to stripped variant.
    script_json = SCRIPTS_DIR / f"{slug}.json"
    if not script_json.exists():
        script_json = SCRIPTS_DIR / f"{slug.replace('-shorts', '')}.json"
    if script_json.exists():
        data = json.loads(script_json.read_text(encoding="utf-8"))
        paper_title = data.get("paper_title", slug)
        verdict = data.get("rating", {}).get("verdict", "")
        official_url = data.get("metadata", {}).get("official_url", "") or ""
        lang = data.get("metadata", {}).get("lang", "ko")
        title_hook = data.get("title_hook", "") or ""
        primary_tag_raw = data.get("primary_tag", "") or ""
        content_type = data.get("metadata", {}).get("content_type", "")
        if not content_type:
            # Detect by heuristic: anime scripts carry image_prompt per line.
            if any(l.get("image_prompt") for l in data.get("script", [])):
                content_type = "anime"
            else:
                content_type = "paper"
    else:
        paper_title, verdict, official_url, lang = slug, "", "", "ko"
        title_hook, primary_tag_raw, content_type = "", "", "paper"
    import re as _re
    title = title_hook if title_hook else paper_title
    primary_tag = _re.sub(r"[^\w가-힣]", "", primary_tag_raw) if primary_tag_raw \
        else _re.sub(r"[^\w가-힣]", "", (paper_title.split()[0] if paper_title else "PaperCast"))
    if lang == "en":
        hashtag_line = f"#PaperReview #AI #DeepLearning #MachineLearning #Research #{primary_tag}"
        if shorts:
            hashtag_line += " #Shorts"
        official_line = f"📄 Paper: {official_url}\n\n" if official_url else ""
        description = (
            f"{paper_title}\n\n"
            f"Takeaway: {verdict}\n\n"
            f"{official_line}"
            f"{hashtag_line}\n\n"
            ""
        )
        tags = [
            "PaperReview", "AI", "DeepLearning", "MachineLearning",
            "Research", "Paper", "arxiv", primary_tag,
        ]
    elif content_type == "anime":
        hashtag_line = f"#애니리뷰 #애니추천 #일본애니 #애니메이션 #{primary_tag}"
        if shorts:
            hashtag_line += " #Shorts"
        official_line = f"🎬 작품 정보: {official_url}\n\n" if official_url else ""
        description = (
            f"{paper_title}\n\n"
            f"한줄평: {verdict}\n\n"
            f"{official_line}"
            f"{hashtag_line}\n\n"
            ""
        )
        tags = [
            "애니리뷰", "애니추천", "애니메이션", "일본애니", "오타쿠",
            "anime", "animereview", "animerecommendation",
            primary_tag,
        ]
    else:
        hashtag_line = f"#논문리뷰 #AI #딥러닝 #인공지능 #논문 #{primary_tag}"
        if shorts:
            hashtag_line += " #Shorts"
        official_line = f"📄 논문 원문: {official_url}\n\n" if official_url else ""
        description = (
            f"{paper_title}\n\n"
            f"한줄평: {verdict}\n\n"
            f"{official_line}"
            f"{hashtag_line}\n\n"
            ""
        )
        tags = [
            "논문리뷰", "AI", "딥러닝", "머신러닝", "인공지능", "논문",
            "논문추천", "MachineLearning", "DeepLearning", "Research", "Paper",
            primary_tag,
        ]
    if shorts:
        tags.append("Shorts")
    video_id = yt_upload.upload(
        mp4, title, description, tags, privacy_status=privacy, is_shorts=shorts,
        channel=channel or None, publish_at=publish_at or None,
    )
    typer.echo(json.dumps({"video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}"}))
    return video_id


@app.command("all")
def all_cmd(
    arxiv_id: str,
    paper_slug: str = typer.Option(None),
    venue: str = typer.Option("arXiv"),
    upload_enabled: bool = typer.Option(False, "--upload"),
    privacy: str = typer.Option("private"),
) -> None:
    """arxiv_id -> 롱폼 mp3+mp4 + 쇼츠 mp4 (+선택적 업로드)."""
    slug = paper_slug or arxiv_id.replace("/", "_")
    run(arxiv_id, paper_slug=slug, venue=venue)
    video(slug)
    shorts(slug)
    if upload_enabled:
        upload(slug, privacy=privacy, shorts=False)
        upload(f"{slug}-shorts", privacy=privacy, shorts=True)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
