"""arXiv API wrapper: search and download PDFs."""
from __future__ import annotations

from pathlib import Path

import arxiv

from src.config import PAPERS_DIR


def fetch_by_id(arxiv_id: str, dest_dir: Path = PAPERS_DIR) -> Path:
    """Download a single paper PDF by arXiv id. Returns the PDF path."""
    search = arxiv.Search(id_list=[arxiv_id])
    paper = next(arxiv.Client().results(search))
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{arxiv_id.replace('/', '_')}.pdf"
    pdf_path = paper.download_pdf(dirpath=str(dest_dir), filename=filename)
    return Path(pdf_path)


def search(query: str, max_results: int = 10) -> list[arxiv.Result]:
    return list(arxiv.Client().results(arxiv.Search(query=query, max_results=max_results)))
