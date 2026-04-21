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
# .env 편집: GOOGLE_API_KEY 필수.
# ANTHROPIC_API_KEY 는 비워두면 Claude Code 구독(OAuth)으로 돌아감.

# 4. FFmpeg 설치 확인
ffmpeg -version

# 5. 파이프라인 실행 (HapticGen 테스트)
python scripts/run_example.py
```

## 기술 스택

| 역할 | 서비스 |
|---|---|
| 스크립트 생성 (LLM) | Claude Agent SDK (`claude-opus-4-7`, 구독 OAuth) |
| 음성 합성 (TTS) | Google AI Studio — Gemini 2.5 TTS |
| 영상 조립 | FFmpeg |
| 논문 수집 | arXiv API |
| 업로드 (Phase 4) | YouTube Data API v3 |

## 디렉터리

```
src/
├── ingest/   # arXiv 다운로드, PDF 파싱
├── script/   # Claude로 대화 스크립트 생성
├── tts/      # Gemini TTS 래퍼
├── video/    # FFmpeg 영상 조립
└── upload/   # YouTube 업로드
```

자세한 설계·프롬프트 원칙·개발 Phase 는 [CLAUDE.md](CLAUDE.md) 참조.
