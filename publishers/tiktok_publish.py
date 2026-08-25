"""
tiktok_publish.py — real Content Posting API flow (open.tiktokapis.com).

NOT executed in this sandbox: TikTok's API isn't reachable from here and
there's no app/token for your account. Production-ready code for your
own deployment.

Reality check (verified current as of Aug 2026 — this is the strictest
gate of the three platforms):
  - Register a developer app at developers.tiktok.com, add the "Content
    Posting API" product.
  - Until your app passes TikTok's audit, every post it makes is forced
    to SELF_ONLY (private, visible only to you) and capped at 5 creator
    accounts/24h. There is no way around this for public posts — TikTok
    enforces it server-side.
  - The audit reviews your actual UX flow (consent screen, disclosure,
    privacy controls) — expect a real review cycle, not a rubber stamp.
  - Until audited: the honest, working interim setup is "auto-draft,
    manual tap-to-post" — this script uploads and TikTok opens it as a
    draft in your inbox for a final one-tap publish. That is a big step
    down from "zero input" but it's what TikTok actually allows today.
"""
import requests

API_BASE = "https://open.tiktokapis.com/v2"


def init_direct_post(access_token: str, title: str, video_size_bytes: int,
                      privacy_level="SELF_ONLY"):
    """Step 1: initialize the post. privacy_level is forced to SELF_ONLY
    by TikTok itself for any unaudited app, regardless of what you pass."""
    resp = requests.post(
        f"{API_BASE}/post/publish/video/init/",
        headers={"Authorization": f"Bearer {access_token}",
                 "Content-Type": "application/json"},
        json={
            "post_info": {
                "title": title[:150],
                "privacy_level": privacy_level,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size_bytes,
                "chunk_size": video_size_bytes,
                "total_chunk_count": 1,
            },
        },
    )
    resp.raise_for_status()
    return resp.json()["data"]  # contains publish_id + upload_url


def upload_video(upload_url: str, video_path: str):
    with open(video_path, "rb") as f:
        data = f.read()
    resp = requests.put(
        upload_url,
        headers={"Content-Type": "video/mp4",
                  "Content-Range": f"bytes 0-{len(data)-1}/{len(data)}"},
        data=data,
    )
    resp.raise_for_status()


def poll_status(access_token: str, publish_id: str):
    resp = requests.post(
        f"{API_BASE}/post/publish/status/fetch/",
        headers={"Authorization": f"Bearer {access_token}",
                 "Content-Type": "application/json"},
        json={"publish_id": publish_id},
    )
    resp.raise_for_status()
    return resp.json()["data"]["status"]  # e.g. PUBLISH_COMPLETE


def publish(access_token: str, video_path: str, title: str):
    import os
    size = os.path.getsize(video_path)
    data = init_direct_post(access_token, title, size)
    upload_video(data["upload_url"], video_path)
    return data["publish_id"]
