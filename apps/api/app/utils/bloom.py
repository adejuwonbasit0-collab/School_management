"""
Bloom (trybloom.ai) integration — real API, confirmed against Bloom's
published docs (trybloom.ai/docs/api). This replaces an earlier version
of this file that was written *before* those docs were reachable and
had to guess the request/response shape — that guess was wrong in a
few important ways, which is why generation was failing:

  - Auth is `x-api-key: <key>` — NOT `Authorization: Bearer <key>`.
  - Bloom only generates IMAGES. There's no text or video endpoint in
    their API, so the old "kind: text/image/video" idea doesn't apply —
    this file only does images now.
  - Generation is brand-scoped: every image belongs to a "brand" (an
    onboarded site/Instagram account Bloom has analyzed for visual DNA).
    You can't generate anything until a brand exists and its status is
    "ready".
  - Generation itself is async: POST /images/generations queues the job
    (202) and hands back an id; you then GET /images/{id}?wait=true to
    block until it's actually done and get the final image URL back.

Settings used (Admin -> Settings -> Bloom):
  - bloom_api_key            required
  - bloom_brand_session_id   which brand to generate against — set
                             automatically when you onboard one from
                             Settings, or paste an existing brand's id
"""
import requests as _requests
from app.utils.settings import get_setting

BASE_URL = "https://www.trybloom.ai/api/v1"
_TIMEOUT = 15
_WAIT_TIMEOUT = 90  # Bloom holds the connection open (wait=true) up to its own server-side cap


def bloom_configured():
    """True if an API key is set — enough to attempt any call."""
    return bool((get_setting("bloom_api_key") or "").strip())


def _headers():
    return {"x-api-key": (get_setting("bloom_api_key") or "").strip(), "Content-Type": "application/json"}


def _request(method, path, timeout=None, **kwargs):
    """Low-level call. Returns (data, error) — exactly one is None.
    `data` is the parsed `data` envelope on success. `error` is built
    from Bloom's `{"error": {"code","status","message"}}` envelope on
    failure, or a plain network/parsing message. Never raises."""
    api_key = (get_setting("bloom_api_key") or "").strip()
    if not api_key:
        return None, "Bloom isn't configured yet — add an API key in Admin -> Settings -> Bloom first."

    url = BASE_URL + path
    try:
        resp = _requests.request(method, url, headers=_headers(), timeout=timeout or _TIMEOUT, **kwargs)
    except _requests.exceptions.RequestException as e:
        return None, f"Couldn't reach Bloom at {url}: {e}"

    try:
        body = resp.json()
    except ValueError:
        return None, f"Bloom returned a non-JSON response (HTTP {resp.status_code}): {resp.text[:300]}"

    if resp.status_code >= 400:
        err = (body or {}).get("error") or {}
        code = err.get("code", "UNKNOWN")
        msg = err.get("message") or str(body)[:300]
        return None, f"Bloom error [{code}]: {msg}"

    return body.get("data"), None


def list_brands():
    """GET /brands -> (list_of_brand_dicts, error)."""
    data, err = _request("GET", "/brands")
    if err:
        return None, err
    if not data:
        return [], None
    return (data if isinstance(data, list) else [data]), None


def onboard_brand(url):
    """POST /brands {url} -> queues brand analysis in the background.
    Returns (brand_dict, error) where brand_dict is {"id":..., "status": "analyzing"}."""
    url = (url or "").strip()
    if not url:
        return None, "Enter a website or Instagram URL to onboard as a Bloom brand."
    return _request("POST", "/brands", json={"url": url})


def get_brand(brand_id, wait=False):
    """GET /brands/{id}[?wait=true] -> (brand_dict, error). Status is one
    of analyzing/ready/logo_required/failed; `failure` is set when failed."""
    if not brand_id:
        return None, "No brand id given."
    params = {"wait": "true"} if wait else {}
    return _request("GET", f"/brands/{brand_id}", params=params, timeout=_WAIT_TIMEOUT if wait else _TIMEOUT)


def ensure_ready_brand():
    """Resolves the configured brand (bloom_brand_session_id) and checks
    it's actually ready to generate against. Returns (brand_id, error) —
    error is a plain-language, user-facing string in every failure case
    (not configured / still analyzing / needs a logo / failed), so
    callers can show it directly instead of a raw API error."""
    brand_id = (get_setting("bloom_brand_session_id") or "").strip()
    if not brand_id:
        return None, ("No Bloom brand is set up yet — go to Admin -> Settings -> Bloom and "
                       "onboard your site's URL as a brand first.")
    brand, err = get_brand(brand_id)
    if err:
        return None, err

    status = (brand or {}).get("status")
    if status == "ready":
        return brand_id, None
    if status == "analyzing":
        return None, "Bloom is still analyzing your brand — try again in a moment."
    if status == "logo_required":
        return None, "Bloom needs a logo before it can finish setting up your brand — check Admin -> Settings -> Bloom."
    if status == "failed":
        failure = (brand or {}).get("failure") or {}
        return None, (f"Bloom's brand setup failed ({failure.get('code', 'UNKNOWN')}): "
                       f"{failure.get('message', 'unknown error')}. Try onboarding again.")
    return None, f"Unexpected brand status '{status}'."


def generate_image(prompt, brand_session_id=None):
    """Generates one on-brand image from a prompt. Returns (image_url, error).
    Handles Bloom's async contract end-to-end: queues the job, then polls
    with wait=true until it's actually done."""
    prompt = (prompt or "").strip()
    if not prompt:
        return None, "Enter a prompt describing the image you want Bloom to generate."

    if not brand_session_id:
        brand_session_id, err = ensure_ready_brand()
        if err:
            return None, err

    data, err = _request("POST", "/images/generations", json={"brandSessionId": brand_session_id, "prompt": prompt})
    if err:
        return None, err

    image_id = None
    if isinstance(data, dict):
        image_id = data.get("id") or (data.get("ids") or [None])[0]
    if not image_id:
        return None, f"Bloom accepted the request but didn't return an image id: {str(data)[:300]}"

    result, err = _request("GET", f"/images/{image_id}", params={"wait": "true"}, timeout=_WAIT_TIMEOUT)
    if err:
        return None, err
    if not isinstance(result, dict):
        return None, f"Unexpected response while checking on Bloom image {image_id}: {str(result)[:300]}"
    if result.get("status") != "completed":
        return None, f"Bloom generation ended with status '{result.get('status')}' — try again."
    image_url = result.get("imageUrl")
    if not image_url:
        return None, f"Bloom marked the image completed but returned no imageUrl: {str(result)[:300]}"
    return image_url, None
