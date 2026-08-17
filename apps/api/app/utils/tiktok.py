"""
TikTok integration (TikTok for Developers — Content Posting API + Display API).

Needs a TikTok Developer app approved for the "Content Posting API" and
"Login Kit" products, with its Client Key/Secret set in Admin -> Settings.

Important, real TikTok platform requirement (not a bug in this code): to
post a video by URL (PULL_FROM_URL, used below — no re-hosting of the
raw file needed), the domain that video_url lives on must be verified in
your TikTok Developer app settings first. If posting fails with a domain
error, that's what's happening — verify your media domain in the TikTok
Developer portal.
"""
import time
import requests as _requests
from app.utils.settings import get_setting

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
PUBLISH_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
PUBLISH_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
VIDEO_LIST_URL = "https://open.tiktokapis.com/v2/video/list/"


def get_valid_access_token(channel):
    """TikTok access tokens are short-lived; refresh_token is long-lived
    (~1 year) and rotates on every refresh, so the new one is saved back
    onto the channel each time. Returns (access_token, error)."""
    creds = channel.credentials or {}
    refresh_token = creds.get("refresh_token")
    if not refresh_token:
        return None, "This TikTok channel has no refresh token saved — reconnect it from Admin -> Social Channels."

    client_key = get_setting("tiktok_client_key")
    client_secret = get_setting("tiktok_client_secret")
    if not client_key or not client_secret:
        return None, "TikTok Client Key/Secret aren't set in Admin -> Settings."

    try:
        resp = _requests.post(TOKEN_URL, data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
        data = resp.json()
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach TikTok: {e}"

    access_token = data.get("access_token")
    if not access_token:
        return None, f"TikTok refresh failed: {data.get('error_description', data.get('error', 'unknown error'))}"

    # Save the rotated refresh_token so the next refresh still works.
    if data.get("refresh_token"):
        from app.extensions import db
        channel.credentials = {**creds, "refresh_token": data["refresh_token"]}
        db.session.commit()

    return access_token, None


def post_video_from_url(channel, video_url, title="", privacy_level="SELF_ONLY"):
    """Publishes a video already hosted at video_url to this TikTok
    account. privacy_level: SELF_ONLY (private/draft — safest default so
    nothing goes live by accident), PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS,
    or FOLLOWER_OF_CREATOR. Returns (publish_id, error) — publishing
    finishes async on TikTok's side; poll check_post_status() with the id."""
    access_token, err = get_valid_access_token(channel)
    if err:
        return None, err

    payload = {
        "post_info": {
            "title": (title or "")[:150],
            "privacy_level": privacy_level,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "video_url": video_url,
        },
    }
    try:
        resp = _requests.post(PUBLISH_INIT_URL, headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }, json=payload, timeout=20)
        data = resp.json()
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach TikTok: {e}"

    error = data.get("error") or {}
    if error.get("code") and error["code"] != "ok":
        hint = ""
        if "url_ownership" in str(error.get("code", "")).lower() or "domain" in str(error.get("message", "")).lower():
            hint = " (this usually means video_url's domain isn't verified in your TikTok Developer app yet)"
        return None, f"TikTok error {error.get('code')}: {error.get('message', 'unknown')}{hint}"

    publish_id = (data.get("data") or {}).get("publish_id")
    if not publish_id:
        return None, f"TikTok accepted the request but returned no publish_id. Raw: {str(data)[:400]}"
    return publish_id, None


def check_post_status(channel, publish_id):
    """Poll after post_video_from_url — returns (status_dict, error)."""
    access_token, err = get_valid_access_token(channel)
    if err:
        return None, err
    try:
        resp = _requests.post(PUBLISH_STATUS_URL, headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }, json={"publish_id": publish_id}, timeout=15)
        data = resp.json()
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach TikTok: {e}"
    return data.get("data") or {}, None


def account_video_analytics(channel, max_results=10):
    """Real view/like/comment/share counts for this account's recent
    videos via the Display API. Returns (videos, error)."""
    access_token, err = get_valid_access_token(channel)
    if err:
        return None, err
    fields = "id,title,view_count,like_count,comment_count,share_count,share_url,create_time"
    try:
        resp = _requests.post(
            f"{VIDEO_LIST_URL}?fields={fields}",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"},
            json={"max_count": max(1, min(int(max_results or 10), 20))},
            timeout=20,
        )
        data = resp.json()
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach TikTok: {e}"

    error = data.get("error") or {}
    if error.get("code") and error["code"] != "ok":
        return None, f"TikTok error {error.get('code')}: {error.get('message', 'unknown')}"

    videos = []
    for v in (data.get("data") or {}).get("videos", []):
        videos.append({
            "id": v.get("id"),
            "title": v.get("title"),
            "views": v.get("view_count", 0),
            "likes": v.get("like_count", 0),
            "comments": v.get("comment_count", 0),
            "shares": v.get("share_count", 0),
            "url": v.get("share_url"),
            "created_at": v.get("create_time"),
        })
    return videos, None
