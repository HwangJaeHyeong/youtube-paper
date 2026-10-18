"""Minimal Qwen3-TTS (Base, voice clone) HTTP server.

POST /tts  {"text": [...], "language": "Korean",
            "ref_audio": <base64 audio file>, "ref_ext": ".mp3", "ref_text": "<transcript>"}
        -> {"wavs": [base64 WAV, ...]}   (one batched forward pass per request)
"""
import base64
import hashlib
import io
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import librosa
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

try:
    import flash_attn  # noqa: F401
    ATTN = "flash_attention_2"
except ImportError:
    ATTN = "sdpa"

MODEL = Qwen3TTSModel.from_pretrained(
    os.getenv("QWEN_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-Base"),
    device_map="cuda:0",
    dtype=torch.bfloat16,
    attn_implementation=ATTN,
)
print(f"ready on {torch.cuda.get_device_name(0)} (attn={ATTN})", flush=True)

_prompts = {}  # (ref audio + transcript) hash -> clone prompt, built once per voice


def clone_prompt(req):
    raw = base64.b64decode(req["ref_audio"])
    key = hashlib.sha1(raw + req["ref_text"].encode()).hexdigest()
    if key not in _prompts:
        with tempfile.NamedTemporaryFile(suffix=req.get("ref_ext", ".wav")) as f:
            f.write(raw)
            f.flush()
            audio, sr = librosa.load(f.name, sr=None, mono=True)  # handles mp3/wav/m4a
        _prompts[key] = MODEL.create_voice_clone_prompt(ref_audio=(audio, sr), ref_text=req["ref_text"])
    return _prompts[key]


def wav_b64(wav, sr):
    buf = io.BytesIO()
    sf.write(buf, wav, sr, format="WAV")
    return base64.b64encode(buf.getvalue()).decode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # health check
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == "/shutdown":  # pipeline finished -> exit so `docker compose up` ends
            self.send_response(200)
            self.end_headers()
            return threading.Thread(target=SERVER.shutdown).start()
        if self.path != "/tts":
            return self.send_error(404)
        try:
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            wavs, sr = MODEL.generate_voice_clone(
                text=req["text"], language=req.get("language", "Korean"), voice_clone_prompt=clone_prompt(req)
            )
            body, code = json.dumps({"wavs": [wav_b64(w, sr) for w in wavs]}).encode(), 200
        except Exception as e:  # report to client instead of dropping the connection
            body, code = json.dumps({"error": f"{type(e).__name__}: {e}"}).encode(), 500
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# Single-threaded on purpose: one GPU, requests run one after another.
SERVER = HTTPServer(("0.0.0.0", 8880), Handler)
SERVER.serve_forever()
