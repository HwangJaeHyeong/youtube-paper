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

from src.config import QWEN_TTS_BATCH, QWEN_TTS_URL, VOICE_CONFIG
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
            for i in range(0, len(mine), QWEN_TTS_BATCH):
                chunk = mine[i : i + QWEN_TTS_BATCH]
                wavs = _post({**voice, "text": [t for t, _, _ in chunk]})
                for (_, _, path), wav in zip(chunk, wavs):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(wav)
