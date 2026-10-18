"""Build a paper short from its portable recipe and frozen speech, without API calls."""

import argparse, hashlib, io, json, re, sys, subprocess
import fitz
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageOps
from pydub import AudioSegment
from src.video import composer, title_card, word_timing as sync


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", required=True, type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--work-dir", type=Path, default=Path("data/build-paper-short"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    recipe_path = args.recipe.resolve()
    recipe_dir = recipe_path.parent
    data = json.loads(recipe_path.read_text(encoding="utf-8"))
    ref = data["reference"]
    ROOT = args.work_dir.resolve()
    ROOT.mkdir(parents=True, exist_ok=True)
    OUT = (args.output or Path("data/videos") / (data["slug"] + "-shorts-1.2x.mp4")).resolve()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    if digest(args.pdf) != data["paper"]["sha256"]:
        parser.error("PDF checksum mismatch: use the PDF recorded by this recipe.")
    script_hash = hashlib.sha256("\n".join(l["text"] for l in data["script"]).encode()).hexdigest()
    if script_hash != ref["script_sha256"]:
        parser.error("Script changed: regenerate reference speech and word timings together.")
    source_audio = recipe_dir / ref["audio"]
    if digest(source_audio) != ref["audio_sha256"]:
        parser.error("Reference audio checksum mismatch.")
    if digest(recipe_dir / ref["words"]) != ref["words_sha256"]:
        parser.error("Word timing checksum mismatch.")
    words = json.loads((recipe_dir / ref["words"]).read_text(encoding="utf-8"))
    if [w["text"] for w in words] != [t for l in data["script"] for t in l["text"].split()]:
        parser.error("Word timings do not match the script.")
    import shutil

    shutil.copy2(source_audio, ROOT / "narration-1.2x.wav")
    originals = ROOT / "originals"
    originals.mkdir(exist_ok=True)
    with fitz.open(args.pdf) as doc:
        if len(doc) != data["paper"]["expected_pages"]:
            parser.error("Unexpected PDF page count.")
        for number, figure in data["figures"].items():
            image = doc[figure["page"] - 1].get_image_info(xrefs=True)[figure["image_index"]]
            payload = doc.extract_image(image["xref"])
            Image.open(io.BytesIO(payload["image"])).convert("RGB").save(
                originals / f"fig{number}.png"
            )
    layout = data.get("layout", {})
    similarity = 1.0
    audio = ROOT / "narration-1.2x.wav"
    duration = len(AudioSegment.from_wav(audio)) / 1000
    ass = ROOT / "captions.ass"
    sync.build_subtitles(words, ass)
    s = (
        ass.read_text()
        .replace("Pretendard Black,78,", f"Pretendard Black,{layout.get('caption_font_size', 88)},")
        .replace(r"\pos(540,1380)", r"\pos(540," + str(layout.get("caption_y", 1320)) + ")")
        .replace(
            r"\fad(20,0)\fscx95\fscy95\t(0,60,\fscx100\fscy100)",
            r"\fad(30,0)\fscx80\fscy80\t(0,110,\fscx100\fscy100)",
        )
    )
    ass.write_text(s, encoding="utf-8")
    specs = data["shots"]
    shots = []
    crops = ROOT / "crops"
    crops.mkdir(exist_ok=True)
    for i, spec in enumerate(specs):
        line, cue, fig, rect = spec["line"], spec.get("cue"), spec["figure"], spec.get("rect")
        candidates = [
            w
            for w in words
            if w["line"] == line
            and (
                not cue
                or re.sub(r"[^가-힣a-zA-Z0-9]", "", w["text"])
                .lower()
                .startswith(re.sub(r"[^가-힣a-zA-Z0-9]", "", cue).lower())
            )
        ]
        if not candidates:
            parser.error(f"Shot cue not found: line={line}, cue={cue!r}")
        start = max(0, candidates[0]["start"] - 0.04) if i else 0
        art = Image.open(ROOT / "originals" / f"fig{fig}.png").convert("RGB")
        if rect:
            art = art.crop(
                tuple(
                    round(v * (art.width if j % 2 == 0 else art.height)) for j, v in enumerate(rect)
                )
            )
        x0, y0, x1, y1 = layout.get("figure_box", [0, 500, 1080, 1250])
        fitted = ImageOps.contain(art, (x1 - x0, y1 - y0), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (1080, 1920), (20, 22, 30))
        canvas.paste(
            fitted, (x0 + (x1 - x0 - fitted.width) // 2, y0 + (y1 - y0 - fitted.height) // 2)
        )
        path = crops / f"shot_{i:02}.png"
        canvas.save(path)
        shots.append({"line": line, "cue": cue, "figure": fig, "start": start, "path": str(path)})
    segments = []
    for i, shot in enumerate(shots):
        end = shots[i + 1]["start"] if i + 1 < len(shots) else duration
        frames = round(end * 30) - round(shot["start"] * 30)
        if frames <= 0:
            parser.error("Shots must be ordered by increasing speech time.")
        segments.append((Path(shot["path"]), frames / 30))
    (ROOT / "sync-manifest.json").write_text(
        json.dumps(
            {"duration": duration, "similarity": similarity, "shots": shots},
            ensure_ascii=False,
            indent=2,
        )
    )
    header = crops / "__HEADER__.png"
    footer = crops / "__FOOTER__.png"
    title_card.render_header_strip(data["title_hook"], header, width=1080)
    title_card.render_footer_strip("다음 논문은 **댓글**로 추천 받아요", footer, width=1080)
    print("Rendering", duration, "seconds; alignment", similarity, flush=True)
    base = ROOT / "base.mp4"
    composer.compose_shorts(
        audio,
        ass,
        [],
        segments,
        base,
        header_png=header,
        footer_png=footer,
        font_dir=Path(__file__).resolve().parent.parent / "assets/fonts",
    )
    demo_info = data.get("intro_demo", {})
    demo = recipe_dir / demo_info.get("path", "__no_demo__")
    if demo_info:
        if not demo.is_file() or digest(demo) != demo_info["sha256"]:
            parser.error("Demo clip is missing or its checksum does not match.")
        end = next(s["start"] for s in shots if s["line"] == demo_info["end_line"])
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(base),
                "-stream_loop",
                "-1",
                "-i",
                str(demo),
                "-filter_complex",
                f"[1:v]scale=950:660:force_original_aspect_ratio=decrease,pad=950:660:(ow-iw)/2:(oh-ih)/2:color=0x14161e,setsar=1[d];[0:v][d]overlay=65:555:enable='lt(t,{end:.3f})'[v]",
                "-map",
                "[v]",
                "-map",
                "0:a",
                "-t",
                str(duration),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "20",
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
                str(OUT),
            ],
            check=True,
        )
    else:
        import shutil

        shutil.copy2(base, OUT)
    print("DONE", OUT, flush=True)


if __name__ == "__main__":
    main()
