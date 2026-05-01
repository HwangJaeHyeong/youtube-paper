"""Anime-review shorts script generator.

Reuses the Claude Agent SDK + OAuth path from the paper pipeline.
Output schema mirrors `src.script.validator.Script` so downstream tooling
(subtitle, composer, upload) works unchanged — with one addition:
each line has an `image_prompt` used by `image_gen` to render per-scene AI art.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from src.config import CLAUDE_MODEL, SCRIPTS_DIR
from src.script.shorts_generator import _parse_first_json

ANIME_SHORTS_SYSTEM = """\
민재(남)와 수빈(여)이 진행하는 **25~35초** 유튜브 쇼츠 **애니메이션 리뷰** 대본.
NotebookLM 오디오 오버뷰 수준 심층 대화 + 솔직 까기 + 씹재밌게.

[제목·태그 — 클릭률 직결]
- `title_hook`: 한국어 후킹 제목. "후킹 문구 (작품 약칭)". 40자 이내.
  · 예: "심리학 논문 8천개가 인용한 애니 (에바)", "감독이 우울증 때문에 엔딩 날린 전설 (에바)"
- `primary_tag`: 작품 약칭 (공백·특수문자 없음). 예: "에바", "원피스", "바케모노".

[콜드 오픈 — 인트로 금지]
- 첫 줄 = 충격 팩트 or 반직관 질문. "안녕/오늘은/이 애니는" 금지.

[리텐션]
- 5~7초마다 새 호기심/페이오프. 15초 지점 두 번째 파동 필수 ("근데 더 놀라운 건").
- 한 편 = 한 통찰. 팩트 나열 금지.

[두 호스트 — 케미]
- 민재: 팩트·연출·업계 관점. 건조하지만 포인트 날카로움.
- 수빈: 감정·의문·비판·농담. 매 턴 최소 1회 의문/비유.

[일반인 눈높이]
- 전문 용어·업계 용어 등장 즉시 한줄 풀이.
- 추상어 ("명작", "혁신적") 금지. "1995년, 한 TV 애니가 심리학 저널 8천건 인용" 식 구체.

[사실 정확성 — 엄수]
- 공식 방영년도·제작사·감독·화수·수상 같은 검증 가능 정보만.
- 모호하면 "정확한 수치는 찾아보자" 식 얼버무리기. 없는 숫자 만들지 말 것.
- 감독·제작진 **사생활 추측 금지** — 본인이 공개 인터뷰·공식 성명에서 말한 일화만.

[이미지 프롬프트 — 각 라인 image_prompt 필수]
- 라인 내용을 시각화할 AI 그림 프롬프트 (영어). 2~3 문장.
- 애니 스타일·구도·색감 포함. 예: "anime style, rainy neon-lit Tokyo street, lone teenage pilot from behind, melancholic blue tones, cinematic composition".
- **저작권 캐릭터·로고 이름 금지**. "Shinji" X → "teenage boy in purple and green plugsuit, helmet off, lost expression" O.
- 인트로 라인은 image_prompt null (타이틀 카드가 들어감).

[출력 — JSON 한 덩어리, 코드펜스 없이]
스키마: {paper_id, paper_title, title_hook, primary_tag, authors, venue, metadata, script[], rating}
- paper_id: slug, paper_title: 공식 작품명 (한글/영문 자유)
- authors: [감독명]
- venue: 제작사 (예: "Gainax / 1995 TV")
- metadata.target_length="shorts", estimated_duration_sec=25~35
- script[]: 8~12줄. 필드:
  · section ∈ intro|background|method|results|backstory|limitations|rating|outro
    (애니에선 method=연출/각본, results=반응/영향, backstory=제작비화, limitations=까기)
  · speaker ∈ 민재|수빈
  · emotion ∈ neutral|skeptical|excited|dry|amused
  · text, pause_after_ms
  · image_prompt: 영어 이미지 생성 프롬프트 (인트로는 null)
- rating: {민재: 0~5, 수빈: 0~5, verdict: 한 줄}
"""


def _build_prompt(name: str, extra_info: str = "") -> str:
    info = f"\n[추가 정보]\n{extra_info}" if extra_info else ""
    return (
        f"아래 애니메이션으로 25~35초 쇼츠 리뷰 대본을 JSON 으로 작성하세요. "
        f"라인마다 image_prompt 필수. 콜드 오픈.\n\n"
        f"작품: {name}{info}"
    )


async def _query(prompt: str) -> str:
    options = ClaudeAgentOptions(
        system_prompt=ANIME_SHORTS_SYSTEM, model=CLAUDE_MODEL, allowed_tools=[],
    )
    chunks: list[str] = []
    async for m in query(prompt=prompt, options=options):
        if isinstance(m, AssistantMessage):
            for b in m.content:
                if isinstance(b, TextBlock):
                    chunks.append(b.text)
    return "".join(chunks)


def generate(name: str, slug: str, extra_info: str = "") -> dict:
    raw = asyncio.run(_query(_build_prompt(name, extra_info)))
    data = _parse_first_json(raw)
    data.setdefault("paper_id", f"{slug}-shorts")
    data.setdefault("metadata", {})
    data["metadata"]["target_length"] = "shorts"
    data["metadata"]["content_type"] = "anime"
    data["metadata"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    out = SCRIPTS_DIR / f"{slug}-shorts.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
