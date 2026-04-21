"""End-to-end orchestrator.

Phase 1: arXiv fetch -> Claude script -> Gemini TTS -> merged mp3 (audio-only mp4).
Later phases add slides, subtitles, shorts, and YouTube upload.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from src.config import AUDIO_DIR, PAPERS_DIR, SCRIPTS_DIR, VIDEOS_DIR
from src.ingest import arxiv_fetcher, pdf_parser
from src.script import generator as script_gen
from src.tts.gemini import GeminiTTS
from src.video import audio_merger

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("papercast")

app = typer.Typer(add_completion=False, help="PaperCast CLI")


@app.command()
def run(
    arxiv_id: str = typer.Argument(..., help="arXiv ID, e.g. 2406.09094"),
    paper_slug: str = typer.Option(None, help="Short id used for filenames"),
    venue: str = typer.Option("arXiv", help="Venue label for the script"),
) -> None:
    slug = paper_slug or arxiv_id.replace("/", "_")

    log.info("1/4 arXiv 다운로드: %s", arxiv_id)
    pdf_path = arxiv_fetcher.fetch_by_id(arxiv_id, dest_dir=PAPERS_DIR)

    log.info("2/4 PDF 파싱")
    paper = pdf_parser.parse(pdf_path)

    log.info("3/4 Claude 스크립트 생성")
    script = script_gen.generate(
        paper_title=paper.title,
        authors=paper.authors,
        venue=venue,
        paper_text=paper.text,
        paper_id=slug,
    )

    log.info("4/4 Gemini TTS 합성 (%d 라인)", len(script["script"]))
    tts = GeminiTTS()
    line_dir = AUDIO_DIR / slug / "lines"
    line_files: list[tuple[Path, int]] = []
    for i, line in enumerate(script["script"]):
        out = line_dir / f"{i:03d}_{line['speaker']}.wav"
        tts.synthesize(line["text"], line["speaker"], out)
        line_files.append((out, int(line.get("pause_after_ms", 0))))

    merged_mp3 = AUDIO_DIR / slug / f"{slug}.mp3"
    audio_merger.merge(line_files, merged_mp3)

    log.info("완료: %s", merged_mp3)
    typer.echo(json.dumps({"script": str(SCRIPTS_DIR / f"{slug}.json"), "audio": str(merged_mp3)}))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
