"""
Fetches real developer news/trends from free, official, no-API-key-required
sources. Admin-triggered (button in Admin -> Trends) rather than a scheduled
job, since this project has no task queue/cron infra set up — see the note
in app/admin/routes.py:fetch_trends.

Sources:
- Hacker News (official Firebase API) — general dev/tech news & discussion
- Dev.to (official public API) — articles, tutorials, announcements
- GitHub (official REST search API, unauthenticated) — trending new repos

Every item stores the real source URL, so clicking a trend on the site
takes the visitor to where it was actually posted — never a redirect
through this site.
"""
import requests

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"
DEVTO_ARTICLES = "https://dev.to/api/articles?top=3&per_page=15"
GITHUB_SEARCH = "https://api.github.com/search/repositories"

TIMEOUT = 8


def fetch_hacker_news(limit=15):
    items = []
    try:
        ids = requests.get(HN_TOP, timeout=TIMEOUT).json()[:40]
    except Exception:
        return items
    for hn_id in ids:
        if len(items) >= limit:
            break
        try:
            item = requests.get(HN_ITEM.format(hn_id), timeout=TIMEOUT).json()
        except Exception:
            continue
        if not item or item.get("type") != "story" or not item.get("url"):
            continue
        items.append({
            "title": item.get("title", "")[:512],
            "description": None,
            "url": item["url"],
            "source": "Hacker News",
            "category": "news",
            "score": item.get("score", 0),
        })
    return items


def fetch_devto(limit=15):
    items = []
    try:
        articles = requests.get(DEVTO_ARTICLES, timeout=TIMEOUT).json()
    except Exception:
        return items
    for a in articles[:limit]:
        items.append({
            "title": a.get("title", "")[:512],
            "description": (a.get("description") or "")[:500],
            "url": a.get("url"),
            "source": "DEV Community",
            "category": "article",
            "score": a.get("positive_reactions_count", 0),
        })
    return items


def fetch_github_trending(limit=15):
    """Uses GitHub's official search API (no key needed for light use) to
    approximate 'trending' as recently-created repos sorted by stars —
    GitHub has no official trending API, and scraping the HTML trending
    page would be fragile and against the spirit of their ToS, so this
    uses a real, sanctioned endpoint instead."""
    import datetime
    since = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
    params = {"q": f"created:>{since}", "sort": "stars", "order": "desc", "per_page": limit}
    items = []
    try:
        data = requests.get(GITHUB_SEARCH, params=params, timeout=TIMEOUT,
                             headers={"Accept": "application/vnd.github+json"}).json()
    except Exception:
        return items
    for repo in data.get("items", [])[:limit]:
        items.append({
            "title": repo.get("full_name", "")[:512],
            "description": (repo.get("description") or "")[:500],
            "url": repo.get("html_url"),
            "source": "GitHub",
            "category": "repo",
            "score": repo.get("stargazers_count", 0),
        })
    return items


def fetch_all():
    """Returns a combined, deduped-by-url list from all sources."""
    results = []
    seen_urls = set()
    for fetcher in (fetch_hacker_news, fetch_devto, fetch_github_trending):
        try:
            for item in fetcher():
                if item.get("url") and item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    results.append(item)
        except Exception:
            continue  # one source failing shouldn't kill the whole fetch
    return results
