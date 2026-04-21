"""End-to-end orchestrator.

Commands:
    python -m src.pipeline run <arxiv_id>           # 롱폼 스크립트 + mp3
    python -m src.pipeline video <slug>             # 롱폼 mp4 (오디오+자막+페이지)
    python -m src.pipeline shorts <slug>            # 쇼츠: 스크립트 + mp3 + mp4
    python -m src.pipeline upload <slug> [--shorts] [--public]
    python -m src.pipeline all <arxiv_id>           # 위 전부
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from src import tts
from src.config import AUDIO_DIR, PAPERS_DIR, SCRIPTS_DIR, VIDEOS_DIR
from src.ingest import arxiv_fetcher, pdf_parser
from src.script import generator as script_gen
from src.script import shorts_generator
from src.video import audio_merger, composer, slide_maker, subtitle
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
    for i, line in enumerate(lines):
        wav = line_dir / f"{i:03d}_{line['speaker']}.wav"
        if not wav.exists():
            tts.synthesize(line["text"], line["speaker"], wav, emotion=line.get("emotion", "neutral"))
        wavs.append(wav)
        file_pairs.append((wav, int(line.get("pause_after_ms", 200))))
    merged = AUDIO_DIR / slug / f"{slug}.mp3"
    audio_merger.merge(file_pairs, merged)
    return merged, wavs, lines


def _generate_video(slug: str, script_json: Path, mp3: Path, is_shorts: bool) -> Path:
    data = json.loads(script_json.read_text(encoding="utf-8"))
    line_dir = AUDIO_DIR / slug / "lines"
    wavs = sorted(line_dir.glob("*.wav"))
    assert len(wavs) == len(data["script"]), f"wav count {len(wavs)} != lines {len(data['script'])}"

    srt = AUDIO_DIR / slug / f"{slug}.srt"
    subtitle.build_srt(data["script"], wavs, srt)

    paper_id = data.get("paper_id", slug).replace("-shorts", "")
    pdf_candidates = list(PAPERS_DIR.glob(f"*{paper_id.split('-')[0]}*.pdf")) or list(PAPERS_DIR.glob("*.pdf"))
    if not pdf_candidates:
        raise RuntimeError(f"No PDF found in {PAPERS_DIR} to use as slide background")
    pdf = pdf_candidates[0]

    pages_dir = AUDIO_DIR / slug / "pages"
    pages = slide_maker.render_pages(pdf, pages_dir, dpi=150) if not list(pages_dir.glob("*.png")) else sorted(pages_dir.glob("*.png"))
    bg = pages[0]

    out_mp4 = VIDEOS_DIR / f"{slug}.mp4"
    if is_shorts:
        composer.compose_shorts(mp3, srt, bg, out_mp4)
    else:
        composer.compose_longform(mp3, srt, bg, out_mp4)
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
    """롱폼 mp4 만들기 (스크립트 JSON + mp3 이미 있어야 함)."""
    script_json = SCRIPTS_DIR / f"{slug}.json"
    mp3 = AUDIO_DIR / slug / f"{slug}.mp3"
    out = _generate_video(slug, script_json, mp3, is_shorts=False)
    typer.echo(json.dumps({"mp4": str(out)}))


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


@app.command()
def upload(
    slug: str,
    privacy: str = typer.Option("private", help="private | unlisted | public"),
    shorts: bool = typer.Option(False, "--shorts", help="Mark as YouTube Shorts"),
) -> None:
    """생성된 mp4 를 YouTube 에 업로드."""
    mp4 = VIDEOS_DIR / f"{slug}.mp4"
    script_json = SCRIPTS_DIR / f"{slug.replace('-shorts', '')}.json"
    if script_json.exists():
        data = json.loads(script_json.read_text(encoding="utf-8"))
        paper_title = data.get("paper_title", slug)
        verdict = data.get("rating", {}).get("verdict", "")
    else:
        paper_title, verdict = slug, ""
    prefix = "[Shorts] " if shorts else ""
    title = f"{prefix}{paper_title}"
    description = f"민재 X 수빈의 논문 까기 — {paper_title}\n\n한줄평: {verdict}\n\nGenerated by PaperCast."
    tags = ["논문리뷰", "AI", "HCI", paper_title.split()[0] if paper_title else "papercast"]
    video_id = yt_upload.upload(mp4, title, description, tags, privacy_status=privacy, is_shorts=shorts)
    typer.echo(json.dumps({"video_id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}"}))


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
