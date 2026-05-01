"""Naver Cloud Platform CLOVA Voice Premium wrapper.

API docs: https://api.ncloud-docs.com/docs/ai-naver-clovavoice-ttspremium
Returns MP3 bytes; we transcode to WAV via pydub so the merger stays uniform.

Resilience:
- Text sanitization for V-series voices (which 400 on "..." and some special chars)
- VS14 (unsupported emotion) -> drop emotion params and retry once
- VS26 (empty synthesized data) -> fall back to `fallback_speaker` if defined
"""
from __future__ import annotations

import re
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

_ELLIPSIS_RE = re.compile(r"\.{2,}|…+")
# CLOVA reads em-dash (—) and en-dash (–) as "마이너스". Replace with comma for natural pause.
_DASH_RE = re.compile(r"\s*[—–]\s*")


def _sanitize(text: str) -> str:
    # CLOVA V-series rejects "…" and "..." with VS26. Replace with a comma.
    text = _ELLIPSIS_RE.sub(",", text)
    # em-dash / en-dash → comma (avoid "마이너스" pronunciation).
    text = _DASH_RE.sub(", ", text)
    # Normalize stray whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _post(payload: dict) -> bytes:
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
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


class ClovaTTS(TTSProvider):
    def __init__(self) -> None:
        if not NCP_CLOVA_KEY_ID or not NCP_CLOVA_KEY:
            raise RuntimeError("NCP_CLOVA_KEY_ID / NCP_CLOVA_KEY missing in .env")

    def _try_once(self, payload: dict) -> tuple[bytes | None, str]:
        try:
            return _post(payload), ""
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return None, body

    def synthesize(self, text: str, speaker: str, out_path: Path, emotion: str = "neutral") -> Path:
        cfg = VOICE_CONFIG[speaker]
        text = _sanitize(text)
        base_payload = {
            "text": text,
            "volume": str(cfg.get("volume", 0)),
            "speed": str(cfg.get("speed", 0)),
            "pitch": str(cfg.get("pitch", 0)),
            "format": "mp3",
        }
        if cfg.get("supports_emotion", False):
            base_payload["emotion"] = str(
                CLOVA_EMOTION_MAP.get(emotion, cfg.get("emotion_default", 0))
            )
            base_payload["emotion-strength"] = str(cfg.get("emotion_strength", 1))

        attempts: list[tuple[str, dict]] = []
        attempts.append((cfg["speaker"], {**base_payload, "speaker": cfg["speaker"]}))
        if fb := cfg.get("fallback_speaker"):
            fb_payload = {k: v for k, v in base_payload.items() if k not in ("emotion", "emotion-strength")}
            fb_payload["speaker"] = fb
            attempts.append((fb, fb_payload))

        last_err = ""
        mp3_bytes: bytes | None = None
        for spk_name, payload in attempts:
            mp3_bytes, err = self._try_once(payload)
            if mp3_bytes is not None:
                if spk_name != cfg["speaker"]:
                    print(f"  [fallback] {cfg['speaker']} -> {spk_name} (VS26 text: {text[:50]!r})")
                break
            # VS14 → drop emotion and retry same speaker once
            if "VS14" in err and "emotion" in payload:
                payload.pop("emotion", None)
                payload.pop("emotion-strength", None)
                mp3_bytes, err = self._try_once(payload)
                if mp3_bytes is not None:
                    break
            last_err = err

        if mp3_bytes is None:
            raise RuntimeError(
                f"CLOVA failed for speaker={cfg['speaker']!r} (and fallback): {last_err[:300]}"
            )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        seg = AudioSegment.from_file(BytesIO(mp3_bytes), format="mp3")
        seg.export(str(out_path), format="wav")
        return out_path
