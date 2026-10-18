"""Qwen batch client writes each line's audio to its own path (no server needed)."""


def test_batches_map_audio_to_right_paths(tmp_path, monkeypatch):
    from src.tts import qwen

    calls = []

    def fake_post(payload):
        calls.append(payload["text"])
        return [t.encode() for t in payload["text"]]  # echo text as "audio" to check mapping

    monkeypatch.setattr(qwen, "_post", fake_post)
    monkeypatch.setattr(qwen, "QWEN_TTS_BATCH", 2)
    texts = ["가나다라마", "가", "가나다", "가나"]
    items = [(t, "민재", tmp_path / f"{i}.wav") for i, t in enumerate(texts)]
    qwen.QwenTTS().synthesize_many(items)

    assert calls == [["가", "가나"], ["가나다", "가나다라마"]]  # sorted by length, chunked
    for t, _, p in items:
        assert p.read_bytes() == t.encode()
