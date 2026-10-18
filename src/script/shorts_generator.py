"""Take a longform script JSON and produce a 30~60 second Shorts version.

Uses the configured Claude or Codex provider (same as longform). Output schema matches the
longform validator, just with fewer lines and metadata.target_length='shorts'.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.config import SCRIPTS_DIR
from src.llm import generate_text
from src.script.generator import _sanitize_sections
from src.script.validator import validate_script

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)

SHORTS_SYSTEM = """\
민재(남)와 수빈(여)이 진행하는 **30~40초 내외** 유튜브 쇼츠 대본을 JSON 으로.
목표: 시청자의 평균 시청 지속 시간을 **끝까지** 끌고 가는 리텐션 최강 쇼츠.

[리텐션 제1 원칙 — 지금까지 평균 20초에서 떨어진다]
- 매 **5~7초** 마다 새 호기심 포인트 또는 페이오프. 데드존 0.
- **루프 개폐 구조**: 1줄째에 질문 던지고 → 3~4줄 뒤 답, 답 직후 다음 루프 시작.
- 전반부(0~10초)에 가장 충격적인 숫자/반전/결과 넣기. 뒤로 갈수록 디테일이 아니라 **함의**·개인 반응 으로 이어가기.
- 15초 지점에 "근데 더 놀라운 건" 같은 **두 번째 파동** 필수.
- 25초 지점에서도 새 정보 or 의외의 각도. "마지막으로" 금지.

[콜드 오픈 — 첫 5초가 80% 결정]
- 첫 줄은 곧바로 **충격 팩트 or 반직관 질문**. "안녕하세요", "오늘은", "이 논문은" 금지.
- 논문 이름·저자 소개 줄 금지 (궁금하면 알아서 찾음).
- **첫 줄은 헤드라인 톤** — 신문 1면 같이 자극적·간결 ("뇌가 멈췄다.", "이걸로 다 끝났음.", "AI가 사람 죽일 뻔.").
- 둘째 줄 (수빈) 은 짧은 충격 리액션 — "잠깐 진짜?", "헐 이거 실화임?", "에이 설마". 무조건 다음 줄 보고 싶게 만드는 한 마디.
- 길게 설명 금지. 콜드 오픈 첫 두 줄은 각각 **15자 이내** 가 이상적.

[찰진 톤 — 의무]
- 논문 설명조 금지. **친구한테 카톡으로 설명하는 톤** 으로.
- 슬랭·구어 활용: "ㄹㅇ", "헐", "근데 더 웃긴 건", "아 이건 좀", "와 이건 진짜", "야 그래서 ~", "그럼 ~ 인데?".
- 짧고 끊어 치는 문장 선호 (12~20자). 한 문장에 정보 1개만.
- 비유는 **일상 + 약간 황당** 조합. "엔진 빼고 더 빨리 달림", "공부 안 한 학생이 시험 1등".
- 감탄 OK: "와 이건 진짜", "이게 말이 됨?", "헐".

[비속어·욕설·자극 어휘 금지 — 엄수]
- 다음 단어 절대 금지: "씨발", "ㅅㅂ", "존나", "ㅈㄴ", "병신", "지랄", "꺼져", "닥쳐", "미친" (그리고 그 변형 "미쳤네", "미쳤다", "ㅁㅊ" 포함).
- 대체 표현 사용:
  · "미쳤다" → "이건 진짜", "이게 말이 됨?", "레전드"
  · "쩐다" → "이건 진짜", "후덜덜"
  · "ㄹㅇ 미친" → "이거 ㄹㅇ", "와 이건 진짜"
- 평가 톤은 그대로 유지하되 어휘만 클린하게.

[수빈 캐릭터 — 짜증/까칠 모드]
- 멍한 동조 ("아 그래서?", "음 그렇구나") 금지. 항상 **반박·의심·시비조** 로.
- 좋은 리액션: "야 그건 좀 이상한데?", "그게 말이 돼?", "에이, 그럼 X는?", "근데 그거 사기 아냐?".
- 수빈은 시청자 대변자 역할. 시청자가 갸웃할 부분 미리 짚어줘야 자연스러움.

[논문 평가 톤 — 평범하면 절대 안됨, 무조건 강한 의견]
- 논문 임팩트에 따라 톤 명확히 갈라줄 것. 중간 톤 ("괜찮은 논문이에요") 금지.
- **레전드/혁신적**: "이건 진짜 레전드 논문임", "AI 역사책에 박힐 논문", "5년 뒤에 교과서에 들어갈 거야", "이거 모르고 AI 한다고?".
- **쓰레기/이상함**: "이딴 게 논문이라고?", "ㅋㅋ 이걸 학회가 통과시킴?", "근데 더 웃긴 건 이게 인용 1만 회야", "그럼에도 의외로 쓸데 있음".
- **과대광고/마케팅**: "이건 솔직히 마케팅 논문 아냐?", "Nature 표지 따려고 짠 거 같은데", "데모 영상은 쩌는데 실제론 안 됨".
- **불완전/한계 명확**: "근데 이게 진짜 가능한 거임?", "솔직히 한계가 너무 큰데", "이거 재현하면 안 될 듯".
- **수빈은 까칠하게 깎아내리고, 민재는 가능하면 변호** — 그래서 의견 충돌이 자연스럽게 생김.

[한 편 = 한 통찰]
- 한 쇼츠에 **한 가지** "이거 몰랐네" 포인트. 여러 팩트 나열 금지.
- 그 통찰을 중심으로 두 호스트가 **서로 파고들어감**. 한 명 독백 3턴 이상 금지.

[두 호스트 — 케미가 곧 재미]
- 민재: 팩트·구체 수치 던짐. 말투 덤덤하지만 포인트는 날카로움.
- 수빈: 즉각 리액션·의문·반박. "근데 그럼 X는?" "아, 잠깐 그럼 ~" 식으로 다음 단계로 밀어붙임.
- 매 교대에 **서로 말 이어받기**. "맞아, 근데 ~" / "그 말 듣고 보니 ~".
- 수빈이 턴마다 최소 1회 날카로운 의문 or 비유 던지기.

[마지막 라인 — "결론 한 줄 + 이분법 CTA" + 오픈 루프 구조]
- 마지막 라인은 두 부분으로 구성:
  1. **결론 (구체 수치 한 줄)** — 논문에서 가장 충격적인 결과 1개를 숫자로 요약.
     예: "결론: LLM 그룹 83%가 자기 글 한 줄도 인용 못 함."
     예: "결론: 학습 시간이 14배 줄었음."
  2. **이분법 논쟁 질문** — 시청자가 한쪽 편 들고 싶게 만드는 질문.
     예: "AI 하루 끊어볼 자신 있어? 댓글로."
     예: "이거 5년 뒤 표준 될까 사장될까?"

- **오픈 루프 (open loop) 필수** — 마지막 라인이 첫 라인과 자연스럽게 이어져 영상이 자동 재생될 때 무한루프처럼 느껴져야 함.
  · 첫 라인이 충격 팩트면, 마지막 라인은 그 팩트의 응답·되묻기로 닫기.
  · 예: 첫 줄 "AI 한 문장에 GPU 5배 태운다." → 마지막 "그래서 너희는 절약파 vs 성능파?" → 자동 재생 → 다시 "AI 한 문장에 GPU 5배 태운다." 가 답처럼 들림.
  · 마지막 라인의 단어가 첫 라인 단어를 callback 하면 이상적 ("뇌가 멈춘다" → "...멈춰본 적 있어?").
  · 시청자가 끝까지 봐도 "끝났다" 느낌이 아니라 "어? 다시 봐도 되겠는데" 라는 여운.

- **별점 멘션 금지** — "4점", "3.5점", "별점" 단어 자체 사용 ❌. 결론 + 이분법으로 대체.
- 단순 "써본 사람?" "뭐 쓰는지?" 류 일반 질문 ❌. 한쪽 편 가르는 질문이어야 함.
- "구독해", "좋아요 눌러" 같은 직접 어필 ❌ (알고리즘 페널티).

[Q&A 흐름 — 엄수]
- 한 호스트가 질문하면 **바로 다음 라인은 같은 화자가 아니라 상대 호스트의 답**.
- 답하지 않고 다른 사실로 넘어가지 말 것.
- 같은 화자가 연속 2턴 이상 말하지 말 것 (예외: 민재가 팩트 + 비유 추가하는 경우만 OK, 단 짧게).
- 질문에 답한 뒤 새 질문 던지는 패턴이 자연스러움.

[자기 이름·상대 이름 부르기 금지 — 엄수]
- 대사 안에서 "민재", "수빈" 이름 호명 절대 금지.
- 1인칭은 "나", "내가". 2인칭은 "너", "네가".
- 단, JSON 의 `speaker` 필드 값은 그대로 "민재"/"수빈".

[일반인 눈높이]
- 전문 용어 등장 즉시 **같은 줄에 한글 풀이** (괄호 사용 OK).
- 영어 약어는 한글 발음 ("비엘이유" X → "블루 점수").
- 추상어("효과적", "혁신적") 금지. "4시간이 8분" 같은 구체 비교.
- 비유 2개 이상, 일상 사물로. "멀티헤드 = 같은 글 8명이 서로 다른 관점으로 읽기".

[사실 정확성 — 엄수]
- **논문 본문·Figure·Table 에 있는 수치만** 인용. 그 외 구체 숫자·통계·퍼센트 **금지** (예: "한국어는 데이터 0.3%", "위키피디아 영국 대비 20분의 1" 같이 검증 불가한 외부 통계).
- 없으면 "정확한 수치는 모르지만 아주 적다" 식 정성 표현으로.
- 비유·과장은 허용되지만 **수치 형태로 위장하지 말 것**.
- 저자 개인사(예: "바에서 떠올렸다")는 **검증된 공개 일화만**. 추측 금지.
- 경쟁 모델 비교 수치는 논문 Table 에 명시된 값만.

[Figure/Table 동기화 — 내용 매칭 엄수]
- 최소 4~5개 라인에 visual_ref 설정 (콜드 오픈 직후·핵심 결과 라인·증거 라인).
- visual_ref 는 그 figure 가 **실제로 다루는 주제** 와 라인 내용이 **정확히 일치** 해야 함.
  · 예: "뇌 연결이 약해" 라인 → 뇌 연결 그림 figure (단순 demographic 그림 ❌)
  · 예: "실험 셋업" 라인 → study protocol figure
  · 예: "인용 능력 비교" 라인 → quotation 그래프 figure
- 라인 내용을 정한 다음, 논문 figure caption 을 검토해 그 라인을 가장 잘 보여주는 figure 를 골라 visual_ref 에 적기.
- 캡션을 모르면 그 라인은 visual_ref=null. 잘못된 figure 거는 것보다 빈 화면이 나음.
- 라인 텍스트 안에 "Figure N" 직접 인용은 visual_ref 와 동일 번호여야 함 (텍스트 "Figure 3 봐" + visual_ref="Figure 1" ❌).

[제목·태그 — 클릭률 직결, 최우선]
- `title_hook`: 한국어 어그로 제목. 형식: "후킹 문구 (논문 약칭)". 최대 40자.

  [제목 작성 원칙 — 둘 중 최소 하나 필수]
  1. **구체 수치 포함** — "14배", "0.3초", "1750억", "90% 정확도", "$100억", "1/1000 비용" 같이 논문의 실제 수치를 제목에 박음.
  2. **FOMO/손해 프레이밍** — "이거 모르면 ~~", "안 쓰면 ~~", "~~한 사람만 아는", "왜 아무도 ~~", "~~ 했어야 했다"
  3. (병행 추천) **반직관·반전** — "버렸더니 더 좋아졌다", "꺼버렸더니 성능 올랐다"
  4. 예시:
     · "학습 14배 빠르게 만든 한 줄 (Batch Norm)" — 수치
     · "ResNet 모르고 AI 한다고? (ResNet)" — FOMO
     · "뉴런 절반 꺼버렸더니 성능이 올랐다 (Dropout)" — 반전
     · "GPT 파인튜닝 비용 1/1000 만든 트릭 (LoRA)" — 수치 + FOMO 느낌
     · "이거 안 쓰면 GPU 5배 태우는 중 (Flash Attn)" — FOMO + 수치

  [절대 금지]
  · 원 논문 제목 그대로 옮기기
  · "이 논문은", "~~에 대해", "~~ 소개", "오늘은" 시작
  · 막연한 형용사만 ("혁신적인", "대단한", "놀라운"). 반드시 수치/반전/FOMO 로 대체.

- `primary_tag`: 논문 카테고리/약칭 하나 (공백·특수문자 없음). 예: "ResNet", "GAN", "강화학습", "CoT", "Diffusion".
  · 금지: 제목 첫 단어 그대로 (Deep, Large, Playing 등 쓰레기).

[출력 — JSON 한 덩어리만, 마크다운 코드블록 없이]
스키마: {paper_id, paper_title, title_hook, primary_tag, authors, venue, metadata, script[], rating}
- metadata.target_length="shorts", estimated_duration_sec=30~40
- script[]: **8~10 항목** (짧고 빠르게, 한 라인 12~16자, 빈 감탄사 금지)
- 라인 필드: section, speaker, text, emotion, pause_after_ms, visual_ref
  · section ∈ intro|background|method|results|backstory|limitations|rating|outro
  · emotion ∈ neutral|skeptical|excited|dry|amused
  · visual_ref: **정확히** "Figure N" 또는 "Table N" 문자열. 설명·overlay·괄호 주석 금지. 없으면 null.
"""


SHORTS_SYSTEM_EN = """\
You write a **25-35 second** YouTube Shorts script as a JSON object, featuring two hosts: **Alex (male)** and **Sam (female)**.
Goal: maximum retention — viewers average 20s, push them all the way through.

[Retention — non-negotiable]
- New curiosity hook or payoff every **5-7 seconds**. Zero dead zones.
- **Loop open/close**: line 1 plants a question → 3-4 lines later answer → immediately open next loop.
- Front-load the most shocking number/twist/result in the first 10 seconds.
- At ~15s mark insert a **second wave**: "But here's the wild part".
- Even at 25s keep new info coming. No "finally".

[Cold open — no intro]
- First line = shocking fact or counterintuitive question. No "Hi", "Today", "This paper".
- Don't introduce paper title or authors (viewers will look it up).

[One short = one insight]
- Exactly **one** "I didn't know that" takeaway. No fact list.
- Two hosts dig INTO it, not around it. No monologue over 3 turns.

[Two hosts — chemistry IS the content]
- Alex: drops hard facts, concrete numbers, dry but sharp.
- Sam: instant reactions, skeptical questions, pushes Alex forward. "Wait, so what about X?" "Hold on —".
- Every turn hands off. "Right, but —" / "Now that you say it —".
- Sam must throw at least one sharp question or analogy per turn.

[Plain language]
- Define jargon in the same line (short parenthetical).
- Replace abstract adjectives ("effective", "novel") with concrete comparisons ("4 hours became 8 minutes").
- At least 2 analogies using everyday objects.

[Factuality — strict]
- Cite only numbers present in the paper body / Figures / Tables. No external stats, no made-up percentages.
- If unknown, say "we don't know the exact number, but it's tiny" — never fabricate.
- Analogies/hyperbole OK; never disguise them as numbers.
- No speculative author anecdotes.

[Figure/Table sync]
- At least 2 concrete Figure/Table citations with accurate `visual_ref`.
- Only set visual_ref when the line actually points at that figure.

[Title & tag — highest CTR lever]
- `title_hook`: English hook title for the thumbnail. Format: "Hook phrase (Paper shortname)". Max 55 chars.
  - Examples: "The one-line trick that changed AI (ResNet)", "Prompting that beat fine-tuning (CoT)"
  - Forbidden: original paper title verbatim, "This paper", long sentences.
- `primary_tag`: one category/shortname, alphanumeric only. e.g. "ResNet", "GAN", "Diffusion", "CoT".
  - Forbidden: first word of the paper title ("Deep", "Large", "Playing", etc.).

[Output — one JSON blob, no markdown fences]
Schema: {paper_id, paper_title, title_hook, primary_tag, authors, venue, metadata, script[], rating}
- metadata.target_length="shorts", estimated_duration_sec=25-35
- script[]: **8-12 items**, each line short and punchy.
- Line fields: section, speaker, text, emotion, pause_after_ms, visual_ref
  - section in intro|background|method|results|backstory|limitations|rating|outro
  - speaker is "Alex" or "Sam"
  - emotion in neutral|skeptical|excited|dry|amused
  - visual_ref: exact string "Figure N" or "Table N" — no descriptions. null otherwise.
- rating uses keys "Alex" and "Sam" (floats 0-5) plus "verdict" (one-line English takeaway).
"""


CRITIC_SYSTEM_EN = """\
You are a ruthless English YouTube Shorts script critic. Benchmark: NotebookLM audio overview quality.

Score the given shorts JSON on 14 criteria 0-10 each and give concrete fixes.

1. cold_open_hook: First line is a cold open (shocking fact / counterintuitive question). "Hi", "Today", "This paper" → 0.
2. second_wave: Does a "but the crazy part" beat land around 10-15s? Missing → 0.
3. retention_loops: New curiosity every 5-7s? 3+ dead lines in a row → 0.
4. single_insight: One central takeaway, not a fact list.
5. turn_taking: Do hosts actually hand off? 3+ monologue turns → penalty.
6. figure_refs: >=2 concrete Figure/Table citations with accurate visual_ref.
7. analogies: >=2 analogies using everyday objects.
8. plain_language: Jargon defined inline; no undefined acronyms.
9. density: No filler interjections / throwaway lines.
10. sam_sharpness: Sam throws a question/pushback every turn.
11. front_loaded: Biggest shock in first 10s, not buried.
12. intuitive: Every line understandable on first listen.
13. concreteness: Concrete numbers/comparisons over abstract adjectives.
14. factuality: No fabricated stats or unverifiable anecdotes.

[Output — one JSON blob, no fences]
{
  "scores": {"cold_open_hook":n, "second_wave":n, "retention_loops":n, "single_insight":n,
             "turn_taking":n, "figure_refs":n, "analogies":n, "plain_language":n,
             "density":n, "sam_sharpness":n, "front_loaded":n, "intuitive":n,
             "concreteness":n, "factuality":n},
  "total": 0-140,
  "critical_issues": ["top 3 pain points"],
  "specific_fixes": ["Rewrite line X as ..." style, 5-10 items]
}
"""


REFINE_SYSTEM_EN = """\
You refine English YouTube Shorts scripts.
Given original script JSON + critique JSON, apply the critical_issues and specific_fixes.

Rules:
- Keep schema (paper_id, paper_title, metadata, script[], rating).
- Add/merge/delete lines freely, 8-16 range.
- Keep visual_ref fields; fix them if wrong.
- Output one JSON blob only, no markdown.
"""


def _build_prompt_from_longform(longform: dict) -> str:
    return (
        "아래 롱폼 대본을 30~60초 쇼츠로 압축해서 JSON으로 돌려주세요.\n\n"
        f"[원본]\n{json.dumps(longform, ensure_ascii=False)}"
    )


def _build_prompt_from_paper(paper_title: str, authors: list[str], venue: str, paper_text: str, lang: str = "ko") -> str:
    if lang == "en":
        authors_str = ", ".join(authors) if authors else "unknown"
        return (
            f"Write a 25-35 second Shorts script as JSON from this paper. "
            f"Concrete Figure/Table citations required.\n\n"
            f"Paper title: {paper_title}\n"
            f"Authors: {authors_str}\n"
            f"Venue: {venue}\n\n"
            f"[Paper body (excerpt)]\n{paper_text[:40000]}"
        )
    authors_str = ", ".join(authors) if authors else "미상"
    return (
        f"아래 논문으로 30~60초 쇼츠 대본을 JSON 으로 작성하세요. "
        f"Figure/Table 구체 인용 필수.\n\n"
        f"논문 제목: {paper_title}\n"
        f"저자: {authors_str}\n"
        f"발표지: {venue}\n\n"
        f"[논문 본문 (발췌)]\n{paper_text[:40000]}"
    )


async def _query(prompt: str, lang: str = "ko") -> str:
    return await generate_text(SHORTS_SYSTEM_EN if lang == "en" else SHORTS_SYSTEM, prompt)


def _strip_fences(s: str) -> str:
    return _FENCE_RE.sub("", s).strip()


def _parse_first_json(s: str) -> dict:
    """Extract the first valid JSON object. Tolerates trailing commentary."""
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(_strip_fences(s))
    return obj


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
    data = _parse_first_json(raw)
    return _postprocess(data, longform_slug)


def generate_from_paper(
    paper_title: str, authors: list[str], venue: str, paper_text: str, slug: str
) -> dict:
    raw = asyncio.run(_query(_build_prompt_from_paper(paper_title, authors, venue, paper_text)))
    data = _parse_first_json(raw)
    return _postprocess(data, slug)


# ---------- Self-critique + refine loop ----------

CRITIC_SYSTEM = """\
당신은 한국어 유튜브 쇼츠 대본 혹독한 비평가입니다. NotebookLM 오디오 오버뷰 급을 기준으로.

주어진 쇼츠 JSON 을 아래 10가지 항목으로 0~10점 채점하고, 반드시 구체 개선 지시도 주세요.

[체크리스트 — 가장 중요: retention, second_wave, no_intro]
1. cold_open_hook: 첫 줄이 콜드 오픈 (인사·소개 없이 충격 팩트/반직관 질문). "안녕", "오늘은", "이 논문은"으로 시작하면 0점.
2. second_wave: 10~15초 지점에 "근데 더 놀라운 건~" 같은 두 번째 파동이 있는가? 없으면 0점 (여기서 시청자 이탈).
3. retention_loops: 매 5~7초 새 호기심 포인트 or 페이오프? 데드존 3줄 이상 연속이면 0점.
4. single_insight: 한 편이 하나의 통찰 중심? 팩트 나열 금지.
5. turn_taking: 두 호스트가 서로 이어받는가? 독백 3턴 연속이면 감점.
6. figure_refs: Figure/Table 최소 2회 구체 인용 + visual_ref 정확 기입.
7. analogies: 추상→일상 비유 2개 이상.
8. plain_language: 전문 용어 즉시 한글 풀이 + 영어 약어 한글 발음.
9. density: 빈 감탄사·버리는 줄 0개.
10. subin_sharpness: 수빈이 턴마다 의문·반박·날카로운 질문.
11. front_loaded: 가장 충격적인 숫자/반전을 뒤로 미루지 않고 10초 안에 배치?
12. intuitive: 모든 라인이 한 번에 이해?
13. concreteness: 추상어 대신 구체 수치/비유.
14. factuality: 논문 밖 검증 불가 수치/통계/개인사 없음? (예: "한국어 0.3%", "위키 영국 대비 20분의 1", 출처 없는 일화 등 있으면 0점)

[출력 형식 — 오직 JSON 한 덩어리만, 코드펜스 없이]
{
  "scores": {"hooking":n, "single_insight":n, "four_act_flow":n, "turn_taking":n,
             "figure_refs":n, "analogies":n, "plain_language":n, "density":n,
             "subin_sharpness":n, "payoff":n, "intuitive":n, "retention":n,
             "concreteness":n, "factuality":n},
  "total": 0~140,
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


async def _critic_query(script_json: str, lang: str = "ko") -> str:
    return await generate_text(CRITIC_SYSTEM_EN if lang == "en" else CRITIC_SYSTEM, script_json)


async def _refine_query(script_json: str, critique_json: str, lang: str = "ko") -> str:
    prompt = f"[원본 대본]\n{script_json}\n\n[비평]\n{critique_json}"
    return await generate_text(REFINE_SYSTEM_EN if lang == "en" else REFINE_SYSTEM, prompt)


async def _iterate(paper_title: str, authors: list[str], venue: str, paper_text: str, rounds: int, lang: str = "ko") -> tuple[dict, list[dict]]:
    """Return (final_data, history). history is [{"round":i, "total":n, "data":...}]."""
    print(f"  [round 0] initial draft...", flush=True)
    raw = await _query(_build_prompt_from_paper(paper_title, authors, venue, paper_text, lang=lang), lang=lang)
    current = _parse_first_json(raw)
    history: list[dict] = [{"round": 0, "total": None, "data": current}]
    best = current
    best_score = -1
    for i in range(1, rounds + 1):
        print(f"  [round {i}/{rounds}] critique...", flush=True)
        critique_raw = await _critic_query(json.dumps(current, ensure_ascii=False), lang=lang)
        try:
            critique = _parse_first_json(critique_raw)
            total = int(critique.get("total", 0))
        except Exception:
            critique = {"critical_issues": ["파싱 실패, 재작성 요망"], "specific_fixes": []}
            total = 0
        print(f"  [round {i}/{rounds}] score={total}/140, refining...", flush=True)
        refined_raw = await _refine_query(json.dumps(current, ensure_ascii=False), json.dumps(critique, ensure_ascii=False), lang=lang)
        try:
            current = _parse_first_json(refined_raw)
        except Exception:
            # if refine fails to produce valid JSON, keep previous
            pass
        history.append({"round": i, "total": total, "data": current})
        if total > best_score:
            best_score = total
            best = current
    return best, history


POLISH_SYSTEM = """\
당신은 한국어 유튜브 쇼츠 대본의 마지막 자연스러움 검수자입니다 (Opus).
주어진 JSON 대본을 받아서 오직 다음 케이스만 고치세요.

[고쳐야 할 항목]
1. 질문에 대한 답이 다른 얘기로 빠진 경우 (Q&A 단절)
2. 같은 화자가 연속 2턴 이상 (자연스러운 짧은 추가 1줄은 OK)
3. 한 라인에 질문 + 자기 답변이 같이 들어간 경우
4. 어색한 어순·조사·구어 (예: "단계별로 생각해봐 힌트가" → "'단계별로 생각해봐' 같은 힌트가")
5. 갑자기 별점 등장 (직전 라인과 자연스러운 전환 필요)
6. "민재", "수빈" 이름 자기/상대 부르기

[원칙]
- 가능한 최소 수정. 의미·정보·논문 인용 수치는 유지.
- 라인 수와 speaker 순서는 유지하되, 필요시 한두 라인 추가/삭제 OK.
- visual_ref 는 유지.

[출력 — JSON 한 덩어리, 코드펜스 없이]
{
  "fixes": ["고친 라인 번호 + 한줄 사유 (5개 이내)"],
  "script": [...전체 수정된 script 배열...]
}
"""


async def _opus_polish(script_data: dict) -> dict:
    """Configured provider final review of dialogue and Q&A flow."""
    raw = await generate_text(POLISH_SYSTEM, json.dumps(script_data, ensure_ascii=False), polish=True)
    try:
        result = _parse_first_json(raw)
        if "script" in result and isinstance(result["script"], list):
            print(f"  [polish] fixes: {result.get('fixes', [])}", flush=True)
            script_data["script"] = result["script"]
    except Exception as e:
        print(f"  [polish] failed, keeping original: {e}", flush=True)
    return script_data


def generate_from_paper_iterative(
    paper_title: str, authors: list[str], venue: str, paper_text: str, slug: str, rounds: int = 5, lang: str = "ko"
) -> dict:
    """N rounds of self-critique + refine + 1 Opus polish. Saves history."""
    final, history = asyncio.run(_iterate(paper_title, authors, venue, paper_text, rounds, lang=lang))
    if lang == "ko":
        print("  [polish] reviewing for awkward dialogue...", flush=True)
        final = asyncio.run(_opus_polish(final))
    # Save history for inspection
    hist_path = SCRIPTS_DIR / f"{slug}-shorts.history.json"
    hist_path.write_text(json.dumps({"rounds": history}, ensure_ascii=False, indent=2), encoding="utf-8")
    return _postprocess(final, slug)
