"""
YouTube integration (Google Data API v3).

Reuses the Google OAuth Client ID/Secret already used for Google Sheets
(Admin -> Settings -> AI/Integrations) — same Google Cloud project, just
needs the YouTube Data API v3 enabled and these scopes added/consented:
  - https://www.googleapis.com/auth/youtube.upload
  - https://www.googleapis.com/auth/youtube.readonly

The OAuth dance itself (start/callback) lives in app/admin/routes.py,
right next to the "Connect YouTube" button — this file is what actually
does something with the token afterwards: refreshing it, uploading a
video, and pulling view/like/comment counts.
"""
import requests as _requests
from app.extensions import db
from app.utils.settings import get_setting

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
API_BASE = "https://www.googleapis.com/youtube/v3"


def get_valid_access_token(channel):
    """Refreshes the stored refresh_token for an access_token good right
    now — Google access tokens only last ~1 hour, so this is called
    before every real API call rather than trusting a cached one.
    Returns (access_token, error)."""
    creds = channel.credentials or {}
    refresh_token = creds.get("refresh_token")
    if not refresh_token:
        return None, "This YouTube channel has no refresh token saved — reconnect it from Admin -> Social Channels."

    client_id = get_setting("google_oauth_client_id")
    client_secret = get_setting("google_oauth_client_secret")
    if not client_id or not client_secret:
        return None, "Google OAuth Client ID/Secret aren't set in Admin -> Settings."

    try:
        resp = _requests.post(TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }, timeout=15)
        data = resp.json()
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach Google: {e}"

    access_token = data.get("access_token")
    if not access_token:
        return None, f"Google refresh failed: {data.get('error_description', data.get('error', 'unknown error'))}"
    return access_token, None


def upload_video(channel, video_url, title, description="", privacy_status="public", tags=None):
    """Uploads a video that's already hosted somewhere (e.g. your NEXUS
    media library or any public URL) to this channel's YouTube account,
    using Google's resumable upload protocol: (1) register the upload +
    metadata to get a one-time upload URL, then (2) stream the actual
    video bytes from video_url straight into that URL — the video never
    has to fully load into this server's memory or disk.
    Returns (youtube_video_id, error)."""
    access_token, err = get_valid_access_token(channel)
    if err:
        return None, err

    title = (title or "").strip()[:100] or "Untitled"
    metadata = {
        "snippet": {
            "title": title,
            "description": (description or "")[:5000],
            "tags": tags or [],
            "categoryId": "22",
        },
        "status": {"privacyStatus": privacy_status if privacy_status in ("public", "unlisted", "private") else "public"},
    }

    try:
        video_resp = _requests.get(video_url, stream=True, timeout=30)
        video_resp.raise_for_status()
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't download the source video from {video_url}: {e}"

    content_length = video_resp.headers.get("Content-Length")
    content_type = video_resp.headers.get("Content-Type", "video/*")

    try:
        init_resp = _requests.post(
            f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": content_type,
                **({"X-Upload-Content-Length": content_length} if content_length else {}),
            },
            json=metadata,
            timeout=20,
        )
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't start the YouTube upload session: {e}"

    if init_resp.status_code not in (200, 201):
        return None, f"YouTube rejected the upload request ({init_resp.status_code}): {init_resp.text[:400]}"

    upload_session_url = init_resp.headers.get("Location")
    if not upload_session_url:
        return None, "YouTube didn't return an upload session URL."

    try:
        put_resp = _requests.put(
            upload_session_url,
            headers={"Content-Type": content_type},
            data=video_resp.iter_content(chunk_size=1024 * 1024),
            timeout=600,
        )
    except _requests.exceptions.RequestException as e:
        return None, f"Uploading the video to YouTube failed partway through: {e}"

    if put_resp.status_code not in (200, 201):
        return None, f"YouTube rejected the video file ({put_resp.status_code}): {put_resp.text[:400]}"

    video_id = (put_resp.json() or {}).get("id")
    if not video_id:
        return None, f"Upload finished but YouTube didn't return a video id. Raw: {put_resp.text[:400]}"
    return video_id, None


def channel_video_stats(channel, max_results=10):
    """Real view/like/comment counts for this channel's most recent
    uploads. Returns (videos, error) where each video is
    {id, title, published_at, views, likes, comments, url}."""
    access_token, err = get_valid_access_token(channel)
    if err:
        return None, err
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        ch_resp = _requests.get(f"{API_BASE}/channels", headers=headers,
                                 params={"part": "contentDetails", "mine": "true"}, timeout=15).json()
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach YouTube: {e}"
    items = ch_resp.get("items") or []
    if not items:
        return None, f"YouTube didn't return a channel for this account: {ch_resp.get('error', {}).get('message', 'unknown error')}"
    uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    try:
        pl_resp = _requests.get(f"{API_BASE}/playlistItems", headers=headers, params={
            "part": "snippet", "playlistId": uploads_playlist_id, "maxResults": max(1, min(int(max_results or 10), 25)),
        }, timeout=15).json()
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach YouTube: {e}"

    video_ids = [it["snippet"]["resourceId"]["videoId"] for it in (pl_resp.get("items") or [])
                 if it.get("snippet", {}).get("resourceId", {}).get("videoId")]
    if not video_ids:
        return [], None

    try:
        stats_resp = _requests.get(f"{API_BASE}/videos", headers=headers, params={
            "part": "snippet,statistics", "id": ",".join(video_ids),
        }, timeout=15).json()
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach YouTube: {e}"

    videos = []
    for v in stats_resp.get("items") or []:
        stats = v.get("statistics", {})
        snippet = v.get("snippet", {})
        videos.append({
            "id": v["id"],
            "title": snippet.get("title"),
            "published_at": snippet.get("publishedAt"),
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "url": f"https://youtube.com/watch?v={v['id']}",
        })
    return videos, None
