"""Naver Cloud Platform CLOVA Voice Premium wrapper.

API docs: https://api.ncloud-docs.com/docs/ai-naver-clovavoice-ttspremium
Returns MP3 bytes. We transcode to WAV via pydub so the rest of the
pipeline (pydub-based merger) handles output uniformly.
"""
from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from pydub import AudioSegment

from src.config import (
    CLOVA_EMOTION_MAP,
    CLOVA_TTS_URL,
    NCP_CLOVA_KEY,
    NCP_CLOVA_KEY_ID,
    VOICE_CONFIG,
)
from src.tts.base import TTSProvider


class ClovaTTS(TTSProvider):
    def __init__(self) -> None:
        if not NCP_CLOVA_KEY_ID or not NCP_CLOVA_KEY:
            raise RuntimeError("NCP_CLOVA_KEY_ID / NCP_CLOVA_KEY missing in .env")

    def synthesize(self, text: str, speaker: str, out_path: Path, emotion: str = "neutral") -> Path:
        cfg = VOICE_CONFIG[speaker]
        emotion_val = CLOVA_EMOTION_MAP.get(emotion, cfg.get("emotion_default", 0))
        payload = {
            "speaker": cfg["speaker"],
            "text": text,
            "volume": str(cfg.get("volume", 0)),
            "speed": str(cfg.get("speed", 0)),
            "pitch": str(cfg.get("pitch", 0)),
            "format": "mp3",
            "emotion": str(emotion_val),
            "emotion-strength": str(cfg.get("emotion_strength", 1)),
        }
        req = urllib.request.Request(
            CLOVA_TTS_URL,
            data=urllib.parse.urlencode(payload).encode(),
            headers={
                "X-NCP-APIGW-API-KEY-ID": NCP_CLOVA_KEY_ID,
                "X-NCP-APIGW-API-KEY": NCP_CLOVA_KEY,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                mp3_bytes = r.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"CLOVA {e.code} for speaker={cfg['speaker']!r} emotion={emotion_val} "
                f"strength={cfg.get('emotion_strength', 1)}: {body[:300]}"
            ) from None
        out_path.parent.mkdir(parents=True, exist_ok=True)
        seg = AudioSegment.from_file(BytesIO(mp3_bytes), format="mp3")
        seg.export(str(out_path), format="wav")
        return out_path
