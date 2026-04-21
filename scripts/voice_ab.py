"""Generate voice A/B samples so the user can pick a pair.

Writes WAVs into data/audio/voice_ab/<combo>_<speaker>.wav.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google import genai
from google.genai import types

from src.config import GEMINI_TTS_MODEL, GOOGLE_API_KEY

from src.tts.gemini import _write_pcm_as_wav

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "audio" / "voice_ab"

LINE_MINJAE = "안녕하세요, 오늘은 2017년 레전드 논문 Attention Is All You Need 한 번 까보려고 합니다. 이게 뭐냐면요, 지금 GPT Claude 전부 이 논문 한 장에서 출발한 거거든요!"
LINE_SUBIN = "잠깐. 이거 9년 된 논문을 지금 까자고요? 다들 외우고 다니지 않아요? 뭐 얼마나 대단하길래 그래요, 한번 봅시다."

SHORTS_STYLE_M = (
    "유튜브 쇼츠 내레이터처럼 빠르고 텐션 높게. 감정 과장 OK. "
    "단조롭지 말고 문장마다 억양 팍팍 살리기. 중요한 단어는 세게 강조."
)
SHORTS_STYLE_F = (
    "유튜브 쇼츠 리액션처럼 쫀득하고 밝게. 의심·놀람·한심함 감정 팍팍. "
    "의문형은 끝음 올리기, 까칠한 멘트는 약간 툭 던지듯 빠르게."
)

COMBOS = [
    ("A_fenrir_laomedeia", "Fenrir", "Laomedeia"),
    ("B_puck_zephyr", "Puck", "Zephyr"),
    ("C_sadachbia_pulcherrima", "Sadachbia", "Pulcherrima"),
    ("D_achird_sadachbia", "Achird", "Sadachbia"),
]


def synth(client, voice: str, styled_text: str, out: Path) -> None:
    resp = client.models.generate_content(
        model=GEMINI_TTS_MODEL,
        contents=styled_text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )
    pcm = resp.candidates[0].content.parts[0].inline_data.data
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_pcm_as_wav(pcm, out)


def main() -> None:
    client = genai.Client(api_key=GOOGLE_API_KEY)
    for label, v_m, v_f in COMBOS:
        print(f"[{label}] 민재={v_m}, 수빈={v_f}", flush=True)
        synth(client, v_m, f"{SHORTS_STYLE_M}: {LINE_MINJAE}", OUT_DIR / f"{label}_minjae.wav")
        synth(client, v_f, f"{SHORTS_STYLE_F}: {LINE_SUBIN}", OUT_DIR / f"{label}_subin.wav")
    print(f"\nDone. Listen in: {OUT_DIR}")


if __name__ == "__main__":
    main()
