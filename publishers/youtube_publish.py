"""
youtube_publish.py — real Data API v3 upload flow (google-api-python-client).

Called from daily.py's publish_new(), which passes the actual persisted
credential paths (see orchestrator.ensure_youtube_creds) — the defaults
below are just fallbacks for running this file standalone.

IMPORTANT: uploads from an unaudited API project publish as PRIVATE by
default — that's not a bug in this code, it's YouTube enforcing it
server-side. For public Shorts, request a compliance audit from Google
(Cloud Console -> API compliance). Routine for a single-owner channel,
budget a few days for it. Until it clears, videos land private and you
flip them public by hand in Studio — daily.py already defaults to
privacy_status="private" for exactly this reason.

Quota: uploads bill to their own ~100/day bucket (separate from the
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
