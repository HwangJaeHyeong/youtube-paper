"""Upload the final HaptiCraft figure-only edit publicly to the default channel."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.discovery import build

from src.config import DATA_DIR, VIDEOS_DIR
from src.upload.youtube import _load_credentials, upload

VIDEO = VIDEOS_DIR / "hapticraft-standard-shorts-figures-only-1.2x.mp4"
RECEIPT = DATA_DIR / "raw" / "hapticraft-public-upload.json"
TITLE = "VR 컨트롤러를 조립한다고? (POSTECH + KOREATECH HaptiCraft)"
DESCRIPTION = """블록처럼 조립해 모양과 촉감을 바꾸는 VR 컨트롤러, HaptiCraft.
진동·충격·온도·가변 관성·가변 강성을 조합하는 방식과 실제 사용 예시, 무게와 그립감의 한계를 소개합니다.

논문: HaptiCraft: A Modular Multimodal Haptic Controller for Immersive Virtual Reality Interactions
저자: Chaeyong Park, Jeongwoo Kim, Yuk-Gwon Song, Sang-Youn Kim, Seungmoon Choi
게재: IEEE Transactions on Visualization and Computer Graphics, 32(7), 6493–6506 (2026)
원문: https://doi.org/10.1109/TVCG.2026.3683951
프로젝트: https://axis.korea.ac.kr/publications/2026_TVCG_HaptiCraft

영상의 그림은 논문 Figure에서 발췌했습니다. 한국어 AI 내레이션으로 소개합니다.

#HaptiCraft #VR #햅틱 #HCI #논문리뷰
"""


def main():
    if not VIDEO.exists():
        raise FileNotFoundError(VIDEO)
    if RECEIPT.exists():
        raise RuntimeError(f"Upload receipt already exists; inspect before uploading again: {RECEIPT}")
    video_id = upload(
        VIDEO, TITLE, DESCRIPTION,
        ["HaptiCraft", "VR", "햅틱", "Haptics", "HCI", "논문리뷰", "POSTECH", "KOREATECH", "IEEE TVCG", "Shorts"],
        privacy_status="public", is_shorts=True,
    )
    receipt = {
        "video_id": video_id,
        "url": f"https://www.youtube.com/shorts/{video_id}",
        "video_path": str(VIDEO),
        "requested_privacy": "public",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+"\n")
    youtube = build("youtube", "v3", credentials=_load_credentials())
    result = youtube.videos().list(part="snippet,status,contentDetails,processingDetails", id=video_id).execute()
    receipt["verified_response"] = result
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
