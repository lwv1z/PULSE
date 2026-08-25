"""
youtube_publish.py — real Data API v3 upload flow (google-api-python-client).

NOT executed in this sandbox: no network path to googleapis.com here, and
no OAuth credentials exist for your channel. This is production-ready code
to run on your own deployment (e.g. the Railway service — see README).

One-time setup (~15 min):
  1. Google Cloud Console -> new project -> enable "YouTube Data API v3".
  2. Create OAuth 2.0 credentials (Desktop app) -> download client_secret.json.
  3. Run this file's `authorize()` once, locally, to produce token.json
     (opens a browser, you approve your own channel).
  4. IMPORTANT: uploads from an unaudited API project publish as PRIVATE
     by default. For public Shorts you request a compliance audit from
     Google (Cloud Console -> API compliance). This is normal, documented,
     and routine for a single-owner channel — budget a few days for it,
     not weeks. Until it's approved, videos land as private/unlisted and
     you flip them public by hand, which is a fine interim workflow.
  5. Quota: uploads bill to their own ~100/day bucket (separate from the
     10,000-unit pool as of the June 2026 change), so this comfortably
     covers a 2-a-day cadence.
"""
import os

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def authorize(client_secret_path="client_secret.json", token_path="token.json"):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials

    if os.path.exists(token_path):
        return Credentials.from_authorized_user_file(token_path, SCOPES)
    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    return creds


def upload_short(video_path: str, title: str, description: str, tags: list,
                  privacy_status="private", client_secret_path="client_secret.json",
                  token_path="token.json"):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = authorize(client_secret_path, token_path)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": "22",
        },
        "status": {"privacyStatus": privacy_status, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
    return response  # contains "id" -> https://youtu.be/{id}
