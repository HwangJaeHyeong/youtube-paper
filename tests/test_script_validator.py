from src.script.validator import validate_script


def test_minimal_script_passes():
    data = {
        "paper_id": "test-001",
        "paper_title": "Test",
        "authors": ["A"],
        "venue": "arXiv",
        "metadata": {"estimated_duration_sec": 60, "target_length": "longform", "generated_at": ""},
        "script": [
            {"section": "intro", "speaker": "민재", "text": "안녕.", "emotion": "neutral", "pause_after_ms": 200},
            {"section": "outro", "speaker": "수빈", "text": "끝.", "emotion": "dry", "pause_after_ms": 0},
        ],
        "rating": {"민재": 4.0, "수빈": 3.5, "verdict": "볼만함"},
    }
    s = validate_script(data)
    assert s.paper_id == "test-001"
    assert len(s.script) == 2
