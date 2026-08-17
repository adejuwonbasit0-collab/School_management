"""
Two lighter-weight alternatives to Bloom for getting images into content,
for when Bloom isn't reachable (e.g. a host's outbound proxy blocking it)
or the admin just wants something simpler:

1. Pexels — REAL stock photos matched to a topic/keyword (this is what
   actually answers "fetch pictures from Google relating to the content" —
   Google itself has no free image-search API worth using (Custom Search
   JSON API needs a Programmable Search Engine + only 100 free queries a
   day); Pexels is free, needs one API key, and returns real, properly-
   licensed photos, which is what you'd actually want to publish anyway.
   Free key: https://www.pexels.com/api/

2. Pollinations — free, NO API key at all, AI-generated images. You hand
   it a prompt and it hands back a working image URL directly; there's no
   sign-up step, so it's a genuine drop-in fallback the moment Bloom or
   DALL-E aren't available.
"""
import urllib.parse
import requests as _requests
from app.utils.settings import get_setting

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"


def pexels_configured():
    return bool((get_setting("pexels_api_key") or "").strip())


def search_photos(query, per_page=8):
    """Real stock photos matching `query`. Returns (photos, error).
    Each photo: {url, thumb, photographer, photographer_url, alt}."""
    query = (query or "").strip()
    if not query:
        return None, "Enter a topic or keyword to search photos for."
    api_key = (get_setting("pexels_api_key") or "").strip()
    if not api_key:
        return None, ("Pexels isn't configured yet — grab a free API key at "
                       "pexels.com/api and add it in Admin -> Settings -> Bloom & Images.")
    try:
        resp = _requests.get(
            PEXELS_SEARCH_URL,
            headers={"Authorization": api_key},
            params={"query": query, "per_page": max(1, min(int(per_page or 8), 15))},
            timeout=20,
        )
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach Pexels: {e}"

    if resp.status_code == 401:
        return None, "Pexels rejected that API key (401) — double-check it in Admin -> Settings."
    if resp.status_code == 429:
        return None, "Pexels rate limit hit (their free tier is 200 requests/hour) — try again shortly."
    try:
        resp.raise_for_status()
        data = resp.json()
    except _requests.exceptions.RequestException as e:
        return None, f"Pexels returned an error: {e}"
    except ValueError:
        return None, "Pexels returned an unexpected (non-JSON) response."

    photos = []
    for p in data.get("photos", []):
        src = p.get("src", {})
        photos.append({
            "url": src.get("large2x") or src.get("large") or src.get("original"),
            "thumb": src.get("medium") or src.get("small"),
            "photographer": p.get("photographer"),
            "photographer_url": p.get("photographer_url"),
            "alt": p.get("alt") or query,
        })
    if not photos:
        return [], None
    return photos, None


def pollinations_image_url(prompt, width=1024, height=1024, seed=None):
    """No API key needed. Returns (image_url, error) — the URL itself does
    the generating server-side on Pollinations' end the moment it's
    fetched/rendered, so there's nothing to poll."""
    prompt = (prompt or "").strip()
    if not prompt:
        return None, "Enter a prompt describing the image you want."
    encoded = urllib.parse.quote(prompt)
    url = POLLINATIONS_URL.format(prompt=encoded)
    params = f"width={int(width)}&height={int(height)}&nologo=true"
    if seed is not None:
        params += f"&seed={int(seed)}"
    return f"{url}?{params}", None
