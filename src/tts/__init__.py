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
    elif provider == "qwen":
        from src.tts.qwen import QwenTTS
        _instances[provider] = QwenTTS()
    elif provider == "edge":
        from src.tts.edge import EdgeTTS
        _instances[provider] = EdgeTTS()
    else:
        raise ValueError(f"unknown TTS provider: {provider!r}")
    return _instances[provider]


def synthesize_many(items: list[tuple[str, str, Path, str]]) -> None:
    """(text, speaker, out_path, emotion) 목록 합성. Qwen 화자는 GPU 배치로 한꺼번에."""
    qwen = [(t, s, p) for t, s, p, _ in items if VOICE_CONFIG[s]["provider"] == "qwen"]
    if qwen:
        _get("qwen").synthesize_many(qwen)  # type: ignore[attr-defined]
    for t, s, p, e in items:
        if VOICE_CONFIG[s]["provider"] != "qwen":
            synthesize(t, s, p, emotion=e)


def synthesize(text: str, speaker: str, out_path: Path, emotion: str = "neutral") -> Path:
    cfg = VOICE_CONFIG[speaker]
    provider = _get(cfg["provider"])
    # ClovaTTS accepts an emotion kwarg; GeminiTTS does not yet.
    try:
        return provider.synthesize(text, speaker, out_path, emotion=emotion)  # type: ignore[call-arg]
    except TypeError:
        return provider.synthesize(text, speaker, out_path)
