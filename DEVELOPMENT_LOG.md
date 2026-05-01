# PaperCast — Development Log

논문 PDF/arXiv URL → 한국어 쇼츠 MP4 자동 생성 파이프라인을 만든 기록.
프로젝트 결정·디버깅 패턴·운영 노하우를 시간순으로 정리.

> 운영 채널: 한국어 메인(`paper-one-shot`), 영어(`paper-one-shot-en`).
> 모든 영상은 60초 안팎의 세로 쇼츠. 두 명의 호스트(민재·수빈)가 까칠하게 토론하는 포맷.

---

## 1. 파이프라인 개요

```
arXiv ID / 로컬 PDF
   │
   ▼
PDF 파싱 (PyMuPDF + pypdf)
   │
   ▼
Claude Sonnet 4.6 (1차 초안) → self-critique → refine → Opus 4.7 polish
   │   ── src/script/shorts_generator.py
   ▼
대화 스크립트 JSON  (data/scripts/{slug}-shorts.json)
   │
   ▼
TTS (CLOVA Voice Premium · 한국어 / Edge TTS · 영어)
   │   ── src/tts/{clova,gemini,edge}.py
   ▼
WAV 라인별 합성  →  MP3 병합 (data/audio/{slug}/...)
   │
   ▼
Figure 인덱싱 + 자동 크롭 (PyMuPDF) + 사용자 수동 크롭 오버라이드
   │   ── src/video/figure_{indexer,cropper}.py
   ▼
타이틀 카드 + 헤더 스트립 + ASS 자막 (문장 단위 청크)
   │   ── src/video/{title_card,subtitle}.py
   ▼
FFmpeg filter_complex 조립 (1080×1920, 30fps, H.264/AAC)
   │   ── src/video/composer.py
   ▼
MP4  →  YouTube Data API v3 업로드 + 썸네일 + publishAt 예약
        ── src/upload/youtube.py
```

---

## 2. 의존성 / 환경

- **OS**: Windows 10, Git Bash 셸 (Unix 경로 사용)
- **Python 3.10+**
- **외부 바이너리**: FFmpeg, Poppler(pdf2image용)
- **API 키** (`.env`):
  - `NCP_CLOVA_KEY_ID`, `NCP_CLOVA_KEY` — Naver CLOVA Voice Premium (메인 한국어 TTS)
  - `GOOGLE_API_KEY` — Gemini TTS (백업)
  - `ANTHROPIC_API_KEY` — Claude Code OAuth 외 직접 호출 시
  - YouTube OAuth 클라이언트 시크릿: `credentials/youtube_oauth_client.json`
  - 채널별 토큰: `credentials/youtube_token_{channel}.json` (자동 생성)

---

## 3. 주요 설계 결정

### 3.1 스크립트 생성 (`src/script/shorts_generator.py`)

- **시스템 프롬프트 핵심 규칙**:
  - 콜드 오픈 + 의문 던지기로 retention
  - 호스트 캐릭터 유지: 민재(건조·긍정), 수빈(까칠·반박)
  - 매 라인에 `visual_ref` (Figure/Table/`__TITLE__`/null) — 영상 페이지 매칭
  - 마지막 라인은 결론 + 이분법 + 오픈루프 ("X파야 Y파야?")
  - `title_hook`은 구체 수치 + FOMO 포함
  - 비속어 금지·일반인 친화적 비유 필수
- **반복 루프**: round 0 초안 → critique → refine → Opus polish (`_opus_polish`)
- **rounds=1 디폴트**: 초기엔 5회였으나 시간/품질 트레이드오프로 1회 고정

### 3.2 Figure 매칭

- `figure_indexer.build_index(pdf)` — 캡션 패턴(`Figure N:`, `Fig. N |` Nature 스타일 등)으로 페이지 매핑
- `figure_cropper.crop_visual(pdf, page, ref, out_png)` — 자동 크롭
- **사용자 수동 크롭 오버라이드 컨벤션**:
  ```
  data/audio/{slug}-shorts/crops/new_Figure_1.png  ← 사용자가 직접 자른 이미지
  ```
  사용자가 알려주면 `mv new_Figure_1.png Figure_1.png`로 덮어쓰기 후 재빌드.
- **`teaser.png`** (선택): `crops/teaser.png` 두면 타이틀 카드 배경에 흐릿한 분위기샷으로 합성됨 (`title_card.py`의 white-key 기반 컴포지팅).

### 3.3 영상 조립 (`src/video/composer.py`)

- `_compose` filter_complex 패턴:
  - 비-타이틀 세그먼트는 88% inner area로 패딩 (Figure 가장자리 여유)
  - `__TITLE__.png`만 풀프레임 — 헤드라인 가독성
  - 헤더 스트립은 첫 세그먼트(타이틀) 끝난 뒤부터 `enable='gte(t,title_dur)'` 로 오버레이
- **자막**: ASS, 문장 단위 청크, 화자별 색, `skip_subtitle: True` 라인은 자막 제외 (타이틀 등)
- **해상도**: SHORTS=`1080×1920`, LONGFORM=`1920×1080`

### 3.4 TTS 보이스

- **CLOVA Premium (한국어 메인)**:
  - 민재 = `nwoosik`
  - 수빈 = `vdain` (pitch=-2)
  - 공통 `speed=-3` (조금 빠르게 — 60초 쇼츠 정보 밀도)
- **Gemini 2.5 TTS**: 폴백/실험용 (영어/멀티스피커)
- **Edge TTS (영어)**: Alex/Sam 보이스, 무료

### 3.5 타이틀 카드 처리

- 초기: 타이틀 카드 보여주고 호스트가 제목 읽음
- 중간: "타이틀 빼자" → `__TITLE__` 라인을 1초 무음 처리 (`pipeline.py:_run_tts_and_merge` 가 silent 1s wav 주입)
- 최종 (현재): **다시 호스트가 제목 읽기** — `scripts/rebuild_with_title.py`가 silence-skip 로직을 우회해서 모든 라인 TTS + 영상 재빌드 + 업로드까지 한 번에 처리.
- 이유: 자막 카드 봐도 "이게 무슨 영상이지?" 싶다는 피드백. 호스트가 직접 제목 읽으면 한 번에 컨셉 전달.

### 3.6 업로드 (`src/upload/youtube.py`)

- **채널별 토큰 분리**: `YOUTUBE_TOKEN_FILE_{channel}` 패턴, OAuth 한 번 인증하면 채널별 토큰 캐시
- **publishAt 예약 업로드**: RFC3339 (`2026-05-03T18:00:00+09:00`), `privacyStatus="private"` + `publishAt` 조합
- **썸네일**: 업로드 후 첫 1초 프레임 추출해서 `thumbnails().set` (커스텀 썸네일이 있어야 인-피드에서 눈에 띔)
- **Shorts 시그널**: 제목/설명에 `#Shorts` 자동 추가

---

## 4. 운영 패턴

### 4.1 일반 워크플로 (1편 만들기)

```bash
# 1. arXiv 논문이면
python -m src.pipeline shorts-only 2503.11651 \
  --venue "CHI 2026 Honorable Mention" \
  --official-url "https://arxiv.org/abs/2503.11651"

# 2. 로컬 PDF (ACM/CHI 등 arXiv 없는 논문)
python scripts/run_local_shorts.py alexnet  # 케이스 분기 안의 헬퍼

# 3. 결과 검토:
#    - data/scripts/{slug}-shorts.json
#    - data/videos/{slug}-shorts.mp4

# 4. 사용자 피드백 반영 (스크립트 수정 / 수동 크롭)
#    - 변경된 라인의 wav만 지우고 재합성
#    - 영상 재빌드: python scripts/rebuild_with_title.py {slug} {publishAt}
```

### 4.2 자주 겪은 이슈 / 해결

| 이슈 | 원인 | 해결 |
|---|---|---|
| `wav count != lines` | 사용자가 스크립트 라인을 수동으로 지웠는데 wav 캐시는 남음 | `data/audio/{slug}-shorts/lines/` 전체 삭제 후 재합성 |
| 타이틀 카드에 `**` 마크다운이 그대로 보임 | textwrap이 `**bold**` 마커를 일반 문자처럼 wrap | `_strip_markdown` 추가, bold 범위는 cleaned 좌표로 추적해서 강조색 적용 |
| FFmpeg path 이스케이프 (`C:\...`) | filter_complex에서 콜론·백슬래시 충돌 | `_escape_filter_path` 헬퍼로 슬래시화 + 콜론 escape |
| 슬러그 vs `paper_id` 미스매치 | Claude가 자기맘대로 paper_id 작성 (`word2vec-arxiv1301` 등) | `_generate_video`는 슬러그 기반 glob으로 PDF 탐색 |
| 영지식증명 비유 모순 ("내용이 다 공개"인데 "가린다") | 메타포 충돌 | "비밀은 절대 안 보냄, 증명서만 보냄" 으로 표현 분리 |
| 32-view DUSt3R 시간 일관성 | 본문 9초·표 200초 혼용 | 논문 캡션(`> 200s`) 기준으로 통일, VGGT 측은 `<0.6s`로 333배 비교 |

### 4.3 예약 스케줄 패턴

- 채널 카덴스: 매일 18:00 KST 1편 공개
- 새로 만든 영상은 다음 빈 슬롯에 `publishAt` 예약
- 기존 예약 영상 교체 필요시: 새로 업로드 → 사용자가 Studio에서 구버전 수동 삭제

---

## 5. 디렉터리

```
youtube-paper/
├── CLAUDE.md                  # Claude Code용 프로젝트 컨텍스트
├── DEVELOPMENT_LOG.md         # 이 파일
├── README.md                  # 사용자용 빠른 시작
├── .env.example
├── requirements.txt
├── pyproject.toml
│
├── src/
│   ├── pipeline.py            # End-to-End CLI (shorts-only / video / shorts)
│   ├── config.py              # 보이스/해상도/경로 설정
│   ├── ingest/
│   │   ├── arxiv_fetcher.py
│   │   └── pdf_parser.py
│   ├── script/
│   │   ├── prompts.py
│   │   ├── shorts_generator.py
│   │   └── validator.py
│   ├── tts/
│   │   ├── clova.py           # 메인 한국어
│   │   ├── gemini.py          # 백업 / 영어
│   │   └── edge.py            # 영어 무료
│   ├── video/
│   │   ├── slide_maker.py     # PDF 페이지 → PNG
│   │   ├── figure_indexer.py
│   │   ├── figure_cropper.py
│   │   ├── title_card.py      # 타이틀 카드 + 헤더 스트립
│   │   ├── subtitle.py        # ASS 빌더
│   │   ├── audio_merger.py
│   │   └── composer.py        # FFmpeg filter_complex
│   └── upload/
│       └── youtube.py         # 업로드 + 썸네일 + publishAt
│
├── scripts/
│   ├── run_example.py         # 스모크 테스트 (Attention 논문)
│   ├── run_local_shorts.py    # arXiv 외 PDF 처리
│   ├── rebuild_with_title.py  # 제목 음성 포함 재빌드 + 재업로드
│   ├── run_combined_frontview.py  # 멀티-페이퍼 합본 쇼츠 사례
│   ├── rebuild_augmenting*.py # 케이스별 재빌드 헬퍼
│   ├── sample_clova_voices.py # CLOVA 보이스 A/B
│   └── update_thumbnails.py
│
├── tests/
│
├── data/                      # 전부 .gitignore (재생성 가능)
│   ├── papers/    *.pdf
│   ├── scripts/   *.json
│   ├── audio/     {slug}/lines/*.wav, {slug}/{slug}.mp3, crops/*.png
│   └── videos/    *.mp4
│
└── credentials/               # .gitignore (OAuth 시크릿/토큰)
    ├── youtube_oauth_client.json
    └── youtube_token_{channel}.json
```

---

## 6. 학습 / 다음에 다른 프로젝트 한다면

- **모델 출력은 무조건 사람이 한 번 본다는 전제로 설계**해야 함. self-critique + Opus polish 도입은 좋았지만, 끝까지 자동화 못 했음. 사용자가 수치/figure/맥락 검증하는 단계가 필수.
- **수동 크롭 오버라이드 컨벤션**(`new_Figure_*.png`)은 의외로 많이 씀. 자동 크롭이 캡션·여백 잘못 잡는 일이 잦음.
- **타이틀 카드/헤더 텍스트의 마크다운 처리**는 처음부터 깔끔히 분리해야 했음. `**bold**` 마커가 영상에 그대로 박히는 사고가 두 번 있었음.
- **YouTube 업로드의 비가역성**: 업로드는 "create new + delete old" 패턴으로 가야 함 (재업로드 X). publishAt 예약이라도 마찬가지.
- **TTS 라인 수와 스크립트 라인 수 동기화**: 사용자가 스크립트 손대면 캐시 wav 전체 무효. assert로 일찍 fail.
