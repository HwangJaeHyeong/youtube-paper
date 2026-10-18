"""Integrity of portable paper inputs and a guard against the wrong PDF."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def test_generative_agents_frozen_inputs_match_script():
    root = PROJECT / "recipes/generative-agents"
    recipe = json.loads((root / "recipe.json").read_text(encoding="utf-8"))
    ref = recipe["reference"]
    for key in ("audio", "words"):
        assert hashlib.sha256((root / ref[key]).read_bytes()).hexdigest() == ref[key + "_sha256"]
    assert (
        hashlib.sha256("\n".join(l["text"] for l in recipe["script"]).encode()).hexdigest()
        == ref["script_sha256"]
    )
    words = json.loads((root / ref["words"]).read_text(encoding="utf-8"))
    assert [(w["line"], w["text"]) for w in words] == [
        (i, t) for i, line in enumerate(recipe["script"]) for t in line["text"].split()
    ]
    assert all(0 <= w["start"] < w["end"] for w in words)
    assert all(a["start"] <= b["start"] for a, b in zip(words, words[1:]))
    demo = recipe["intro_demo"]
    assert hashlib.sha256((root / demo["path"]).read_bytes()).hexdigest() == demo["sha256"]
    for shot in recipe["shots"]:
        assert str(shot["figure"]) in recipe["figures"]
        assert any(
            w["line"] == shot["line"] and (not shot["cue"] or w["text"].startswith(shot["cue"]))
            for w in words
        )


def test_generic_builder_rejects_wrong_pdf_before_render(tmp_path):
    wrong_pdf = tmp_path / "wrong.pdf"
    wrong_pdf.write_bytes(b"This is not the reviewed paper")
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_paper_short.py"),
            "--recipe",
            str(PROJECT / "recipes/generative-agents/recipe.json"),
            "--pdf",
            str(wrong_pdf),
            "--work-dir",
            str(tmp_path / "work"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "PDF checksum mismatch" in result.stderr
    assert not (tmp_path / "work/base.mp4").exists()
