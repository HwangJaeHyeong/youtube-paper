"""Generate conversational podcast scripts from paper text.

Uses the configured Claude or Codex provider through src.llm.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone

from src.config import SCRIPTS_DIR
from src.llm import generate_text
from src.script.prompts import SYSTEM_PROMPT, user_prompt
from src.script.validator import validate_script

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def _strip_code_fences(s: str) -> str:
    return _FENCE_RE.sub("", s).strip()


async def _query_claude(prompt: str) -> str:
    return await generate_text(SYSTEM_PROMPT, prompt)


_ALLOWED_SECTIONS = {
    "intro", "background", "method", "results", "backstory", "limitations", "rating", "outro"
}


def _sanitize_sections(lines: list[dict]) -> None:
    """Replace unknown section tags with the previous valid section (in-place)."""
    last_valid = "intro"
    for line in lines:
        if line.get("section") in _ALLOWED_SECTIONS:
            last_valid = line["section"]
        else:
            line["section"] = last_valid


def generate(
    paper_title: str,
    authors: list[str],
    venue: str,
    paper_text: str,
    paper_id: str,
    save: bool = True,
) -> dict:
    prompt = user_prompt(paper_title, authors, venue, paper_text)
    raw = asyncio.run(_query_claude(prompt))
    data = json.loads(_strip_code_fences(raw))
    data.setdefault("paper_id", paper_id)
    data.setdefault("metadata", {})["generated_at"] = datetime.now(timezone.utc).isoformat()
    _sanitize_sections(data.get("script", []))

    if save:
        out = SCRIPTS_DIR / f"{paper_id}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        validate_script(data)
    except Exception as e:
        print(f"[WARN] Script validation failed (raw saved anyway): {e}")
    return data
