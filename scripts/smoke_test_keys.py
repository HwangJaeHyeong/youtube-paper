"""Quick liveness check for ANTHROPIC + GOOGLE keys using stdlib only.

Run: python scripts/smoke_test_keys.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    env = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def check_google(key: str) -> str:
    if not key:
        return "missing"
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return f"OK ({len(data.get('models', []))} models visible)"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read()[:200].decode(errors='replace')}"
    except Exception as e:
        return f"ERROR: {e}"


def check_anthropic(key: str) -> str:
    if not key:
        return "missing"
    body = json.dumps(
        {
            "model": "claude-opus-4-7",
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "Reply with one Korean word."}],
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            text = data.get("content", [{}])[0].get("text", "")
            model = data.get("model", "?")
            return f"OK (model={model}, reply={text!r})"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read()[:200].decode(errors='replace')}"
    except Exception as e:
        return f"ERROR: {e}"


def main() -> int:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    env = load_env(env_path)
    os.environ.update(env)
    print(f"GOOGLE_API_KEY   → {check_google(env.get('GOOGLE_API_KEY', ''))}")
    print(f"ANTHROPIC_API_KEY → {check_anthropic(env.get('ANTHROPIC_API_KEY', ''))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
