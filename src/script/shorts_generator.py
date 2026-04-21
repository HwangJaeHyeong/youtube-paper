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
민재(남)와 수빈(여)이 진행하는 **NotebookLM 스타일 심층 대화 쇼츠** 대본을 JSON 으로.
목표: 60초짜리 유튜브 쇼츠인데, 60초 동안 "논문의 진짜 흥미로운 한 가지"를 깊이 파고든 느낌이 남도록.

[이 쇼츠의 성격 — 가장 중요]
당신은 지금 NotebookLM 오디오 오버뷰의 핫한 60초를 잘라낸다고 상상하세요.
- 두 호스트가 **정말로 논문을 재밌어 하면서** 서로 리액션하고 생각을 쌓아가는 대화.
- 한 명이 통찰을 던지면 다른 한 명이 "잠깐, 그럼 이거?" 하고 파고들어 가기.
- 한 편 = **한 깊은 통찰** 을 탐구. 여러 팩트 나열 금지.
- 끝나면 시청자가 "오, 그거 몰랐네" 하나 남아야 함.

[대화의 흐름 — 이 4단 구조로 가기]
① **후킹 (0~5초, 2~3줄)**
   - 반직관적 사실 / 놀라운 숫자 / 말 안 되는 상황 하나 제시.
   - 예: "이 논문, RNN 다 버리고 번역 1등 먹었어요." → "잠깐, 순환신경망 없이 번역이 되나?"
② **왜 그게 특이한지 (5~20초, 3~4줄)**
   - 이전 접근법의 한계 → 이 논문이 깬 상식.
   - 진짜 논문 Figure/Table 을 가리키며 얘기. visual_ref 정확히.
③ **어떻게 해낸 건지 깊이 파기 (20~45초, 4~5줄)**
   - 방법의 한 가지 핵심 트릭을 일상 비유로 설명.
   - 한 호스트가 "이게 왜 먹히는지" 질문 → 다른 호스트가 답.
   - "내 기준으론 이게 가장 영리한 부분" 같은 주관적 평가 OK.
④ **그래서 뭐가 바뀌었는지 (45~60초, 2~3줄)**
   - 이 논문 이후 세상이 어떻게 달라졌는지 (혹은 영향). 그리고 두 호스트 별점.

[대화 규칙]
- 서로 **이어받기**: "맞아, 그래서 ~" / "잠깐 그거 ~" / "그 말 듣고 보니 ~" 같이 상대 말에 반응.
- 한 명이 3턴 이상 독점 금지.
- 수빈은 **매 단계 1회 이상** 의문·반박·연결 질문.
- 모든 라인 한 호흡(13~20자).
- 빈 감탄사("와!" 단독, "음..." 등) 금지 — 감탄을 쓰려면 꼭 근거와 세트.

[날카로움 & 리텐션 — 넘기지 않게]
- 모든 라인 **한 번에 직관적 이해** 가능해야 함. 다시 들어야 알아듣는 문장은 버릴 것.
- 8~10초마다 새 **호기심 포인트** — "근데 이게 왜?" / "진짜?" 하게 만드는 미끼 심기.
- "수치 충격 → 즉시 풀이" 리듬. 숫자 던지고 바로 "이게 얼마나 빠른 거냐면 ~" 식.
- 추상어 금지. "효과적인 학습" 같은 말 대신 "일주일 걸리던 걸 하루에 끝냄" 처럼 구체적으로.
- 각 라인 끝이 다음 라인 궁금하게 만들도록 엮기.

[일반인 눈높이]
- 전문 용어 나오면 **같은 줄에 한글 풀이**.
- 비유 최소 2개, 일상 사물로. 예: "어텐션 = 단어끼리 서로 쳐다봄", "멀티헤드 = 8명이 같은 문장 각자 관점으로 읽기".
- 영어 약어는 한글 발음으로 말하기 ("비엘이유" 아니라 "블루 점수").

[출력]
JSON 한 덩어리만, 마크다운 없이.
스키마: {paper_id, paper_title, authors, venue, metadata, script[], rating}
- metadata.target_length="shorts", estimated_duration_sec=45~60
- script[]: 10~16 항목 (4단 구조 따르기)
- 라인 필드: section, speaker, text, emotion, pause_after_ms, visual_ref
  · section ∈ intro|background|method|results|backstory|limitations|rating|outro
  · emotion ∈ neutral|skeptical|excited|dry|amused
  · visual_ref: **정확히** "Figure N" 또는 "Table N" 문자열만. 설명·overlay·괄호 주석·★등 추가 금지. 참조 없으면 null.
"""


def _build_prompt_from_longform(longform: dict) -> str:
    return (
        "아래 롱폼 대본을 30~60초 쇼츠로 압축해서 JSON으로 돌려주세요.\n\n"
        f"[원본]\n{json.dumps(longform, ensure_ascii=False)}"
    )


def _build_prompt_from_paper(paper_title: str, authors: list[str], venue: str, paper_text: str) -> str:
    authors_str = ", ".join(authors) if authors else "미상"
    return (
        f"아래 논문으로 30~60초 쇼츠 대본을 JSON 으로 작성하세요. "
        f"Figure/Table 구체 인용 필수.\n\n"
        f"논문 제목: {paper_title}\n"
        f"저자: {authors_str}\n"
        f"발표지: {venue}\n\n"
        f"[논문 본문 (발췌)]\n{paper_text[:40000]}"
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


def _postprocess(data: dict, slug: str) -> dict:
    data.setdefault("paper_id", f"{slug}-shorts")
    data.setdefault("metadata", {})
    data["metadata"]["target_length"] = "shorts"
    data["metadata"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    _sanitize_sections(data.get("script", []))
    out = SCRIPTS_DIR / f"{slug}-shorts.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        validate_script(data)
    except Exception as e:
        print(f"[WARN] Shorts validation failed (raw saved): {e}")
    return data


def generate_from_longform(longform_slug: str) -> dict:
    src_path = SCRIPTS_DIR / f"{longform_slug}.json"
    longform = json.loads(src_path.read_text(encoding="utf-8"))
    raw = asyncio.run(_query(_build_prompt_from_longform(longform)))
    data = json.loads(_strip_fences(raw))
    return _postprocess(data, longform_slug)


def generate_from_paper(
    paper_title: str, authors: list[str], venue: str, paper_text: str, slug: str
) -> dict:
    raw = asyncio.run(_query(_build_prompt_from_paper(paper_title, authors, venue, paper_text)))
    data = json.loads(_strip_fences(raw))
    return _postprocess(data, slug)


# ---------- Self-critique + refine loop ----------

CRITIC_SYSTEM = """\
당신은 한국어 유튜브 쇼츠 대본 혹독한 비평가입니다. NotebookLM 오디오 오버뷰 급을 기준으로.

주어진 쇼츠 JSON 을 아래 10가지 항목으로 0~10점 채점하고, 반드시 구체 개선 지시도 주세요.

[체크리스트]
1. hooking: 첫 3초가 반직관적/충격적/흥미로운가? "안녕하세요" 같은 빈 인사 0점.
2. single_insight: 한 편이 여러 팩트 나열 대신 하나의 깊은 통찰을 파고드는가?
3. four_act_flow: 후킹→왜 특이→어떻게→그래서 뭐, 순서로 가는가?
4. turn_taking: 두 호스트가 서로 이어받고 반응하는가? 독백식이면 감점.
5. figure_refs: Figure/Table 최소 2회 구체 인용 + visual_ref 정확 기입?
6. analogies: 추상→일상 비유 2개 이상?
7. plain_language: 전문 용어 즉시 한글 풀이 + 영어 약어 한글 발음?
8. density: "와!", "음..." 같은 빈 감탄사/버리는 줄이 없는가?
9. subin_sharpness: 수빈이 매 단계 의문·반박·날카로운 질문 1회 이상?
10. payoff: 마무리에 "so what" 실질 여운 남는가 (별점 나열만이면 감점)?
11. intuitive: 각 라인이 **한 번에** 이해되는가? 다시 들어야 하는 복잡 문장 있으면 감점.
12. retention: 8~10초마다 호기심 포인트(다음 궁금하게 만드는 미끼)가 있는가? 중간 데드존 있으면 감점.
13. concreteness: 추상어("효과적", "혁신적") 대신 구체 수치/비유로 치환됐는가?

[출력 형식 — 오직 JSON 한 덩어리만, 코드펜스 없이]
{
  "scores": {"hooking":n, "single_insight":n, "four_act_flow":n, "turn_taking":n,
             "figure_refs":n, "analogies":n, "plain_language":n, "density":n,
             "subin_sharpness":n, "payoff":n, "intuitive":n, "retention":n,
             "concreteness":n},
  "total": 0~130,
  "critical_issues": ["가장 아픈 문제 3개"],
  "specific_fixes": ["라인 X 를 ~로 바꿔라" 식의 구체 지시 5~10개]
}
"""


REFINE_SYSTEM = """\
당신은 한국어 유튜브 쇼츠 대본 리파이너입니다.
원본 대본 JSON + 비평 JSON 을 받아서, 비평의 critical_issues 와 specific_fixes 를 반드시 반영해 개선된 대본 JSON 을 돌려주세요.

규칙:
- 기존 스키마 유지 (paper_id, paper_title, metadata, script[], rating).
- 라인 삭제·병합·신규 OK. 8~16줄 범위.
- visual_ref 필드 유지. 필요시 수정.
- 마크다운 없이, JSON 한 덩어리만.
"""


async def _critic_query(script_json: str) -> str:
    options = ClaudeAgentOptions(
        system_prompt=CRITIC_SYSTEM, model=CLAUDE_MODEL, allowed_tools=[],
    )
    chunks: list[str] = []
    async for m in query(prompt=script_json, options=options):
        if isinstance(m, AssistantMessage):
            for b in m.content:
                if isinstance(b, TextBlock):
                    chunks.append(b.text)
    return "".join(chunks)


async def _refine_query(script_json: str, critique_json: str) -> str:
    options = ClaudeAgentOptions(
        system_prompt=REFINE_SYSTEM, model=CLAUDE_MODEL, allowed_tools=[],
    )
    prompt = f"[원본 대본]\n{script_json}\n\n[비평]\n{critique_json}"
    chunks: list[str] = []
    async for m in query(prompt=prompt, options=options):
        if isinstance(m, AssistantMessage):
            for b in m.content:
                if isinstance(b, TextBlock):
                    chunks.append(b.text)
    return "".join(chunks)


async def _iterate(paper_title: str, authors: list[str], venue: str, paper_text: str, rounds: int) -> tuple[dict, list[dict]]:
    """Return (final_data, history). history is [{"round":i, "total":n, "data":...}]."""
    raw = await _query(_build_prompt_from_paper(paper_title, authors, venue, paper_text))
    current = json.loads(_strip_fences(raw))
    history: list[dict] = [{"round": 0, "total": None, "data": current}]
    best = current
    best_score = -1
    for i in range(1, rounds + 1):
        critique_raw = await _critic_query(json.dumps(current, ensure_ascii=False))
        try:
            critique = json.loads(_strip_fences(critique_raw))
            total = int(critique.get("total", 0))
        except Exception:
            critique = {"critical_issues": ["파싱 실패, 재작성 요망"], "specific_fixes": []}
            total = 0

        refined_raw = await _refine_query(json.dumps(current, ensure_ascii=False), json.dumps(critique, ensure_ascii=False))
        try:
            current = json.loads(_strip_fences(refined_raw))
        except Exception:
            # if refine fails to produce valid JSON, keep previous
            pass
        history.append({"round": i, "total": total, "data": current})
        if total > best_score:
            best_score = total
            best = current
    return best, history


def generate_from_paper_iterative(
    paper_title: str, authors: list[str], venue: str, paper_text: str, slug: str, rounds: int = 5
) -> dict:
    """5 rounds of self-critique + refine. Saves history to data/scripts/<slug>-shorts.history.json."""
    final, history = asyncio.run(_iterate(paper_title, authors, venue, paper_text, rounds))
    # Save history for inspection
    hist_path = SCRIPTS_DIR / f"{slug}-shorts.history.json"
    hist_path.write_text(json.dumps({"rounds": history}, ensure_ascii=False, indent=2), encoding="utf-8")
    return _postprocess(final, slug)
