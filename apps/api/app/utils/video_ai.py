"""Generic video-generation integration. Same honesty rule as bloom.py and
web_search.py: there's no way to verify a specific "free video AI" from
this environment (no live web access, and free-tier terms/APIs change
constantly), so rather than hardcode a guess at one provider's contract
that might already be wrong by the time this runs, the endpoint is fully
admin-configurable — point it at whichever provider you sign up with
(many video-gen APIs — e.g. Stability AI, Runway, Pika — offer some form
of free or trial tier; check current terms before relying on "free").
"""
import requests as _requests
from app.utils.settings import get_setting


def video_ai_configured():
    return bool((get_setting("video_ai_api_key") or "").strip() and (get_setting("video_ai_base_url") or "").strip())


def generate_video(prompt, max_wait_note=True):
    """Returns (result, error) — exactly one is None. `result` is whatever
    string the provider returns under the configured response field — a
    direct video URL for providers that generate synchronously, or a job/
    request ID for providers that generate asynchronously (many video APIs
    do — if what comes back looks like an ID rather than a URL, that's
    normal and expected, not a bug in this integration)."""
    api_key = (get_setting("video_ai_api_key") or "").strip()
    base_url = (get_setting("video_ai_base_url") or "").strip().rstrip("/")
    path = (get_setting("video_ai_api_path") or "/generate").strip()
    if not path.startswith("/"):
        path = "/" + path
    prompt_field = (get_setting("video_ai_prompt_field") or "prompt").strip() or "prompt"
    response_field = (get_setting("video_ai_response_field") or "video_url").strip() or "video_url"

    if not api_key or not base_url:
        return None, ("Video AI isn't configured yet — add an API key and base URL in "
                       "Admin -> Settings -> Video AI first.")

    url = base_url + path
    try:
        resp = _requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={prompt_field: prompt},
            timeout=60,
        )
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach the video AI at {url}: {e}"

    if resp.status_code >= 400:
        return None, f"Video AI returned HTTP {resp.status_code}: {resp.text[:500]}"

    try:
        data = resp.json()
    except ValueError:
        return None, f"Video AI's response wasn't JSON: {resp.text[:500]}"

    if isinstance(data, dict) and response_field in data:
        result = data[response_field]
        return (result if isinstance(result, str) else str(result)), None

    return None, (f"Got a 200 but couldn't find a '{response_field}' field in the response. "
                   f"Raw response so you can find the right field name: {str(data)[:500]}")
