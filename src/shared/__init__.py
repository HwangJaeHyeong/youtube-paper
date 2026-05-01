"""Shared infrastructure for PaperCast and sibling content pipelines.

Any pipeline that wants to turn (host dialogue) -> (TTS audio + ASS subtitles + video + YouTube upload)
can depend only on this package and avoid the paper-specific modules (`src.ingest`, `src.script`,
`src.video.figure_cropper`, `src.video.figure_indexer`).

Reusable surface:
- `tts`          : per-speaker voice synthesis (CLOVA / Gemini / Edge)
- `subtitle`     : ASS builder with per-speaker color + sentence-chunked timing
- `composer`     : FFmpeg-based video assembly (shorts 1080x1920 / longform 1920x1080)
- `title_card`   : solid cover + large-centered title intro card
- `upload`       : YouTube Data API v3 upload w/ per-channel token and publishAt scheduling
- `config`       : paths, resolutions, FPS, VOICE_CONFIG, API keys
"""
from src import tts
from src.video import subtitle, composer, title_card
from src.upload import youtube as upload
from src import config

__all__ = ["tts", "subtitle", "composer", "title_card", "upload", "config"]
