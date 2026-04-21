"""Try many CLOVA voice pairs. Skip speakers that the API rejects.

Writes WAVs into data/audio/tasty_ab/<label>_<speaker>.wav
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO

from pydub import AudioSegment

from src.config import CLOVA_TTS_URL, NCP_CLOVA_KEY, NCP_CLOVA_KEY_ID

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "audio" / "tasty_ab"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LINE_MINJAE = "안녕하세요. 오늘은 AI 역사를 완전히 바꾼 2017년 전설의 논문, Attention Is All You Need 한번 까보겠습니다."
LINE_SUBIN  = "잠깐. 이거 9년 된 논문을 지금 까자고요? 다들 외우고 다니지 않아요? 근데 뭐, 한번 봐봅시다."

# 민재 = 첫 번째 화자, 수빈 = 두 번째 화자
COMBOS = [
    ("A_V_ian_hyeri",        "vian",          "vhyeri"),
    ("B_V_daeseong_ara",     "vdaeseong",     "vara"),
    ("C_V_donghyun_goeun",   "vdonghyun",     "vgoeun"),
    ("D_V_daeseong_yuna",    "vdaeseong",     "vyuna"),
    ("E_nes_noah_sohyun",    "nes_c_noah",    "nes_c_sohyun"),
    ("F_nes_kihyo_mikyung",  "nes_c_kihyo",   "nes_c_mikyung"),
    ("G_N_minseok_minjeong", "nminseok",      "nminjeong"),
    ("H_N_wontak_dain",      "nwontak",       "ndain"),
    ("I_N_jinho_sujin",      "njinho",        "nsujin"),
    ("J_N_tiffany_bora",     "nminseok",      "ntiffany"),  # 수빈에 ntiffany
    ("K_mix_vian_dain",      "vian",          "ndain"),
    ("L_mix_wontak_hyeri",   "nwontak",       "vhyeri"),
]


def synth(speaker: str, text: str, out_wav: Path, speed: int = -1, pitch: int = 1) -> tuple[bool, str]:
    payload = {
        "speaker": speaker,
        "text": text,
        "volume": "0",
        "speed": str(speed),
        "pitch": str(pitch),
        "format": "mp3",
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
        with urllib.request.urlopen(req, timeout=30) as r:
            mp3_bytes = r.read()
        seg = AudioSegment.from_file(BytesIO(mp3_bytes), format="mp3")
        seg.export(str(out_wav), format="wav")
        return True, "OK"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:100]
        return False, f"{e.code} {body}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main() -> None:
    for label, m_speaker, s_speaker in COMBOS:
        print(f"\n[{label}]  민재={m_speaker}  수빈={s_speaker}")
        m_out = OUT_DIR / f"{label}_minjae_{m_speaker}.wav"
        s_out = OUT_DIR / f"{label}_subin_{s_speaker}.wav"
        ok_m, msg_m = synth(m_speaker, LINE_MINJAE, m_out)
        print(f"  민재: {'✓' if ok_m else '✗'} {msg_m}")
        ok_s, msg_s = synth(s_speaker, LINE_SUBIN, s_out)
        print(f"  수빈: {'✓' if ok_s else '✗'} {msg_s}")


if __name__ == "__main__":
    main()
