"""YouTube Data API v3 upload via resumable upload.

OAuth flow (installed app / desktop):
1. First run opens a browser for the user to grant `youtube.upload` scope.
2. Token is cached in YOUTUBE_TOKEN_FILE and refreshed automatically afterwards.
"""
from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.config import (
    YOUTUBE_CATEGORY_ID,
    YOUTUBE_OAUTH_CLIENT_FILE,
    YOUTUBE_SCOPES,
    YOUTUBE_TOKEN_FILE,
)


def _token_path(channel: str | None) -> Path:
    if not channel:
        return YOUTUBE_TOKEN_FILE
    return YOUTUBE_TOKEN_FILE.parent / f"youtube_token_{channel}.json"


def _load_credentials(channel: str | None = None) -> Credentials:
    token_file = _token_path(channel)
    creds: Credentials | None = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), YOUTUBE_SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not YOUTUBE_OAUTH_CLIENT_FILE.exists():
            raise RuntimeError(
                f"Missing OAuth client file at {YOUTUBE_OAUTH_CLIENT_FILE}. "
                "Download it from GCP Console → Credentials → OAuth 2.0 Client (Desktop)."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(YOUTUBE_OAUTH_CLIENT_FILE), YOUTUBE_SCOPES
        )
        creds = flow.run_local_server(port=0)
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds


def upload(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str] | None = None,
    privacy_status: str = "private",
    is_shorts: bool = False,
    channel: str | None = None,
    publish_at: str | None = None,
) -> str:
    """Upload `video_path` to the authenticated channel. Returns video id."""
    creds = _load_credentials(channel)
    youtube = build("youtube", "v3", credentials=creds)

    final_title = title
    if is_shorts and "#Shorts" not in final_title and "#shorts" not in final_title:
        final_title = f"{title} #Shorts"
    if is_shorts:
        description = f"{description}\n\n#Shorts"

    status = {
        "privacyStatus": privacy_status,
        "selfDeclaredMadeForKids": False,
    }
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at  # RFC3339, e.g. 2026-04-22T19:00:00+09:00
    body = {
        "snippet": {
            "title": final_title[:100],
            "description": description[:5000],
            "tags": (tags or [])[:30],
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": status,
    }
    media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"  uploaded {int(status.progress() * 100)}%", flush=True)
    video_id = response["id"]
    print(f"  done: https://www.youtube.com/watch?v={video_id}", flush=True)

    # Extract first frame as custom thumbnail.
    try:
        import subprocess, tempfile
        from pathlib import Path as _Path
        thumb = _Path(tempfile.gettempdir()) / f"thumb_{video_id}.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "1.0", "-i", str(video_path),
             "-frames:v", "1", "-q:v", "2", str(thumb)],
            check=True, capture_output=True,
        )
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg"),
        ).execute()
        print(f"  thumbnail set", flush=True)
    except Exception as e:
        print(f"  thumbnail skipped: {e}", flush=True)

    return video_id
