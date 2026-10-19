"""Qwen3-TTS voice-clone client. The model runs in the Docker GPU server (docker/qwen-tts).

Start it with `docker compose up -d qwen-tts`. Each speaker clones the voice in its
`qwen_ref_audio` (transcript in `qwen_ref_text`). Lines are sent in batches
(one GPU forward pass per QWEN_TTS_BATCH lines) to keep the GPU busy.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

from src.config import QWEN_TTS_BATCH, QWEN_TTS_BATCH_CHARS, QWEN_TTS_URL, VOICE_CONFIG
from src.tts.base import TTSProvider


def _post(payload: dict) -> list[bytes]:
    req = urllib.request.Request(
        QWEN_TTS_URL, json.dumps(payload).encode(), {"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return [base64.b64decode(w) for w in json.load(r)["wavs"]]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Qwen TTS failed: {e.read().decode('utf-8', 'replace')[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Qwen TTS server ({QWEN_TTS_URL}) unreachable: {e.reason}. Run `docker compose up -d qwen-tts`"
        ) from e


class QwenTTS(TTSProvider):
    def synthesize(self, text: str, speaker: str, out_path: Path) -> Path:
        self.synthesize_many([(text, speaker, out_path)])
        return out_path

    def synthesize_many(self, items: list[tuple[str, str, Path]]) -> None:
        # One reference voice per request; similar lengths per batch -> less padding waste.
        for speaker in dict.fromkeys(spk for _, spk, _ in items):
            cfg = VOICE_CONFIG[speaker]
            if "qwen_ref_audio" not in cfg:
                raise RuntimeError(f"{speaker}: qwen_ref_audio / qwen_ref_text not set in VOICE_CONFIG")
            ref = Path(cfg["qwen_ref_audio"])
            voice = {
                "ref_audio": base64.b64encode(ref.read_bytes()).decode(),
                "ref_ext": ref.suffix,
                "ref_text": cfg["qwen_ref_text"],
                "language": cfg.get("qwen_language", "Korean"),
            }
            mine = sorted((it for it in items if it[1] == speaker), key=lambda it: len(it[0]))
            for chunk in _batches(mine):
                _send(voice, chunk)


def _batches(items: list[tuple[str, str, Path]]) -> list[list[tuple[str, str, Path]]]:
    """At most QWEN_TTS_BATCH lines and QWEN_TTS_BATCH_CHARS characters per GPU pass.

    The character cap matters for long lines: a CUDA out-of-memory error can leave the
    server's GPU context unusable, so we avoid hitting it rather than recover from it."""
    out: list[list[tuple[str, str, Path]]] = []
    for it in items:
        if out and len(out[-1]) < QWEN_TTS_BATCH and sum(len(t) for t, _, _ in out[-1]) + len(it[0]) <= QWEN_TTS_BATCH_CHARS:
            out[-1].append(it)
        else:
            out.append([it])
    return out


def _send(voice: dict, chunk: list[tuple[str, str, Path]]) -> None:
    """POST one batch; on GPU out-of-memory (long reference voice / long lines) retry in halves."""
    try:
        wavs = _post({**voice, "text": [t for t, _, _ in chunk]})
    except RuntimeError as e:
        if "out of memory" not in str(e) or len(chunk) == 1:
            raise
        half = len(chunk) // 2
        _send(voice, chunk[:half])
        _send(voice, chunk[half:])
        return
    for (_, _, path), wav in zip(chunk, wavs):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(wav)
