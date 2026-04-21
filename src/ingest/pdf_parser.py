"""Extract text and metadata from a paper PDF."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass
class PaperContent:
    title: str
    authors: list[str]
    text: str
    num_pages: int


def parse(pdf_path: Path) -> PaperContent:
    reader = PdfReader(str(pdf_path))
    meta = reader.metadata or {}
    title = (meta.get("/Title") or pdf_path.stem).strip()
    authors_raw = (meta.get("/Author") or "").strip()
    authors = [a.strip() for a in authors_raw.replace(";", ",").split(",") if a.strip()]
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    return PaperContent(title=title, authors=authors, text=text, num_pages=len(reader.pages))
