"""Generate a TTS sample for every CLOVA Voice Premium speaker.

Output:
    data/audio/voice_samples/<voice_id>.wav
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from pydub import AudioSegment

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import CLOVA_TTS_URL, NCP_CLOVA_KEY, NCP_CLOVA_KEY_ID, AUDIO_DIR  # noqa: E402

SAMPLE_TEXT = "오늘의 논문을 소개해보겠습니다."

# CLOVA Voice Premium 카탈로그 (2024~2025 기준).
# 일부 V-series / 특수 화자는 한도·요청 형식 다를 수 있어 실패하면 스킵.
VOICES = [
    # 표준 한국어 남성
    "njihun", "njihwan", "njinho", "nminseok", "nhyunjun", "nseohyun",
    "nseonghoon", "nyounghoon", "ntaejin", "nyoungil", "nwoosik",
    "nsangdo", "neunwoo", "nsiyoon", "nkitae", "nkyunglee",
    # 표준 한국어 여성
    "ndain", "ngaram", "ngoeun", "nhajun", "nian", "nminyoung",
    "nsujin", "nara", "njiyun", "nmijin", "nyuna", "nseonyoung",
    "nbora", "nbufmom", "nminsuh", "nshasha", "ntiffany", "njiwon",
    "nyejin",
    # V-series (감정·연기 가능)
    "vhyeri", "vmikyung", "vian", "vdain", "vgoeun", "vsinu", "vyuna",
    "vmikyung", "vdaeseong", "vhyeri",
]


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
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main() -> None:
    out_dir = AUDIO_DIR / "voice_samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    ok, fail = 0, 0
    for v in VOICES:
        if v in seen:
            continue
        seen.add(v)
        out_wav = out_dir / f"{v}.wav"
        if out_wav.exists():
            print(f"  SKIP exists  {v}", flush=True)
            continue
        payload = {
            "text": SAMPLE_TEXT,
            "speaker": v,
            "volume": "0",
            "speed": "0",
            "pitch": "0",
            "format": "mp3",
        }
        try:
            mp3 = _post(payload)
            seg = AudioSegment.from_file(BytesIO(mp3), format="mp3")
            seg.export(str(out_wav), format="wav")
            print(f"  OK    {v}", flush=True)
            ok += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:120]
            print(f"  FAIL  {v}  {e.code}: {body}", flush=True)
            fail += 1
        except Exception as e:
            print(f"  FAIL  {v}  {e}", flush=True)
            fail += 1

    print(f"\n{ok} OK, {fail} FAIL. Samples in: {out_dir}", flush=True)


if __name__ == "__main__":
    main()
