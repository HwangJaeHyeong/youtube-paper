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
CLAUDE_MODEL = "claude-opus-4-7"

# --- TTS: Gemini 2.5 (Google AI Studio) ---
# https://ai.google.dev/gemini-api/docs/speech-generation
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"

# --- TTS: CLOVA Voice Premium (Naver Cloud) ---
# https://api.ncloud-docs.com/docs/ai-naver-clovavoice-ttspremium
CLOVA_TTS_URL = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"

VOICE_CONFIG: dict[str, dict] = {
    "민재": {
        "provider": "clova",
        "speaker": "njihwan",   # 청년 남성, 활기찬
        "speed": -1,            # -5(빠름) ~ 5(느림). 쇼츠 느낌은 약간 빠르게.
        "pitch": 0,
        "volume": 0,
        "emotion_default": 0,   # 0 neutral, 1 sad, 2 happy, 3 angry
        "emotion_strength": 2,  # 0 weak, 1 normal, 2 strong
    },
    "수빈": {
        "provider": "clova",
        "speaker": "ndain",     # 성인 여성, 발랄 (쇼츠 클래식 보이스)
        "speed": -1,
        "pitch": 0,
        "volume": 0,
        "emotion_default": 0,
        "emotion_strength": 2,
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
