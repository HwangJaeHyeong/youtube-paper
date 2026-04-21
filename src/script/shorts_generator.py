"""Take a longform script JSON and produce a 30~60 second Shorts version.

Uses Claude Agent SDK (same OAuth as longform). Output schema matches the
longform validator, just with fewer lines and metadata.target_length='shorts'.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from src.config import CLAUDE_MODEL, SCRIPTS_DIR
from src.script.generator import _sanitize_sections
from src.script.validator import validate_script

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)

SHORTS_SYSTEM = """\
당신은 유튜브 쇼츠용 한국어 대본 압축 작가입니다.
롱폼 팟캐스트 대본(JSON)을 입력받아 30~60초짜리 쇼츠 버전으로 압축해 새 JSON 으로 돌려주세요.

[호스트 유지]
- 민재 (남, 긍정적 설명조) / 수빈 (여, 까칠·발랄)
- 두 명 모두 반드시 등장. 한쪽만 나오면 재미 없음.

[쇼츠 원칙]
1. 첫 3초가 전부 — 강한 후크: 숫자·의문·반전·충격 중 하나. "안녕하세요" 금지.
2. 총 8~14줄, 전체 합쳐 200자 이내.
3. 논문 자체 설명 최소화. "이거 왜 재밌냐" / "그래서 뭐가 바뀌었냐" 포인트 딱 하나.
4. 마지막은 "롱폼 풀버전에서 더" 같은 가벼운 유도 멘트 or 별점.
5. 한 줄은 한 호흡(15자 이내), 쇼츠 템포로 빠르게.

[출력 형식]
오직 JSON 한 덩어리만. 마크다운 코드블록·앞뒤 설명 금지.
동일 스키마(paper_id, paper_title, metadata, script[], rating) 유지하되:
- metadata.target_length = "shorts"
- metadata.estimated_duration_sec = 30~60
- script[] 항목은 8~14개
- 각 항목 5개 필드 필수: section, speaker, text, emotion, pause_after_ms
- section 은 'intro|background|method|results|backstory|limitations|rating|outro' 중 하나
"""


def _build_prompt(longform: dict) -> str:
    return (
        "아래 롱폼 대본을 30~60초 쇼츠로 압축해서 JSON으로 돌려주세요.\n\n"
        f"[원본]\n{json.dumps(longform, ensure_ascii=False)}"
    )


async def _query(prompt: str) -> str:
    options = ClaudeAgentOptions(
        system_prompt=SHORTS_SYSTEM,
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


def _strip_fences(s: str) -> str:
    return _FENCE_RE.sub("", s).strip()


def generate_from_longform(longform_slug: str, save: bool = True) -> dict:
    """Read data/scripts/<slug>.json, produce <slug>-shorts.json."""
    src_path = SCRIPTS_DIR / f"{longform_slug}.json"
    longform = json.loads(src_path.read_text(encoding="utf-8"))

    raw = asyncio.run(_query(_build_prompt(longform)))
    data = json.loads(_strip_fences(raw))
    data.setdefault("paper_id", f"{longform_slug}-shorts")
    data.setdefault("metadata", {})
    data["metadata"]["target_length"] = "shorts"
    data["metadata"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    _sanitize_sections(data.get("script", []))

    if save:
        out = SCRIPTS_DIR / f"{longform_slug}-shorts.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        validate_script(data)
    except Exception as e:
        print(f"[WARN] Shorts validation failed (raw saved): {e}")
    return data
