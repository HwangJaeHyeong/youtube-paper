"""Korean hype-narrator shorts for Attention Is All You Need (Vaswani 2017).

- Single narrator (민재 = nwoosik CLOVA voice)
- First line forced: "인공지능 연구자들은 멘탈이 나가버렸습니다."
- Korean YouTube Shorts vibe: punchy, dramatic, info-dense
- Bypasses default two-host prompt; uses a custom hype-narrator system prompt.

Usage:
    PYTHONPATH=. .venv/bin/python scripts/run_attention_hype.py
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from src.config import CLAUDE_MODEL, PAPERS_DIR, SCRIPTS_DIR
from src.ingest import arxiv_fetcher, pdf_parser
from src.pipeline import _generate_video, _run_tts_and_merge

ARXIV_ID = "1706.03762"
SLUG = "attention-mental-shorts"
FORCED_FIRST_LINE = "인공지능 연구자들은 멘탈이 나가버렸습니다."

SYSTEM_PROMPT = """\
당신은 한국 인기 유튜브 쇼츠 (사물궁이·슈카월드·라끼남 톤) 의 단일 내레이터 대본 작가입니다.
한 명의 내레이터가 빠르고 자극적이고 정보 밀도 높게 풀어가는 30~45초 쇼츠를 JSON 으로.

[캐릭터 — 단일 내레이터]
- 화자 한 명. 모든 script 라인의 speaker = "민재".
- 톤: 차분하지만 단호. 충격 사실을 담담히 던지면서 시청자가 "헐" 하게 만드는 스타일.

[첫 라인 — 무조건]
- script[0].text = "인공지능 연구자들은 멘탈이 나가버렸습니다."
- 이 문장은 일언일자 그대로 유지. 절대 변형 금지.

[리텐션 원칙]
- 매 5~7초마다 새 충격/반전/숫자.
- 라인당 12~22자. 짧고 끊어 치기.
- 추상 형용사("혁신적", "대단한") 금지. 구체 수치·결과로 대체.
- 두 번째 라인부터 첫 라인의 "왜 멘탈이 나갔는지" 를 펀치라인으로 풀어가기.
- 15초 지점에 "근데 더 무서운 건" 같은 두 번째 파동 필수.

[찰진 톤 — 필수]
- 슬랭 허용: "ㄹㅇ", "이게 말이 됨?", "근데 더 무서운 건", "와 이건 진짜".
- 욕설·자극 어휘 금지: 씨발, 존나, 미친, 미쳤다, 미쳤네, ㅁㅊ, 병신, 쩐다, 등 모두 금지.
- "미쳤다" 대신 "이게 말이 됨", "이건 진짜", "후덜덜", "레전드" 사용.

[Vaswani 2017 — 핵심 사실 (이 안에서만 인용)]
- 2017년 NeurIPS 발표 ("Attention Is All You Need")
- 저자: Google Brain + Google Research, 8명 (Vaswani 등)
- 핵심: Recurrence (RNN) 와 Convolution (CNN) 다 빼고, self-attention 만으로 sequence 처리
- BLEU 28.4 on WMT En→De (당시 기존 SOTA 보다 +2 BLEU)
- 학습 시간: 8 GPU × 3.5일 (Big 모델), 12시간 (Base 모델) — 기존 모델 대비 압도적 단축
- multi-head attention 8개 헤드
- 이 논문 이후 BERT, GPT, ChatGPT, 모든 LLM 이 트랜스포머 기반
- 7년치 RNN/CNN 연구가 사실상 우회됨
- 인용 17만 회 이상 (2025 기준)

[수치 인용 규칙 — 엄수]
- 위 [핵심 사실] 안의 수치만 사용. 그 외 임의 통계/외부 비교 금지.
- 불확실하면 정성 표현 ("훨씬 빠름", "압도적으로 적은") 으로.

[클로징 — 마지막 라인]
- "결론: ~" + 강한 한 문장.
- 또는 시청자에게 던지는 짧은 질문 ("그래서 RNN 박사들 다 어디 갔을까?", "지금 LLM 다 이 한 논문에서 시작됨").
- "구독해", "좋아요" 같은 직접 어필 금지.

[출력 — JSON 한 덩어리만, 마크다운 코드펜스 없이]
{
  "paper_id": "attention-mental-shorts",
  "paper_title": "Attention Is All You Need",
  "title_hook": "<썸네일 후킹 — 40자 내, 'Attention' 또는 'Transformer' 약칭 포함>",
  "primary_tag": "Transformer",
  "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "et al."],
  "venue": "NeurIPS 2017",
  "metadata": {
    "target_length": "shorts",
    "estimated_duration_sec": 35,
    "lang": "ko"
  },
  "script": [
    {
      "section": "intro",
      "speaker": "민재",
      "text": "인공지능 연구자들은 멘탈이 나가버렸습니다.",
      "emotion": "neutral",
      "pause_after_ms": 350,
      "visual_ref": null
    }
    // ... 9~12 라인 더, 모두 speaker="민재"
    // visual_ref 는 그 줄이 가리키는 figure 가 있으면 "Figure N" / "Table N", 아니면 null
  ],
  "rating": {
    "민재": 5.0,
    "verdict": "<한 줄 평>"
  }
}

[총 라인 수]: 10~13 라인 (첫 라인 포함).
[모든 speaker]: "민재" 통일.
"""


def _strip_fences(s: str) -> str:
    return re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", s, flags=re.MULTILINE).strip()


async def _claude_query(prompt: str) -> str:
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=CLAUDE_MODEL,
        allowed_tools=[],
    )
    chunks: list[str] = []
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for blk in msg.content:
                if isinstance(blk, TextBlock):
                    chunks.append(blk.text)
    return "".join(chunks)


def _force_constraints(data: dict) -> dict:
    """Sanity: enforce single narrator + forced first line + required fields."""
    data.setdefault("paper_id", SLUG)
    data.setdefault("metadata", {})
    data["metadata"]["target_length"] = "shorts"
    data["metadata"]["lang"] = "ko"

    script = data.get("script", [])
    if not script:
        raise RuntimeError("Claude returned empty script.")

    # Force ALL speakers = 민재
    for line in script:
        line["speaker"] = "민재"
        line.setdefault("section", "intro")
        line.setdefault("emotion", "neutral")
        line.setdefault("pause_after_ms", 200)

    # Force first line text exactly
    script[0]["text"] = FORCED_FIRST_LINE
    script[0]["section"] = "intro"
    script[0]["emotion"] = "neutral"
    script[0]["pause_after_ms"] = 350
    script[0]["visual_ref"] = None

    return data


def main() -> None:
    t_start = time.time()
    print("=" * 70)
    print("Korean Hype-Narrator Shorts — Attention Is All You Need (Vaswani 2017)")
    print("=" * 70)

    # ---- 1/4 arXiv ----
    print(f"\n[1/4] arXiv {ARXIV_ID} 다운로드/캐시 확인...", flush=True)
    pdf_path = arxiv_fetcher.fetch_by_id(ARXIV_ID, dest_dir=PAPERS_DIR, slug=SLUG.replace("-shorts", ""))
    print(f"      PDF: {pdf_path}", flush=True)
    paper = pdf_parser.parse(pdf_path)
    print(f"      title:   {paper.title}", flush=True)
    print(f"      authors: {', '.join(paper.authors[:4])}{'...' if len(paper.authors) > 4 else ''}", flush=True)
    print(f"      length:  {len(paper.text)} chars", flush=True)

    # ---- 2/4 Claude script ----
    print(f"\n[2/4] Claude {CLAUDE_MODEL} 한국식 쇼츠 대본 생성...", flush=True)
    user_prompt = (
        f"논문 제목: {paper.title or 'Attention Is All You Need'}\n"
        f"저자: {', '.join(paper.authors) if paper.authors else 'Vaswani et al.'}\n"
        f"발표지: NeurIPS 2017\n\n"
        f"[논문 본문 발췌 — 인용 가능한 사실/수치만 추출하세요]\n{paper.text[:25000]}"
    )
    raw = asyncio.run(_claude_query(user_prompt))
    cleaned = _strip_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"      [WARN] JSON parse failed: {e}\n      raw response (first 500 chars):\n{cleaned[:500]}", flush=True)
        # Try first JSON blob
        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(cleaned)
    data = _force_constraints(data)

    json_path = SCRIPTS_DIR / f"{SLUG}.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      Saved: {json_path}", flush=True)
    print(f"      title_hook: {data.get('title_hook', '(none)')}", flush=True)
    print(f"      lines:      {len(data['script'])}", flush=True)
    for i, ln in enumerate(data["script"]):
        ref = f" [{ln.get('visual_ref')}]" if ln.get("visual_ref") else ""
        print(f"        [{i:2d}] {ln['text']}{ref}", flush=True)

    # ---- 3/4 CLOVA TTS ----
    print(f"\n[3/4] CLOVA TTS — {len(data['script'])} 라인 합성 + 병합...", flush=True)
    mp3, wavs, _ = _run_tts_and_merge(data, SLUG)
    print(f"      Per-line WAVs: {len(wavs)}", flush=True)
    print(f"      Merged MP3:    {mp3}", flush=True)

    # ---- 4/4 Video ----
    print(f"\n[4/4] FFmpeg 쇼츠 영상 조립 (1080×1920)...", flush=True)
    out_mp4 = _generate_video(SLUG, json_path, mp3, is_shorts=True)

    elapsed = time.time() - t_start
    print(f"\n{'=' * 70}")
    print(f"DONE in {elapsed:.1f}s")
    print(f"Video: {out_mp4}")
    print(f"Open : open {out_mp4}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
