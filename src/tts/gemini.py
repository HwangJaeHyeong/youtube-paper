"""Google AI Studio Gemini 2.5 TTS wrapper.

Docs: https://ai.google.dev/gemini-api/docs/speech-generation
Single-speaker mode used here for per-line synthesis (precise timestamps for subtitles).
Multi-speaker mode (one call per section with both voices) can be added in Phase 2.
"""
from __future__ import annotations

import wave
from pathlib import Path

from google import genai
from google.genai import types

from src.config import GOOGLE_API_KEY, VOICE_CONFIG
from src.tts.base import TTSProvider


class GeminiTTS(TTSProvider):
    def __init__(self) -> None:
        if not GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY missing — set it in .env")
        self.client = genai.Client(api_key=GOOGLE_API_KEY)

    def synthesize(self, text: str, speaker: str, out_path: Path) -> Path:
        cfg = VOICE_CONFIG[speaker]
        styled_text = f"{cfg['style_prompt']}: {text}"
        response = self.client.models.generate_content(
            model=cfg["model"],
            contents=styled_text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=cfg["voice_name"])
                    )
                ),
            ),
        )
        pcm = response.candidates[0].content.parts[0].inline_data.data
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_pcm_as_wav(pcm, out_path)
        return out_path


def _write_pcm_as_wav(pcm_bytes: bytes, path: Path, sample_rate: int = 24000) -> None:
    """Gemini returns raw 16-bit mono PCM; wrap it as WAV for FFmpeg to consume."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm_bytes)
