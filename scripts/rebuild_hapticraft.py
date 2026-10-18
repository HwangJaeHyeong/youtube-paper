"""Rebuild the published HaptiCraft edit from a fresh clone, without API calls."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path, help="Original 14-page HaptiCraft PDF")
    parser.add_argument("--work-dir", type=Path, help="Optional data directory; can be completely empty")
    parser.add_argument("--output-dir", type=Path, help="Optional directory for the final MP4")
    args = parser.parse_args()
    if args.work_dir:
        os.environ["DATA_DIR"] = str(args.work_dir.resolve())

    import fitz
    from PIL import Image

    from scripts import rebuild_hapticraft_standard as renderer
    from src.config import AUDIO_DIR, SCRIPTS_DIR

    recipe_dir = PROJECT/"recipes"/"hapticraft"
    recipe = json.loads((recipe_dir/"recipe.json").read_text(encoding="utf-8"))
    reference = recipe["reference"]
    script_hash = hashlib.sha256("\n".join(l["text"] for l in recipe["script"]).encode()).hexdigest()
    if script_hash != reference["script_sha256"]:
        parser.error("The script changed; reference speech would not match. Restore the published recipe.")
    audio = recipe_dir/reference["audio"]
    if hashlib.sha256(audio.read_bytes()).hexdigest() != reference["audio_sha256"]:
        parser.error("Reference audio checksum mismatch. Restore it from GitHub.")
    for binary in ("ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            parser.error(f"Install {binary} and put it on PATH")

    source_root = AUDIO_DIR/"hapticraft-paper-shorts"
    originals, crops = source_root/"originals", source_root/"crops"
    originals.mkdir(parents=True, exist_ok=True)
    crops.mkdir(exist_ok=True)
    images = {}
    with fitz.open(args.pdf) as doc:
        title = "".join(doc[0].get_text().split()).lower()
        if len(doc) != recipe["paper"]["expected_pages"] or "hapticraft" not in title:
            parser.error("This recipe requires the original 14-page HaptiCraft paper")
        for number, figure in recipe["figures"].items():
            page = doc[figure["page"]-1]
            info = page.get_image_info(xrefs=True)[figure["image_index"]]
            payload = doc.extract_image(info["xref"])
            image = Image.open(io.BytesIO(payload["image"])).convert("RGB")
            # This stable PNG content is saved as JPEG only for the two legacy
            # renderer lookup paths. Use the original JPEG bytes when available.
            target = originals/f"fig{number}.jpeg"
            if payload["ext"] in ("jpeg", "jpg"):
                target.write_bytes(payload["image"])
            else:
                image.save(target, quality=100, subsampling=0)
            images[number] = image
    manifest = {"pdf": args.pdf.name, "panels": {}}
    for name, panel in recipe["panels"].items():
        image = images[str(panel["figure"])]
        box = tuple(round(v*(image.width if i%2 == 0 else image.height)) for i,v in enumerate(panel["rect"]))
        if not (0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height):
            parser.error(f"Invalid source crop: {name}")
        path = crops/f"{name}.png"
        image.crop(box).save(path)
        manifest["panels"][name] = {"path": str(path), "source_size": list(image.size), "crop_pixels": box}
    (source_root/"crop-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    root = AUDIO_DIR/recipe["slug"]
    root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(audio, root/"narration-1.2x.wav")
    words = json.loads((recipe_dir/reference["words"]).read_text(encoding="utf-8"))
    if " ".join(w["text"] for w in words) != " ".join(l["text"] for l in recipe["script"]):
        parser.error("Reference word timings do not match the script")
    annotations = [{"type": "word_info", "text": w["text"], "start_offset": f"{w['start']}s",
                    "end_offset": f"{w['end']}s"} for w in words]
    (root/"transcription-response.json").write_text(json.dumps({"annotations": annotations}, ensure_ascii=False), encoding="utf-8")
    timeline = AUDIO_DIR/"hapticraft-puck-sync-shorts"
    timeline.mkdir(parents=True, exist_ok=True)
    shots = [{"line": s["line"], "cue": s["cue"], "keys": s["panels"]} for s in recipe["shots"]]
    (timeline/"sync-manifest.json").write_text(json.dumps({"shots": shots}), encoding="utf-8")
    data = {"paper_id": recipe["slug"], "paper_title": recipe["paper"]["title"],
            "title_hook": recipe["title_hook"], "script": recipe["script"],
            "metadata": {"official_url": recipe["paper"]["official_url"], "target_length": "shorts"}}
    (SCRIPTS_DIR/f"{recipe['slug']}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.output_dir:
        renderer.VIDEOS_DIR = args.output_dir.resolve()
        renderer.VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    renderer.main()


if __name__ == "__main__":
    main()
