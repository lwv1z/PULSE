"""
instagram_publish.py — real Graph API Reels flow (graph.facebook.com).

NOT executed in this sandbox: no network path to Meta's API here, and no
app/token for your account. Production-ready code for your own deployment.

One-time setup:
  - Instagram account must be a Business or Creator account, linked to a
    Facebook Page (personal accounts get zero API access to Reels).
  - Register a Meta developer app, add "Instagram Graph API".
  - Request instagram_business_basic + instagram_business_content_publish
    permissions via Meta App Review (2-6 weeks, needs a screencast of the
    real flow) — budget for this like TikTok's audit, it's the long pole.
  - Video must be hosted at a public HTTPS URL at publish time (Meta pulls
    it, it doesn't accept raw file bytes) — the orchestrator would need to
    drop finished videos into a public bucket/CDN first.
"""
import time
import requests

GRAPH = "https://graph.facebook.com/v19.0"


def publish_reel(ig_user_id: str, access_token: str, video_public_url: str,
                  caption: str):
    # Step 1: create the container
    create = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_public_url,
            "caption": caption,
            "access_token": access_token,
        },
    )
    create.raise_for_status()
    container_id = create.json()["id"]

    # Step 2: poll until the container finishes processing
    for _ in range(30):
        status = requests.get(
            f"{GRAPH}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
        ).json()
        if status.get("status_code") == "FINISHED":
            break
        time.sleep(5)
    else:
        raise TimeoutError("Instagram container never finished processing")

    # Step 3: publish it
    publish = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
    )
    publish.raise_for_status()
    return publish.json()  # contains the published media id
