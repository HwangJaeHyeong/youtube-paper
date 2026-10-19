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


def test_oom_batch_is_retried_in_halves(tmp_path, monkeypatch):
    from src.tts import qwen

    sizes = []

    def fake_post(payload):
        sizes.append(len(payload["text"]))
        if len(payload["text"]) > 2:
            raise RuntimeError('Qwen TTS failed: {"error": "CUDA error: out of memory"}')
        return [t.encode() for t in payload["text"]]

    monkeypatch.setattr(qwen, "_post", fake_post)
    items = [(f"줄{i}", "민재", tmp_path / f"{i}.wav") for i in range(5)]
    qwen.QwenTTS().synthesize_many(items)

    assert sizes == [5, 2, 3, 1, 2]
    for t, _, p in items:
        assert p.read_bytes() == t.encode()


def test_long_lines_are_capped_by_characters(monkeypatch):
    from src.tts import qwen

    monkeypatch.setattr(qwen, "QWEN_TTS_BATCH_CHARS", 100)
    items = [("가" * n, "민재", None) for n in (30, 40, 50, 60, 100, 120)]
    assert [[len(t) for t, _, _ in b] for b in qwen._batches(items)] == [[30, 40], [50], [60], [100], [120]]
