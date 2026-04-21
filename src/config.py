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

VOICE_CONFIG: dict[str, dict] = {
    "민재": {
        "provider": "gemini",
        "voice_name": "Orus",
        "model": GEMINI_TTS_MODEL,
        "style_prompt": "건조하고 설명하는 톤, 살짝 느리게",
    },
    "수빈": {
        "provider": "gemini",
        "voice_name": "Aoede",
        "model": GEMINI_TTS_MODEL,
        "style_prompt": "까칠하고 의심 많은 톤, 말 빠르게",
    },
}

# --- Video ---
LONGFORM_RESOLUTION = (1920, 1080)
SHORTS_RESOLUTION = (1080, 1920)
FPS = 30
AUDIO_BITRATE = "192k"
