"""Update thumbnails of all already-uploaded shorts on the default channel.

Lists channel's recent uploads, matches each to a local mp4 by title keyword,
extracts first frame, and calls thumbnails.set.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import VIDEOS_DIR  # noqa: E402
from src.upload.youtube import _load_credentials  # noqa: E402


def main() -> None:
    creds = _load_credentials(None)
    yt = build("youtube", "v3", credentials=creds)

    # Get channel uploads playlist
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    videos = []
    page = None
    while True:
        r = yt.playlistItems().list(
            part="snippet,contentDetails", playlistId=uploads, maxResults=50, pageToken=page
        ).execute()
        for it in r["items"]:
            videos.append({
                "id": it["contentDetails"]["videoId"],
                "title": it["snippet"]["title"],
                "publishedAt": it["contentDetails"].get("videoPublishedAt", ""),
            })
        page = r.get("nextPageToken")
        if not page:
            break

    # Filter to published only (videoPublishedAt exists)
    live = [v for v in videos if v["publishedAt"]]
    print(f"{len(live)} live videos found.", flush=True)

    # Match each live video to a local mp4 by looking up arxiv-id-shaped slugs in title
    mp4s = {p.stem: p for p in VIDEOS_DIR.glob("*-shorts.mp4")}

    for v in live:
        # Extract mp4 by trying to find arxiv id in VIDEOS_DIR that corresponds to this title
        # Simpler: try each mp4 and see which video details match. Actually just iterate mp4s
        # and try reverse match by title keyword.
        match: Path | None = None
        title_low = v["title"].lower()
        for stem, p in mp4s.items():
            # stem is like "1207.0580-shorts"
            arxiv_id = stem.replace("-shorts", "")
            # Try title keywords
            if arxiv_id in title_low:
                match = p; break
        if not match:
            # Try keyword match from our known hook phrases
            hooks = {
                "dropout": "1207.0580-shorts",
                "batch norm": "1502.03167-shorts",
                "adam": "1412.6980-shorts",
                "resnet": "1512.03385-shorts",
                "residual": "1512.03385-shorts",
                "transformer": "1706.03762-shorts",
                "word2vec": "1301.3781-shorts",
                "단어 뺄셈": "1301.3781-shorts",
                "seq2seq": "1409.3215-shorts",
                "bahdanau": "1409.0473-shorts",
                "vae": "1312.6114-shorts",
                "vgg": "1409.1556-shorts",
                "inception": "1409.4842-shorts",
                "dcgan": "1511.06434-shorts",
                "faster r-cnn": "1506.01497-shorts",
                "yolo": "1506.02640-shorts",
            }
            for kw, stem in hooks.items():
                if kw in title_low and stem in mp4s:
                    match = mp4s[stem]; break
        if not match:
            print(f"  SKIP  {v['id']}  {v['title'][:50]}  (no local mp4)")
            continue

        thumb = Path(tempfile.gettempdir()) / f"thumb_{v['id']}.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "1.0", "-i", str(match),
             "-frames:v", "1", "-q:v", "2", str(thumb)],
            check=True, capture_output=True,
        )
        try:
            yt.thumbnails().set(
                videoId=v["id"],
                media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg"),
            ).execute()
            print(f"  OK    {v['id']}  {match.name}")
        except Exception as e:
            print(f"  FAIL  {v['id']}  {e}")


if __name__ == "__main__":
    main()
