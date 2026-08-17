"""
app/utils/ayrshare.py
======================
Direct social publishing through Ayrshare instead of a raw Meta Graph API
integration. The reason this exists: posting to Facebook/Instagram directly
via Meta's API requires YOU to register a Facebook Developer App and get it
reviewed — that's a Meta platform rule, not something any code can route
around. Ayrshare (and similar services) already have an approved Meta app;
you link your Facebook Page / Instagram Business account inside Ayrshare's
own dashboard (a normal "Connect Facebook" button on their site, no App
Review needed on your end), then give this platform just one Ayrshare API
key. Everything after that is one simple API call.

Setup the user needs to do themselves (cannot be automated from here):
  1. Sign up at https://www.ayrshare.com
  2. In their dashboard, connect Facebook Page / Instagram Business / etc.
  3. Copy the API Key from their dashboard into Admin -> Settings ->
     Direct Social Publishing -> Ayrshare API Key.

NOTE: this wraps Ayrshare's REST API as documented as of this build. Ayrshare
occasionally changes response field names — if a call starts failing with a
parsing error rather than an auth/platform error, check their current API
docs at https://docs.ayrshare.com before assuming the integration is broken.
"""
import requests

AYRSHARE_POST_URL = "https://api.ayrshare.com/api/post"
VALID_PLATFORMS = ("facebook", "instagram", "twitter", "linkedin", "tiktok", "youtube", "pinterest", "reddit")


def post_to_ayrshare(api_key, message, platforms, media_urls=None, schedule_date=None):
    """Publish a post to one or more platforms via Ayrshare.

    Args:
        api_key: the user's Ayrshare API key (from Settings).
        message: post text.
        platforms: list of platform strings, e.g. ["facebook", "instagram"].
        media_urls: optional list of public image/video URLs to attach.
        schedule_date: optional ISO 8601 UTC datetime string to schedule
            instead of posting immediately.

    Returns: (result_dict or None, error_message or None)
    """
    if not api_key:
        return None, "No Ayrshare API key set — add one in Admin -> Settings -> Direct Social Publishing."
    if not message or not message.strip():
        return None, "Nothing to post — enter some text."
    platforms = [p for p in (platforms or []) if p in VALID_PLATFORMS]
    if not platforms:
        return None, "Pick at least one platform to post to."

    payload = {"post": message.strip(), "platforms": platforms}
    if media_urls:
        payload["mediaUrls"] = [u.strip() for u in media_urls if u and u.strip()]
    if schedule_date:
        payload["scheduleDate"] = schedule_date

    try:
        resp = requests.post(
            AYRSHARE_POST_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=20,
        )
    except requests.exceptions.Timeout:
        return None, "Ayrshare took too long to respond. Try again."
    except requests.exceptions.RequestException as e:
        return None, f"Could not reach Ayrshare: {e}"

    try:
        data = resp.json()
    except ValueError:
        return None, f"Ayrshare returned an unexpected response (HTTP {resp.status_code})."

    if resp.status_code >= 400:
        # Ayrshare error responses generally include a "message" or "errors" field.
        err = data.get("message") or data.get("errors") or data.get("error") or f"HTTP {resp.status_code}"
        return None, f"Ayrshare rejected the post: {err}"

    # Success responses list per-platform post results, some of which can
    # individually have failed even on an overall 200 — surface those too.
    per_platform_errors = []
    for item in data.get("postIds", []) or []:
        if item.get("status") == "error":
            per_platform_errors.append(f"{item.get('platform', '?')}: {item.get('errors') or item.get('message') or 'failed'}")
    if per_platform_errors and len(per_platform_errors) == len(platforms):
        return None, "All platforms failed: " + "; ".join(per_platform_errors)

    return {"raw": data, "partial_errors": per_platform_errors}, None
