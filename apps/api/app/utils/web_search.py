"""Live web search for agents. Same honesty rule as bloom.py: this can't
call a specific provider correctly without a real API key AND knowing
that provider's exact request/response shape, so — like Bloom — the
provider choice and field names are admin-configurable rather than
hardcoded to one guessed service. Two well-known, genuinely-cheap options
are pre-filled as presets (Serper.dev, Brave Search API) since their
request/response shapes are stable and simple; "custom" lets an admin
point this at anything else that returns JSON.
"""
import requests as _requests
from app.utils.settings import get_setting

_PRESETS = {
    "serper": {
        "url": "https://google.serper.dev/search",
        "auth_style": "header_x_api_key",
        "query_field": "q",
        "results_path": "organic",
        "snippet_field": "snippet",
        "title_field": "title",
        "link_field": "link",
    },
    "brave": {
        "url": "https://api.search.brave.com/res/v1/web/search",
        "auth_style": "header_x_subscription_token",
        "query_field": "q",
        "results_path": "web.results",
        "snippet_field": "description",
        "title_field": "title",
        "link_field": "url",
    },
}


def _dig(data, dotted_path):
    cur = data
    for part in dotted_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def search_web(query, max_results=5):
    """Returns (formatted_text, error) — exactly one is None."""
    provider = (get_setting("web_search_provider") or "").strip().lower()
    api_key = (get_setting("web_search_api_key") or "").strip()

    if not provider or not api_key:
        return None, ("Web search isn't configured yet — set a provider and API key in "
                       "Admin -> Settings -> Web Search (Serper.dev and Brave Search both have "
                       "free-tier keys you can generate in a couple of minutes).")

    if provider in _PRESETS:
        cfg = _PRESETS[provider]
        headers = {"Content-Type": "application/json"}
        if cfg["auth_style"] == "header_x_api_key":
            headers["X-API-KEY"] = api_key
        elif cfg["auth_style"] == "header_x_subscription_token":
            headers["X-Subscription-Token"] = api_key
        try:
            if provider == "serper":
                resp = _requests.post(cfg["url"], headers=headers, json={cfg["query_field"]: query}, timeout=15)
            else:
                resp = _requests.get(cfg["url"], headers=headers, params={cfg["query_field"]: query}, timeout=15)
        except _requests.exceptions.RequestException as e:
            return None, f"Couldn't reach {provider}: {e}"
        if resp.status_code >= 400:
            return None, f"{provider} returned HTTP {resp.status_code}: {resp.text[:300]}"
        try:
            data = resp.json()
        except ValueError:
            return None, f"{provider}'s response wasn't JSON: {resp.text[:300]}"
        results = _dig(data, cfg["results_path"]) or []
    else:
        # "custom" — fully admin-configured generic REST search, same
        # pattern as Bloom, for any other JSON-returning search API.
        base_url = (get_setting("web_search_base_url") or "").strip()
        results_path = (get_setting("web_search_results_path") or "results").strip()
        title_field = (get_setting("web_search_title_field") or "title").strip()
        snippet_field = (get_setting("web_search_snippet_field") or "snippet").strip()
        link_field = (get_setting("web_search_link_field") or "link").strip()
        if not base_url:
            return None, "Custom web search selected but no base URL is configured in Admin -> Settings -> Web Search."
        try:
            resp = _requests.get(base_url, headers={"Authorization": f"Bearer {api_key}"}, params={"q": query}, timeout=15)
        except _requests.exceptions.RequestException as e:
            return None, f"Couldn't reach {base_url}: {e}"
        if resp.status_code >= 400:
            return None, f"Search API returned HTTP {resp.status_code}: {resp.text[:300]}"
        try:
            data = resp.json()
        except ValueError:
            return None, f"Search API's response wasn't JSON: {resp.text[:300]}"
        results = _dig(data, results_path) or []
        cfg = {"title_field": title_field, "snippet_field": snippet_field, "link_field": link_field}

    if not results:
        return f'No results found for "{query}".', None

    lines = [f'Search results for "{query}":']
    for r in results[:max_results]:
        if not isinstance(r, dict):
            continue
        title = r.get(cfg["title_field"], "")
        snippet = r.get(cfg["snippet_field"], "")
        link = r.get(cfg["link_field"], "")
        lines.append(f"- {title}: {snippet} ({link})")
    return "\n".join(lines), None
