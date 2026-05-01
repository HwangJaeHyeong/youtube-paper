"""Microsoft Edge TTS wrapper (free, no API key)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

from src.config import VOICE_CONFIG
from src.tts.base import TTSProvider


class EdgeTTS(TTSProvider):
    def synthesize(self, text: str, speaker: str, out_path: Path) -> Path:
        cfg = VOICE_CONFIG[speaker]
        voice = cfg["voice_name"]
        rate = cfg.get("rate", "+0%")
        pitch = cfg.get("pitch", "+0Hz")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        asyncio.run(self._run(text, voice, rate, pitch, out_path))
        return out_path

    @staticmethod
    async def _run(text: str, voice: str, rate: str, pitch: str, out_path: Path) -> None:
        communicator = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        await communicator.save(str(out_path))
