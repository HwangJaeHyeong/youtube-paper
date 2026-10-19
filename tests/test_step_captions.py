"""Step captions: 2-line phrases, no pop animation, each stays until the next one."""


def test_step_captions(tmp_path):
    from src.video.word_timing import build_subtitles

    words = "님들 혹시 VR 컨트롤러의 충격적인 반전을 암? 원래는 손잡이가 똑같았음".split()
    tokens = [{"text": w, "line": 0, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, w in enumerate(words)]
    out = tmp_path / "c.ass"
    n = build_subtitles(tokens, out, step=True, line_chars=10)
    events = [l for l in out.read_text(encoding="utf-8").splitlines() if l.startswith("Dialogue")]
    assert n == len(events) >= 2
    assert all(r"\fscx" not in e and r"\fad" not in e for e in events)
    assert all(r"\N" in e for e in events[:-1])
    ends = [e.split(",")[2] for e in events]
    starts = [e.split(",")[1] for e in events]
    assert ends[:-1] == starts[1:]  # no gap between phrases
