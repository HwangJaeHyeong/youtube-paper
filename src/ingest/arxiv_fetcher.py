"""arXiv helpers: direct PDF download + metadata search.

Direct PDF download avoids the API query that gets 429-rate-limited
when running tests/examples back-to-back.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

import arxiv

from src.config import PAPERS_DIR

_PDF_URL = "https://arxiv.org/pdf/{id}"


def fetch_by_id(arxiv_id: str, dest_dir: Path = PAPERS_DIR) -> Path:
    """Download a single paper PDF by arXiv id. Returns the PDF path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{arxiv_id.replace('/', '_')}.pdf"
    dest = dest_dir / filename
    if not dest.exists():
        url = _PDF_URL.format(id=arxiv_id)
        req = urllib.request.Request(url, headers={"User-Agent": "papercast/0.1"})
        with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as f:
            f.write(r.read())
    return dest


def search(query: str, max_results: int = 10) -> list[arxiv.Result]:
    return list(arxiv.Client().results(arxiv.Search(query=query, max_results=max_results)))
