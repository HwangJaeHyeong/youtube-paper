"""Record checksums after preparing and reviewing a new paper recipe."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", required=True, type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    args = parser.parse_args()
    recipe = json.loads(args.recipe.read_text(encoding="utf-8"))
    root = args.recipe.resolve().parent

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    words = json.loads((root / recipe["reference"]["words"]).read_text(encoding="utf-8"))
    expected = [
        (i, token) for i, line in enumerate(recipe["script"]) for token in line["text"].split()
    ]
    if [(w["line"], w["text"]) for w in words] != expected:
        parser.error("Prepare word timings matching every script token and line first.")
    if not words or any(w["start"] < 0 or w["end"] <= w["start"] for w in words):
        parser.error("Word timings must have nonnegative starts and positive duration.")
    if any(a["start"] > b["start"] for a, b in zip(words, words[1:])):
        parser.error("Word timings must be ordered.")
    recipe["paper"]["sha256"] = digest(args.pdf)
    ref = recipe["reference"]
    ref["script_sha256"] = hashlib.sha256(
        "\n".join(l["text"] for l in recipe["script"]).encode()
    ).hexdigest()
    for key in ("audio", "words"):
        ref[key + "_sha256"] = digest(root / ref[key])
    if recipe.get("intro_demo"):
        demo = recipe["intro_demo"]
        demo["sha256"] = digest(root / demo["path"])
    args.recipe.write_text(
        json.dumps(recipe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("Sealed", args.recipe)


if __name__ == "__main__":
    main()
