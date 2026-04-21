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


def _load_credentials() -> Credentials:
    creds: Credentials | None = None
    if YOUTUBE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(YOUTUBE_TOKEN_FILE), YOUTUBE_SCOPES)
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
        YOUTUBE_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        YOUTUBE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def upload(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str] | None = None,
    privacy_status: str = "private",
    is_shorts: bool = False,
) -> str:
    """Upload `video_path` to the authenticated channel. Returns video id."""
    creds = _load_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    final_title = title
    if is_shorts and "#Shorts" not in final_title and "#shorts" not in final_title:
        final_title = f"{title} #Shorts"
    if is_shorts:
        description = f"{description}\n\n#Shorts"

    body = {
        "snippet": {
            "title": final_title[:100],  # YouTube 100자 제한
            "description": description[:5000],
            "tags": (tags or [])[:30],
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": privacy_status,  # "private" | "unlisted" | "public"
            "selfDeclaredMadeForKids": False,
        },
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
    return video_id
