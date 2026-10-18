"""Verify the portable reference assets agree with the saved edit."""
import hashlib
import json
import wave
from pathlib import Path

from src.video import word_timing

ROOT = Path(__file__).resolve().parents[1] / "recipes" / "hapticraft"


def test_reference_audio_script_and_cues_agree():
    recipe = json.loads((ROOT / "recipe.json").read_text())
    ref = recipe["reference"]
    audio = ROOT / ref["audio"]
    assert hashlib.sha256(audio.read_bytes()).hexdigest() == ref["audio_sha256"]
    script = "\n".join(line["text"] for line in recipe["script"])
    assert hashlib.sha256(script.encode()).hexdigest() == ref["script_sha256"]
    words = json.loads((ROOT / ref["words"]).read_text())
    assert " ".join(w["text"] for w in words) == script.replace("\n", " ")
    with wave.open(str(audio)) as wav:
        duration = wav.getnframes() / wav.getframerate()
    assert all(0 <= w["start"] < w["end"] <= duration for w in words)
    starts = []
    for shot in recipe["shots"]:
        candidates = [w for w in words if w["line"] == shot["line"]]
        if shot["cue"] != "line start":
            candidates = [w for w in candidates if w["text"].startswith(shot["cue"])]
        assert candidates, shot
        starts.append(candidates[0]["start"])
    assert starts == sorted(starts)


def test_word_alignment_keeps_display_text_and_speech_times(tmp_path):
    data = {"script": [{"text": "HaptiCraft 18명이 7가지 상황을 체험합니다."}]}
    recognized = [
        {"text": "HaptiCraft", "start": 0.2, "end": 1.1},
        {"text": "18명이", "start": 1.2, "end": 1.8},
        {"text": "7가지", "start": 1.9, "end": 2.4},
        {"text": "상황을", "start": 2.5, "end": 2.9},
        {"text": "체험합니다.", "start": 3.0, "end": 3.8},
    ]
    words, similarity = word_timing.align_words(data, recognized)
    assert similarity == 1.0
    assert words[1]["text"] == "18명이"
    assert words[1]["start"] == 1.2
    assert words[-1]["end"] == 3.8
    output = tmp_path / "subtitles.ass"
    word_timing.build_subtitles(words, output)
    assert "18명이" in output.read_text()
    assert "열여덟" not in output.read_text()
