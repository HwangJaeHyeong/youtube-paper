# PaperCast

HCI/AI/VR 논문을 두 명의 AI 호스트가 대화로 리뷰하는 유튜브 콘텐츠 자동 생성 파이프라인.
NotebookLM 스타일이지만 까칠한 비판적 관점 + 논문 뒷이야기로 차별화.

## 빠른 시작

```bash
# 1. 가상환경
python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows

# 2. 의존성
pip install -r requirements.txt

# 3. API 키
cp .env.example .env
# .env 편집:
#   NCP_CLOVA_KEY_ID, NCP_CLOVA_KEY  — 한국어 메인 TTS (CLOVA Voice Premium)
#   GOOGLE_API_KEY                   — Gemini TTS (백업)
#   ANTHROPIC_API_KEY                — 비워두면 Claude Code 구독(OAuth) 사용

# 4. FFmpeg + Poppler 설치 확인
ffmpeg -version
pdftoppm -v   # poppler

# 5. arXiv 쇼츠 (예: VGGT)
python -m src.pipeline shorts-only 2503.11651 \
  --venue "CVPR 2025" --official-url "https://arxiv.org/abs/2503.11651"

# 6. 로컬 PDF 쇼츠 (arXiv 없는 ACM/CHI 논문)
#    PDF 를 data/papers/ 에 두고 scripts/run_local_shorts.py 의 케이스 추가
python scripts/run_local_shorts.py alexnet
```

## 기술 스택

| 역할 | 서비스 |
|---|---|
| 스크립트 생성 (LLM) | Claude Sonnet 4.6 → Opus 4.7 polish (Claude Agent SDK) |
| 한국어 TTS | Naver CLOVA Voice Premium (`nwoosik`, `vdain`) |
| 영어 TTS | Edge TTS / Gemini 2.5 |
| 영상 조립 | FFmpeg (filter_complex) |
| 논문 수집 | arXiv API + 로컬 PDF |
| 업로드 | YouTube Data API v3 (publishAt 예약 + 커스텀 썸네일) |

## 디렉터리

```
src/
├── ingest/   # arXiv 다운로드, PDF 파싱
├── script/   # Claude로 대화 스크립트 생성 (self-critique + Opus polish)
├── tts/      # CLOVA / Gemini / Edge TTS 래퍼
├── video/    # FFmpeg 영상 조립, 타이틀 카드, ASS 자막, Figure 크롭
└── upload/   # YouTube 업로드 (채널별 토큰)
```

상세 설계·프롬프트 원칙·운영 패턴은 [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) 참조.
초기 기획서/철학은 [CLAUDE.md](CLAUDE.md) 참조.
