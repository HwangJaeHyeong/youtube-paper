"""FFmpeg video assembly with per-line page selection.

Each script line maps to a specific paper page (via visual_ref → figure index).
The video shows that page for exactly the line's audio duration + pause.
ASS subtitles with per-speaker color are overlaid throughout.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from pydub import AudioSegment

from src.config import AUDIO_BITRATE, FPS, LONGFORM_RESOLUTION, SHORTS_RESOLUTION
from src.video.figure_indexer import resolve_visual_ref


def _escape_filter_path(p: Path) -> str:
    return str(p.resolve()).replace("\\", "/").replace(":", "\\:")


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed:\n{e.stderr[-2000:]}") from None


def _build_segments(
    script_lines: list[dict],
    wavs: list[Path],
    pages: list[Path],
    figure_index: dict[str, int],
    fallback_page: int = 1,
) -> list[tuple[Path, float]]:
    """Return [(page_png, duration_sec), ...] aligned with the merged audio."""
    segs: list[tuple[Path, float]] = []
    current_page_idx: int | None = None
    pending_duration = 0.0
    for line, wav in zip(script_lines, wavs):
        audio_sec = len(AudioSegment.from_file(wav)) / 1000.0
        pause_sec = int(line.get("pause_after_ms", 0)) / 1000.0
        line_dur = audio_sec + pause_sec
        page_idx = resolve_visual_ref(line.get("visual_ref"), figure_index, fallback_page)
        page_idx = max(1, min(page_idx, len(pages)))
        if page_idx == current_page_idx:
            # Accumulate consecutive same-page lines into one segment
            pending_duration += line_dur
        else:
            if current_page_idx is not None:
                segs.append((pages[current_page_idx - 1], pending_duration))
            current_page_idx = page_idx
            pending_duration = line_dur
    if current_page_idx is not None:
        segs.append((pages[current_page_idx - 1], pending_duration))
    return segs


def _write_concat_list(segments: list[tuple[Path, float]], out_txt: Path) -> None:
    """FFmpeg concat demuxer list file."""
    lines = []
    for path, dur in segments:
        lines.append(f"file '{str(path.resolve()).replace(chr(92), '/')}'")
        lines.append(f"duration {dur:.3f}")
    # concat demuxer quirk: repeat last file once without duration
    last_path = segments[-1][0]
    lines.append(f"file '{str(last_path.resolve()).replace(chr(92), '/')}'")
    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _compose(
    audio_mp3: Path,
    ass_file: Path,
    segments: list[tuple[Path, float]],
    out_mp4: Path,
    width: int,
    height: int,
    header_png: Path | None = None,
) -> Path:
    """filter_complex-based concat: one input per segment, scaled+padded, concatenated.

    Reliable pix_fmt and duration handling vs. the concat-demuxer approach.
    """
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    inputs: list[str] = []
    for img, dur in segments:
        inputs += [
            "-loop", "1",
            "-framerate", str(FPS),
            "-t", f"{dur:.3f}",
            "-i", str(img),
        ]

    # 88% inner area gives a comfortable margin around figures.
    # Title card (__TITLE__.png) gets full frame so the headline reads at edge-to-edge.
    inner_w = int(width * 0.88)
    inner_h = int(height * 0.88)
    parts: list[str] = []
    for i, (img, _dur) in enumerate(segments):
        is_title = img.name == "__TITLE__.png"
        sw, sh = (width, height) if is_title else (inner_w, inner_h)
        parts.append(
            f"[{i}:v]scale={sw}:{sh}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x14161e,"
            f"setsar=1,fps={FPS},format=yuv420p[v{i}]"
        )
    concat_refs = "".join(f"[v{i}]" for i in range(len(segments)))
    parts.append(f"{concat_refs}concat=n={len(segments)}:v=1:a=0[vc]")

    # Optional header overlay: appears after the first (title) segment ends.
    extra_inputs: list[str] = []
    if header_png and header_png.exists():
        title_dur = segments[0][1] if segments else 0.0
        header_idx = len(segments) + 1  # +1 because audio is len(segments) input
        extra_inputs = ["-i", str(header_png)]
        parts.append(
            f"[vc][{header_idx}:v]overlay=x=(W-w)/2:y=140:enable='gte(t,{title_dur:.3f})'[vh]"
        )
        parts.append(f"[vh]subtitles='{_escape_filter_path(ass_file)}'[vout]")
    else:
        parts.append(f"[vc]subtitles='{_escape_filter_path(ass_file)}'[vout]")

    filter_graph = ";".join(parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", str(audio_mp3),
        *extra_inputs,
        "-filter_complex", filter_graph,
        "-map", "[vout]",
        "-map", f"{len(segments)}:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        "-shortest", "-movflags", "+faststart",
        str(out_mp4),
    ]
    _run(cmd)
    return out_mp4


def compose_shorts(
    audio_mp3: Path,
    ass_file: Path,
    pages: list[Path],
    segments: list[tuple[Path, float]],
    out_mp4: Path,
    header_png: Path | None = None,
) -> Path:
    w, h = SHORTS_RESOLUTION
    return _compose(audio_mp3, ass_file, segments, out_mp4, w, h, header_png=header_png)


def compose_longform(
    audio_mp3: Path,
    ass_file: Path,
    pages: list[Path],
    segments: list[tuple[Path, float]],
    out_mp4: Path,
) -> Path:
    w, h = LONGFORM_RESOLUTION
    return _compose(audio_mp3, ass_file, segments, out_mp4, w, h)


def build_segments(
    script_lines: list[dict],
    wavs: list[Path],
    pages: list[Path],
    figure_index: dict[str, int],
) -> list[tuple[Path, float]]:
    """Public helper for pipeline.py to pre-compute (page, duration) segments."""
    return _build_segments(script_lines, wavs, pages, figure_index)


def build_segments_v2(
    script_lines: list[dict],
    wavs: list[Path],
    pages: list[Path],
    figure_index: dict[str, int],
    crops: dict[str, Path],
    fallback_img: Path | None = None,
) -> list[tuple[Path, float]]:
    """Like build_segments but prefer cropped Figure/Table images when available.

    Each line's visual_ref is normalized (e.g. 'Figure 1'); if a corresponding
    cropped PNG exists in `crops`, that image is shown for the line's duration.
    Lines without visual_ref use `fallback_img` (typically a clean title card)
    so the arXiv header / raw paper page is never shown.
    """
    from src.video.figure_cropper import normalize_ref
    fallback = fallback_img or (pages[0] if pages else None)
    segs: list[tuple[Path, float]] = []
    current_img: Path | None = None
    pending = 0.0
    for line, wav in zip(script_lines, wavs):
        audio_sec = len(AudioSegment.from_file(wav)) / 1000.0
        pause_sec = int(line.get("pause_after_ms", 0)) / 1000.0
        dur = audio_sec + pause_sec

        ref = normalize_ref(line.get("visual_ref"))
        img: Path | None = crops.get(ref) if ref else None
        if img is None:
            img = fallback

        if img == current_img:
            pending += dur
        else:
            if current_img is not None:
                segs.append((current_img, pending))
            current_img = img
            pending = dur
    if current_img is not None:
        segs.append((current_img, pending))
    return segs
