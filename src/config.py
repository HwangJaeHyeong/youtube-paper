"""Central config: env vars, voice mapping, path layout."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- API keys ---
# ANTHROPIC_API_KEY: optional. Leave empty to use Claude Code subscription via
# the Agent SDK's OAuth flow. Set it to switch to pay-per-token billing.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
NCP_CLOVA_KEY_ID = os.getenv("NCP_CLOVA_KEY_ID", "")
NCP_CLOVA_KEY = os.getenv("NCP_CLOVA_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
PAPERS_DIR = DATA_DIR / "papers"
SCRIPTS_DIR = DATA_DIR / "scripts"
AUDIO_DIR = DATA_DIR / "audio"
VIDEOS_DIR = DATA_DIR / "videos"

for _d in (PAPERS_DIR, SCRIPTS_DIR, AUDIO_DIR, VIDEOS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- LLM models ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "claude").strip().lower()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
CLAUDE_POLISH_MODEL = os.getenv("CLAUDE_POLISH_MODEL", "claude-opus-4-7")
# Empty uses the model configured in Codex CLI.
CODEX_MODEL = os.getenv("CODEX_MODEL", "")
CODEX_POLISH_MODEL = os.getenv("CODEX_POLISH_MODEL", "") or CODEX_MODEL
CODEX_BIN = os.getenv("CODEX_BIN", "codex")
CODEX_TIMEOUT_SECONDS = float(os.getenv("CODEX_TIMEOUT_SECONDS", "600"))

# --- TTS: Gemini 2.5 (Google AI Studio) ---
# https://ai.google.dev/gemini-api/docs/speech-generation
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"

# --- TTS: CLOVA Voice Premium (Naver Cloud) ---
# https://api.ncloud-docs.com/docs/ai-naver-clovavoice-ttspremium
CLOVA_TTS_URL = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"

# --- TTS: Qwen3-TTS (local GPU via Docker server: `docker compose up -d qwen-tts`) ---
# https://github.com/QwenLM/Qwen3-TTS — model is chosen in docker-compose.yml (QWEN_TTS_MODEL)
QWEN_TTS_URL = os.getenv("QWEN_TTS_URL", "http://127.0.0.1:8880/tts")
# Lines per GPU forward pass. 16GB VRAM (RTX 5070 Ti) 기준 시작값 — OOM 나면 줄이고, 여유 있으면 올릴 것.
QWEN_TTS_BATCH = int(os.getenv("QWEN_TTS_BATCH", "16"))
# Korean host voices: qwen (default) | clova
KO_TTS = os.getenv("KO_TTS", "qwen").strip().lower()

VOICE_CONFIG: dict[str, dict] = {
    "민재": {
        "provider": KO_TTS,
        "speaker": "nwoosik",
        # Qwen3-TTS Base voice clone: 참고 음성 + 그 음성의 정확한 대본
        "qwen_ref_audio": PROJECT_ROOT / "voices" / "minjae_ref.mp3",
        "qwen_ref_text": (
            "알고 보니까 태권도 여러분들, 뭐 뭔 태권도가 있고 이게 다 살짝 좀 다르더만. "
            "근데 알고 보니까 엄청 유명하신 분인 거야."
        ),
        "speed": -3,
        "pitch": 0,
        "volume": 0,
        "supports_emotion": False,
        "subtitle_color": "&H00E8993D",
    },
    "수빈": {
        "provider": KO_TTS,
        "speaker": "vdain",
        "qwen_ref_audio": PROJECT_ROOT / "voices" / "subin_ref.mp3",
        "qwen_ref_text": (
            "삼이일하고 떴을 때 보인 사람한테. 자, 일, 이, 삼, 사, 오. 일, 이, 삼, 사, 오. "
            "눈 감았다 떴을 때 제 맨 밑에 있는 댓글로 뽑겠습니다."
        ),
        "speed": -3,
        "pitch": -2,
        "volume": 0,
        "supports_emotion": False,
        "subtitle_color": "&H00B569FF",
    },
    "Alex": {
        "provider": "edge",
        "voice_name": "en-US-GuyNeural",
        "rate": "+10%",
        "pitch": "+0Hz",
        "subtitle_color": "&H00E8993D",
    },
    "Sam": {
        "provider": "edge",
        "voice_name": "en-US-JennyNeural",
        "rate": "+12%",
        "pitch": "+20Hz",
        "subtitle_color": "&H00B569FF",
    },
}

# CLOVA emotion mapping from script's "emotion" field → CLOVA emotion int.
# ndain/njihwan 등 일반 화자는 {0 neutral, 1 sad, 2 happy} 만 지원 (VS14 회피).
# angry(3) 은 nsabina, nminseok 같은 특수 화자에만 있음.
CLOVA_EMOTION_MAP = {
    "neutral": 0,
    "dry": 0,
    "skeptical": 0,   # 까칠함은 화자 톤에 맡김 (angry 는 미지원)
    "excited": 2,     # → happy
    "amused": 2,      # → happy
}

# 보이스 후보 (쇼츠 스타일):
#   남성: njihwan(청년), nminseok(내레이터), nhyunjun(청년), njinho(성인)
#   여성: ndain(발랄), nsujin(명쾌), ngaram(어린), nminyoung(성인)
# Gemini fallback 용 voice_name 도 필요하면 여기 확장.

# --- Video ---
LONGFORM_RESOLUTION = (1920, 1080)
SHORTS_RESOLUTION = (1080, 1920)
FPS = 30
AUDIO_BITRATE = "192k"

# --- Third-party binaries ---
# Windows: project-local poppler bundle. macOS/Linux: rely on `pdftoppm` on PATH
# (install via `brew install poppler` or `apt install poppler-utils`). When None,
# pdf2image falls back to PATH lookup.
import sys as _sys

_BUNDLED_POPPLER = PROJECT_ROOT / "tools" / "poppler-24.08.0" / "Library" / "bin"
if _sys.platform.startswith("win") and _BUNDLED_POPPLER.exists():
    POPPLER_BIN: Path | None = _BUNDLED_POPPLER
else:
    POPPLER_BIN = None

# --- Phase 4: YouTube upload ---
YOUTUBE_OAUTH_CLIENT_FILE = PROJECT_ROOT / "credentials" / "youtube_oauth_client.json"
YOUTUBE_TOKEN_FILE = PROJECT_ROOT / "credentials" / "youtube_token.json"
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
]
YOUTUBE_CATEGORY_ID = "28"  # Science & Technology
