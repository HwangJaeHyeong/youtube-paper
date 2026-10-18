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

## 대본 생성 엔진 선택

롱폼, 쇼츠, 애니메이션 대본과 비평·수정·최종 검수 모두 Claude 또는 Codex로 실행할 수 있습니다.
기본값은 Claude이며 `.env`에 `LLM_PROVIDER=claude` 또는 `LLM_PROVIDER=codex`를 설정합니다.
명령 앞에 환경 변수를 지정하면 해당 실행에만 적용됩니다 (macOS/Linux).

```bash
# Codex CLI 설치 및 로그인 필요. 현재 CLI의 로그인과 모델 설정을 사용합니다.
LLM_PROVIDER=codex .venv/bin/python -m src.pipeline shorts-only 2503.11651

# Claude Code 로그인 또는 ANTHROPIC_API_KEY 필요
LLM_PROVIDER=claude .venv/bin/python -m src.pipeline shorts-only 2503.11651
```

`CODEX_MODEL`, `CODEX_POLISH_MODEL`로 Codex의 생성·검수 모델을 지정할 수 있습니다.
빈 값은 CLI 기본 모델을 사용합니다. `CLAUDE_MODEL`, `CLAUDE_POLISH_MODEL`은 Claude 모델을 지정합니다.
Codex 실행 제한 시간은 `CODEX_TIMEOUT_SECONDS`(기본 600초), 실행 경로는 `CODEX_BIN`으로 설정합니다.
Codex 연동은 공식 [비대화형 CLI 옵션](https://learn.chatgpt.com/docs/cli/reference)을 사용합니다.
인증 방식에 따라 구독 사용량 또는 API 요금이 적용되며, 한국어 CLOVA TTS 비용은 별도입니다.
기존 쇼츠 대본이 있으면 엔진을 바꿔도 재사용하므로, 비교 생성에는 다른 `--paper-slug`를 사용하세요.

## 기술 스택

| 역할 | 서비스 |
|---|---|
| 스크립트 생성 (LLM) | Claude Agent SDK / Codex CLI 선택 가능 |
| 한국어 TTS | Qwen3-TTS 로컬 GPU Docker 서버 (기본, `KO_TTS=qwen`, `docker compose up -d qwen-tts`) / Naver CLOVA Voice Premium (`KO_TTS=clova`) |
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

## HaptiCraft 공개본 재현

다른 컴퓨터에서 최종 음성·원문 Figure·타이밍을 그대로 재현하려면
[실행 방법](docs/hapticraft.md)을 따르세요. 원문 PDF를 지정하면 API 키 없이 빌드합니다.

```bash
python scripts/rebuild_hapticraft.py --pdf "/path/to/HaptiCraft.pdf"
```
