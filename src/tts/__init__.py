"""TTS provider dispatcher. Routes each line to the provider set in VOICE_CONFIG."""
from __future__ import annotations

from pathlib import Path

from src.config import VOICE_CONFIG
from src.tts.base import TTSProvider

_instances: dict[str, TTSProvider] = {}


def _get(provider: str) -> TTSProvider:
    if provider in _instances:
        return _instances[provider]
    if provider == "clova":
        from src.tts.clova import ClovaTTS
        _instances[provider] = ClovaTTS()
    elif provider == "gemini":
        from src.tts.gemini import GeminiTTS
        _instances[provider] = GeminiTTS()
    elif provider == "edge":
        from src.tts.edge import EdgeTTS
        _instances[provider] = EdgeTTS()
    else:
        raise ValueError(f"unknown TTS provider: {provider!r}")
    return _instances[provider]


def synthesize(text: str, speaker: str, out_path: Path, emotion: str = "neutral") -> Path:
    cfg = VOICE_CONFIG[speaker]
    provider = _get(cfg["provider"])
    # ClovaTTS accepts an emotion kwarg; GeminiTTS does not yet.
    try:
        return provider.synthesize(text, speaker, out_path, emotion=emotion)  # type: ignore[call-arg]
    except TypeError:
        return provider.synthesize(text, speaker, out_path)
