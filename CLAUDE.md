# PaperCast — AI 논문 리뷰 팟캐스트 자동화

## 프로젝트 개요

HCI/AI/VR 분야 논문을 두 명의 AI 호스트가 대화 형식으로 리뷰하는 유튜브 콘텐츠 자동 생성 시스템. NotebookLM 스타일이지만 **까칠한 비판적 관점 + 논문 뒷이야기**로 차별화.

**최종 산출물**: 논문 PDF 또는 arXiv URL을 입력하면 → 10~15분짜리 MP4 영상이 나오는 End-to-End 파이프라인.

## 타겟 포맷

- **호스트 A (민재)**: 기술 긍정적, 건조한 톤, 논문 저자 편에서 설명
- **호스트 B (수빈)**: 까칠함, 의문 제기, 한계 지적, 농담 섞음
- **분량**: 롱폼 10~15분 / 쇼츠 30~60초
- **언어**: 한국어 (1차), 영어 확장 고려
- **스타일**: "스타트업 엔지니어 둘이 점심 먹으며 논문 까는 느낌"

## 기술 스택

### 필수 (결정됨)

- **언어**: Python 3.10+
- **LLM**: Claude Agent SDK (`claude-agent-sdk`) + `claude-opus-4-7`
  - 기본값: Claude Code **구독 OAuth** 사용 (별도 Anthropic API 과금 없음)
  - Phase 4 자동화 시 `ANTHROPIC_API_KEY` 설정하면 pay-per-token 으로 전환
- **TTS**: **Google AI Studio — Gemini 2.5 TTS** (멀티스피커 모드)
  - 모델: `gemini-2.5-flash-preview-tts` (롱폼) / `gemini-2.5-pro-preview-tts` (고품질)
  - 한 번의 API 호출로 두 호스트 대화를 통째로 합성 가능
  - 한국어 지원, 30개 내외 보이스 프리셋 제공 (Kore, Puck, Charon, Leda, Orus, Aoede …)
- **영상 조립**: FFmpeg (ffmpeg-python 래퍼)
- **논문 수집**: arXiv API
- **업로드**: YouTube Data API v3

### 백업/대안 (Gemini TTS 불안정 시)

- Amazon Polly Korean (`Seoyeon` 단일 보이스 한계 있음)
- ElevenLabs Multilingual v2 ($22/월)
- CLOVA Voice (네이버, 한국어 다수 보이스)

## 실행 환경 제약

- **개발 머신**: Windows 10 (`c:\git\youtube-paper`) — 메인 작업 환경
- **로컬 AI 연산 금지**: 무거운 모델은 전부 클라우드 API 사용
- **머신 역할**: API 호출, FFmpeg 영상 인코딩, 파일 관리만
- **셸**: Git Bash (Unix 스타일 경로 사용, `/c/git/youtube-paper`)

## 디렉터리 구조

```
youtube-paper/
├── CLAUDE.md                    # 이 파일 (Claude Code 참조용)
├── README.md                    # 사용자용 설명
├── .env.example                 # API 키 템플릿
├── .gitignore
├── requirements.txt
├── pyproject.toml
│
├── src/
│   ├── __init__.py
│   ├── config.py               # 환경변수, 보이스 설정
│   │
│   ├── ingest/
│   │   ├── arxiv_fetcher.py    # arXiv API로 논문 검색·다운로드
│   │   └── pdf_parser.py       # PDF → 텍스트·메타데이터 추출
│   │
│   ├── script/
│   │   ├── prompts.py          # Claude용 프롬프트 템플릿
│   │   ├── generator.py        # 논문 → 대화 스크립트 JSON
│   │   └── validator.py        # 생성 결과 검증 (JSON 스키마)
│   │
│   ├── tts/
│   │   ├── base.py             # 공통 인터페이스
│   │   └── gemini.py           # Google AI Studio Gemini TTS 래퍼
│   │
│   ├── video/
│   │   ├── audio_merger.py     # 개별 대사 mp3 → 하나로 병합
│   │   ├── subtitle.py         # SRT 자막 생성
│   │   ├── slide_maker.py      # 논문 페이지 → 슬라이드 이미지
│   │   └── composer.py         # 최종 영상 조립 (FFmpeg)
│   │
│   ├── upload/
│   │   └── youtube.py          # YouTube Data API v3
│   │
│   └── pipeline.py             # End-to-End 오케스트레이션
│
├── tests/
│   ├── test_script_generator.py
│   ├── test_tts.py
│   └── test_pipeline.py
│
├── data/
│   ├── papers/                 # 입력 PDF
│   ├── scripts/                # 생성된 JSON 스크립트
│   ├── audio/                  # 개별·병합 오디오
│   └── videos/                 # 최종 영상
│
└── scripts/
    └── run_example.py          # HapticGen 논문으로 테스트
```

## 스크립트 JSON 스키마

Claude가 논문에서 생성할 대화 포맷:

```json
{
  "paper_id": "hapticgen-chi2025",
  "paper_title": "HapticGen: Generative Text-to-Vibration Model",
  "authors": ["Youjin Sung", "Kevin John", "Sang Ho Yoon", "Hasti Seifi"],
  "venue": "CHI 2025",
  "metadata": {
    "estimated_duration_sec": 720,
    "target_length": "longform",
    "generated_at": "2026-04-21T10:00:00Z"
  },
  "script": [
    {
      "section": "intro",
      "speaker": "민재",
      "text": "안녕하세요, 오늘은 CHI 2025 논문 하나 까보려고 합니다.",
      "emotion": "neutral",
      "pause_after_ms": 300
    },
    {
      "section": "intro",
      "speaker": "수빈",
      "text": "잠깐. 텍스트로 진동을 만든다고요?",
      "emotion": "skeptical",
      "pause_after_ms": 500
    }
  ],
  "rating": {
    "민재": 4.0,
    "수빈": 3.5,
    "verdict": "HCI/햅틱 관심 있으면 필독"
  }
}
```

**섹션 구성** (고정): `intro` → `background` → `method` → `results` → `backstory` → `limitations` → `rating` → `outro`

## 핵심 프롬프트 원칙

`src/script/prompts.py`에서 Claude에게 전달할 시스템 프롬프트는 반드시 다음을 포함:

1. **비율 강제**: 논문 요약 30%, 의심·뒷이야기·현실 적용 70%
2. **캐릭터 유지**: 수빈은 매 섹션마다 최소 1번 의문·반박 제기
3. **전문 용어 처리**: 등장 즉시 "~인데 쉽게 말하면 ~" 풀이 필수
4. **구어체**: 논문 낭독 금지, 실제 대화처럼 "음...", "잠깐" 등 포함
5. **별점 엔딩**: 두 호스트가 각자 별점 주고 한 줄 평가
6. **환각 방지**: 수치·저자 정보는 논문 PDF에서 발췌, 불확실하면 "정확한 수치는 논문 참조"

## TTS 보이스 매핑 (Google AI Studio Gemini)

```python
# src/config.py
VOICE_CONFIG = {
    "민재": {
        "provider": "gemini",
        "voice_name": "Orus",        # 남성, 차분함 (후보: Charon, Fenrir, Puck)
        "model": "gemini-2.5-flash-preview-tts",
        "style_prompt": "건조하고 설명하는 톤, 살짝 느리게"
    },
    "수빈": {
        "provider": "gemini",
        "voice_name": "Aoede",       # 여성, 또랑또랑 (후보: Kore, Leda, Callirhoe)
        "model": "gemini-2.5-flash-preview-tts",
        "style_prompt": "까칠하고 의심 많은 톤, 말 빠르게"
    }
}
```

**구현 시 주의사항**:
- Gemini 2.5 TTS는 **멀티스피커 모드**로 두 화자 대화를 한 번에 생성 가능 → 섹션 단위로 일괄 호출하면 비용·속도 유리
- 개별 대사 단위로 자르려면 싱글 스피커 모드로 반복 호출 (자막 타임스탬프 정밀도 ↑)
- Phase 1에서는 **개별 호출 방식**으로 시작 (자막 생성 편의성). 품질·비용 확인 후 Phase 2에서 멀티스피커로 최적화 검토.
- 보이스 프리셋 선정은 `scripts/run_example.py`에서 샘플 대사 5~10개 합성해 A/B 비교.

## FFmpeg 영상 조립 규격

- **해상도**: 1920x1080 (롱폼) / 1080x1920 (쇼츠)
- **프레임레이트**: 30fps
- **오디오**: AAC 192kbps
- **비디오 코덱**: H.264
- **자막**: SRT → 하드코딩 (소프트 자막은 YouTube에서 별도 업로드)
- **슬라이드 전환**: 대사 섹션 단위로 논문 페이지 이미지 변경

## 개발 순서 (MVP → 풀 자동화)

### Phase 1: 수동 검증 가능한 최소 파이프라인 (1주)
1. arXiv에서 HapticGen 논문 PDF 다운로드
2. Claude API로 대화 스크립트 생성
3. Gemini TTS로 음성 mp3 생성 (각 대사별)
4. FFmpeg로 오디오 병합 (영상 없이 오디오만)
5. **검증**: 사람이 들어보고 품질 판단

### Phase 2: 영상 조립 (1주)
1. 논문 PDF → 페이지 이미지 추출 (`pdf2image`)
2. 자막 생성 (대사별 길이로 타임스탬프 계산 또는 `whisper`)
3. FFmpeg로 슬라이드 + 오디오 + 자막 합성

### Phase 3: 쇼츠 버전 (3일)
1. 롱폼 스크립트 → 30~60초 압축 스크립트 변환 (Claude로)
2. 세로 영상 포맷

### Phase 4: 자동화 (1주)
1. arXiv 일일 크롤러 (관심 카테고리 자동 수집)
2. YouTube 자동 업로드
3. 스케줄러 (cron 또는 GitHub Actions)

### Phase 5: 품질 개선 (지속)
1. 다양한 Gemini TTS 보이스 A/B 테스트
2. 프롬프트 엔지니어링 반복
3. 시청자 피드백 반영

## 쇼츠 1편 제작 워크플로 (현 운영 표준)

> 위쪽 "스크립트 JSON 스키마" 섹션은 **롱폼 멀티스피커** 비전. 현재 운영 중인 쇼츠는 **민재 단독, 10줄 고정 템플릿**으로 발산. 새 논문 1편을 처리할 때는 아래 패턴을 그대로 복제할 것.

### 4개 산출물 (slug 기준 통일)
새 슬러그를 정한다 (예: `aivtuber`). 4개 위치에 같은 슬러그를 쓴다.

| 위치 | 파일 | 역할 |
|---|---|---|
| `data/papers/<slug>.pdf` | 논문 원문 | 수치·인용 검증용 (PDF 직접 다운) |
| `data/scripts/<slug>-shorts.json` | 스크립트 | 아래 10줄 템플릿 |
| `scripts/rebuild_<slug>.py` | 빌드 | CLOVA TTS + 영상 합성 |
| `scripts/upload_<slug>.py` | 업로드 | YouTube **private** 업로드 |

### 10줄 단일 화자 템플릿 (정확히 이 구성)
```
intro      [0] "X 멘탈이 나가버렸습니다."         (350ms pause)
intro      [1] "<충격적 사실 한 줄>거든요."         (300ms)
background [2] "원래 <기존 방식>"                   (250ms)
method     [3] "근데 <연구팀>이 <뭘 했는지>"        (300ms)
method     [4] "<핵심 수치/결과 1>"                 (300ms)
method     [5] "<핵심 수치/결과 2>"                 (350ms)
method     [6] "그게 <이름>의 핵심 아이디어입니다."  (400ms)
backstory  [7] "근데 진짜 무서운 건, <뒷이야기>"   (350ms, emotion: solemn)
outro      [8] "<랩명>이 <학회>에 발표한 논문이에요." (350ms)
outro      [9] "X들 다들 어디 갔을까요?"            (0ms, emotion: deadpan)
```
- 모든 줄 `speaker: "민재"`, `lang: "ko"`, `estimated_duration_sec: 38`
- `visual_ref`는 Figure 번호 또는 `null`
- 첫 줄 `X`와 마지막 줄 `X`는 동일한 직군 (예: "한국 판사들" / "사주 도사들" / "트위치 인간 버튜버들")

### title_hook 패턴
```
"X 멘탈을 날려버린 Y\n(**랩명/소속** 논문 약칭)"
```
- 교수 이름 금지, **랩/연구소/학교 이름만** (예: "KAIST + LBox", "중국과학원 + 상하이푸둥검찰", "Notre Dame 데이터마이닝")
- 메모리: `feedback_no_professor_names.md`, `feedback_title_pattern.md` 참조

### 메타데이터 필수 키
```json
{
  "paper_id": "<slug>-shorts",
  "paper_title": "<영문 원제>",
  "title_hook": "...",
  "primary_tag": "<CamelCase 약칭, hashtag로 쓰임>",
  "authors": ["First Author", "et al."],
  "venue": "<학회 + 연도>",
  "metadata": {"target_length": "shorts", "estimated_duration_sec": 38, "lang": "ko", "official_url": "<arXiv/DOI>"},
  "rating": {"민재": 5.0, "verdict": "<한 줄 평>"}
}
```

### 빌드/업로드 스크립트 템플릿
참고 원본: `scripts/rebuild_aiprosecutor.py`, `scripts/upload_lcube.py`. 새 슬러그용은 SLUG·해시태그 리스트만 갈아끼우면 됨.
- rebuild: `_run_tts_and_merge(data, SLUG)` → `_generate_video(SLUG, ..., is_shorts=True, subtitle_style="hype", sticky_visuals=False)`
- upload: `privacy_status="private"`, `is_shorts=True`, 해시태그는 도메인별 (논문리뷰/AI는 공통, 나머지는 주제별)

### 실행 순서
1. PDF 다운 → `data/papers/<slug>.pdf`
2. 논문 읽고 **수치·소속 검증** (Claude가 만든 줄은 반드시 원문 대조)
3. JSON 작성 → 사용자 확인 받기
4. `.venv/bin/python scripts/rebuild_<slug>.py` (CLOVA TTS 호출됨, 비용 발생)
5. **1.2배속 fast 변환** (업로드 스크립트가 `<slug>-shorts-fast.mp4`를 요구):
   ```bash
   ffmpeg -y -i data/videos/<slug>-shorts.mp4 \
     -filter_complex "[0:v]setpts=PTS/1.2[v];[0:a]atempo=1.2[a]" \
     -map "[v]" -map "[a]" -c:v libx264 -preset fast -crf 20 \
     -c:a aac -b:a 192k -movflags +faststart \
     data/videos/<slug>-shorts-fast.mp4
   ```
6. `data/videos/<slug>-shorts-fast.mp4` 사람이 미리보기
7. `.venv/bin/python scripts/upload_<slug>.py` (private 업로드, 사용자가 YouTube Studio에서 수동 공개)

> Python은 반드시 프로젝트 `.venv` 사용 (`typer` 등 의존성이 시스템 파이썬에 없음).

## 개발 시 금기 사항

- **로컬에서 무거운 AI 모델 돌리지 말 것** — 전부 API 사용
- **유튜브/TikTok에서 오디오 추출해서 TTS 대용으로 쓰지 말 것** (저작권)
- **논문 원문 그대로 영상에 삽입 금지** — 이미지는 요약/재작성
- **Claude가 생성한 수치·인용은 반드시 PDF와 대조 검증**
- **API 키를 코드나 git에 커밋 금지** — `.env` + `.gitignore` 필수

## 예상 운영 비용

월 기준 (주 2편 업로드 가정):
- Claude API: 약 10~30만원 (PDF 분석 비용)
- Google AI Studio Gemini TTS: 무료 티어 우선 활용, 초과분 종량제
- AWS S3 저장소(선택): 1만원 이하
- **총 월 10~35만원** (Gemini 무료 티어 활용 시 크게 절감)

## 참고 자료

- Claude API 문서: https://docs.claude.com/en/api/overview
- Claude Code 문서: https://docs.claude.com/en/docs/claude-code/overview
- Google AI Studio: https://aistudio.google.com/
- Gemini API (TTS): https://ai.google.dev/gemini-api/docs/speech-generation
- YouTube Data API v3: https://developers.google.com/youtube/v3
- arXiv API: https://info.arxiv.org/help/api/
- FFmpeg: https://ffmpeg.org/documentation.html

## 첫 번째 테스트 논문

**목표 논문**: HapticGen (Sung et al., CHI 2025) — 프로젝트 자체 목적에 맞는 첫 타겟.
- ACM DL 전용(arXiv 없음)이라 ID 기반 `fetch_by_id` 불가. PDF 수동 다운 필요.
- https://hapticgen.hcitech.org/ 또는 ACM DL (DOI: 10.1145/3706598.3713609) 에서 받아 `data/papers/hapticgen-chi2025.pdf` 로 저장 후 파이프라인 호출.

**임시 스모크 테스트**: `scripts/run_example.py` 는 arXiv 에서 바로 받을 수 있는 *Attention Is All You Need* (1706.03762) 로 End-to-End 검증.
