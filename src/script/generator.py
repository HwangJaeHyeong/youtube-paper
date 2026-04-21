"""Generate conversational podcast scripts from paper text.

Uses the Claude Agent SDK, which authenticates via the user's Claude Code
subscription (OAuth) by default — no ANTHROPIC_API_KEY needed for Phase 1~3.
Set ANTHROPIC_API_KEY in .env later if you want to switch to pay-per-token
for headless/cron deployments.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from src.config import CLAUDE_MODEL, SCRIPTS_DIR
from src.script.prompts import SYSTEM_PROMPT, user_prompt
from src.script.validator import validate_script

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def _strip_code_fences(s: str) -> str:
    return _FENCE_RE.sub("", s).strip()


async def _query_claude(prompt: str) -> str:
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=CLAUDE_MODEL,
        allowed_tools=[],
    )
    chunks: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
    return "".join(chunks)


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
    validate_script(data)
    if save:
        out = SCRIPTS_DIR / f"{paper_id}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
