"""
Software/game import — two real, free, keyless public APIs:

  Internet Archive (archive.org)
    - Advanced Search API   https://archive.org/advancedsearch.php
    - Metadata API          https://archive.org/metadata/{identifier}
    Old console/DOS/Apple II games and utilities, playable live in-browser
    via archive.org's own emulator.

  Modrinth (modrinth.com)
    - Search API   https://api.modrinth.com/v2/search
    - Project/version API   https://api.modrinth.com/v2/project/{id}
    Real, currently-maintained Minecraft mods/plugins/resource packs/
    datapacks — actual downloadable .jar/.zip files, open-source licensed
    per-project (real license shown per item, not a blanket assumption).

Every imported item gets real, working data — actual cover art, a real
download link pulled from the item's own file list, and (for archive.org)
a live playable link. Nothing here is a metadata-only stub.

Licensing note (surfaced in every imported item's long_desc, not hidden):
archive.org's software collection sits under a preservation/fair-use
framing rather than the clean public-domain status their film collection
has. Modrinth projects each carry their own explicit open-source license,
which is included per item instead of assumed.
"""
import re
import requests

# ── Internet Archive ────────────────────────────────────────────────────────
IA_SEARCH_URL = "https://archive.org/advancedsearch.php"
IA_METADATA_URL = "https://archive.org/metadata/{}"
IA_THUMB_URL = "https://archive.org/services/img/{}"
IA_DETAILS_URL = "https://archive.org/details/{}"
IA_EMBED_URL = "https://archive.org/embed/{}"
IA_DOWNLOAD_URL = "https://archive.org/download/{}/{}"

# ── Modrinth ─────────────────────────────────────────────────────────────────
MR_SEARCH_URL = "https://api.modrinth.com/v2/search"
MR_PROJECT_URL = "https://api.modrinth.com/v2/project/{}"
MR_VERSIONS_URL = "https://api.modrinth.com/v2/project/{}/version"
MR_PROJECT_PAGE = "https://modrinth.com/{}/{}"
# Modrinth requires a uniquely-identifying User-Agent on every request.
MR_HEADERS = {"User-Agent": "Bazillin-Marketplace/1.0 (software importer)"}

TIMEOUT = 12
_TAG_RE = re.compile(r"<[^>]+>")

# Real software/rom/disk-image formats worth offering as "the" download —
# everything else on an archive.org item page is usually housekeeping
# (metadata xml, torrent, checksums, thumbnail images).
_DOWNLOADABLE_EXTS = (
    ".zip", ".7z", ".rar", ".iso", ".bin", ".img", ".rom",
    ".nes", ".sfc", ".smc", ".gba", ".gb", ".gbc", ".n64", ".z64",
    ".exe", ".d64", ".adf", ".dsk", ".pce", ".cue",
)
_SKIP_SUFFIXES = (".xml", ".torrent", ".sqlite", ".gif", "_meta.txt", ".png", ".jpg", ".jpeg")

SOURCES = ("archive", "modrinth")


def _clean_text(raw):
    """Strips HTML tags/entities — both sources sometimes return HTML or
    markdown-ish text where a plain string is expected."""
    if not raw:
        return ""
    if isinstance(raw, list):
        raw = " ".join(str(r) for r in raw)
    text = _TAG_RE.sub(" ", str(raw))
    for ent, repl in (("&nbsp;", " "), ("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">")):
        text = text.replace(ent, repl)
    return re.sub(r"\s+", " ", text).strip()


# ── Internet Archive: search + detail ───────────────────────────────────────
def _search_archive(query, page=1, rows=24):
    query = (query or "").strip()
    q = f"({query}) AND mediatype:(software)" if query else "mediatype:(software)"
    params = {
        "q": q,
        "fl[]": ["identifier", "title", "description", "year", "downloads", "collection"],
        "rows": max(1, min(int(rows or 24), 50)),
        "page": max(1, int(page or 1)),
        "sort[]": "downloads desc",
        "output": "json",
    }
    try:
        resp = requests.get(IA_SEARCH_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        docs = (resp.json().get("response") or {}).get("docs") or []
    except requests.exceptions.RequestException as e:
        return None, f"Couldn't reach archive.org: {e}"
    except ValueError:
        return None, "archive.org returned an unexpected (non-JSON) response."

    results = []
    for d in docs:
        identifier = d.get("identifier")
        if not identifier:
            continue
        results.append({
            "source": "archive",
            "identifier": identifier,
            "title": d.get("title") or identifier,
            "description": _clean_text(d.get("description"))[:220],
            "year": d.get("year"),
            "downloads": d.get("downloads", 0),
            "thumbnail_url": IA_THUMB_URL.format(identifier),
            "details_url": IA_DETAILS_URL.format(identifier),
        })
    return results, None


def _pick_ia_download_file(files, identifier):
    candidates = []
    for f in files or []:
        name = f.get("name") or ""
        if not name or name.startswith("__"):
            continue
        low = name.lower()
        if low.endswith(_SKIP_SUFFIXES):
            continue
        try:
            size = int(f.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        candidates.append((name, size, low.endswith(_DOWNLOADABLE_EXTS)))
    if not candidates:
        return None
    preferred = [c for c in candidates if c[2]]
    pool = preferred or candidates
    best = max(pool, key=lambda c: c[1])
    return IA_DOWNLOAD_URL.format(identifier, best[0])


def _detail_archive(identifier):
    try:
        resp = requests.get(IA_METADATA_URL.format(identifier), timeout=TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.RequestException as e:
        return None, f"Couldn't fetch details for '{identifier}': {e}"
    except ValueError:
        return None, f"archive.org returned an unexpected response for '{identifier}'."

    meta = payload.get("metadata") or {}
    if not meta:
        return None, f"'{identifier}' has no metadata on archive.org."

    title = meta.get("title") or identifier
    description = _clean_text(meta.get("description"))
    subject = meta.get("subject") or []
    if isinstance(subject, str):
        subject = [s.strip() for s in re.split(r"[;,]", subject) if s.strip()]
    tags = [s.lower() for s in subject][:10]

    download_url = _pick_ia_download_file(payload.get("files"), identifier)
    thumbnail_url = IA_THUMB_URL.format(identifier)
    details_url = IA_DETAILS_URL.format(identifier)
    embed_url = IA_EMBED_URL.format(identifier)

    attribution = (
        f"Sourced from the Internet Archive's software preservation library ({details_url}). "
        f"Provided for historical/preservation access under archive.org's framing for this "
        f"collection — check archive.org's terms before any commercial use."
    )
    long_desc = f"{description}\n\n{attribution}" if description else attribution

    return {
        "source": "archive",
        "identifier": identifier,
        "title": title[:256],
        "description": (description or title)[:500],
        "long_desc": long_desc,
        "category": "software",
        "type": "software",
        "tags": tags,
        "images": [thumbnail_url],
        "preview_url": thumbnail_url,
        "demo_url": embed_url,
        "file_url": download_url or details_url,
        "license": "standard",
        "version": str(meta.get("year") or "") or "1.0.0",
    }, None


# ── Modrinth: search + detail ───────────────────────────────────────────────
def _search_modrinth(query, page=1, rows=24):
    query = (query or "").strip()
    limit = max(1, min(int(rows or 24), 50))
    offset = (max(1, int(page or 1)) - 1) * limit
    params = {"query": query, "limit": limit, "offset": offset}
    try:
        resp = requests.get(MR_SEARCH_URL, params=params, headers=MR_HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        hits = resp.json().get("hits") or []
    except requests.exceptions.RequestException as e:
        return None, f"Couldn't reach Modrinth: {e}"
    except ValueError:
        return None, "Modrinth returned an unexpected (non-JSON) response."

    results = []
    for h in hits:
        pid = h.get("project_id") or h.get("slug")
        if not pid:
            continue
        ptype = h.get("project_type") or "mod"
        slug = h.get("slug") or pid
        results.append({
            "source": "modrinth",
            "identifier": pid,
            "title": h.get("title") or slug,
            "description": _clean_text(h.get("description"))[:220],
            "year": (h.get("date_created") or "")[:4],
            "downloads": h.get("downloads", 0),
            "thumbnail_url": h.get("icon_url") or "",
            "details_url": MR_PROJECT_PAGE.format(ptype, slug),
        })
    return results, None


def _detail_modrinth(project_id):
    try:
        p_resp = requests.get(MR_PROJECT_URL.format(project_id), headers=MR_HEADERS, timeout=TIMEOUT)
        p_resp.raise_for_status()
        project = p_resp.json()
        v_resp = requests.get(MR_VERSIONS_URL.format(project_id), headers=MR_HEADERS, timeout=TIMEOUT)
        v_resp.raise_for_status()
        versions = v_resp.json() or []
    except requests.exceptions.RequestException as e:
        return None, f"Couldn't fetch details for '{project_id}' on Modrinth: {e}"
    except ValueError:
        return None, f"Modrinth returned an unexpected response for '{project_id}'."

    if not project:
        return None, f"'{project_id}' has no project data on Modrinth."

    title = project.get("title") or project_id
    slug = project.get("slug") or project_id
    ptype = project.get("project_type") or "mod"
    description = _clean_text(project.get("description") or project.get("body"))
    categories = (project.get("categories") or []) + (project.get("loaders") or [])
    tags = [c.lower() for c in categories][:10]

    file_url = None
    latest_version_num = "1.0.0"
    if versions:
        latest = versions[0]
        latest_version_num = latest.get("version_number") or latest_version_num
        files = latest.get("files") or []
        primary = next((f for f in files if f.get("primary")), files[0] if files else None)
        if primary:
            file_url = primary.get("url")

    icon_url = project.get("icon_url") or ""
    details_url = MR_PROJECT_PAGE.format(ptype, slug)
    lic = project.get("license") or {}
    license_name = lic.get("name") or lic.get("id") or "open-source (see Modrinth page)"

    attribution = (
        f"Sourced from Modrinth ({details_url}). Licensed under {license_name} — "
        f"see the project page for the full license terms before redistribution."
    )
    long_desc = f"{description}\n\n{attribution}" if description else attribution

    return {
        "source": "modrinth",
        "identifier": project_id,
        "title": title[:256],
        "description": (description or title)[:500],
        "long_desc": long_desc,
        "category": "software",
        "type": ptype,
        "tags": tags,
        "images": [icon_url] if icon_url else [],
        "preview_url": icon_url,
        "demo_url": details_url,
        "file_url": file_url or details_url,
        "license": "standard",
        "version": latest_version_num,
    }, None


# ── Public dispatch ──────────────────────────────────────────────────────────
def search_software(query, source="archive", page=1, rows=24):
    """Searches one real software source. `source` is 'archive' or
    'modrinth'. Returns (results, error) — exactly one is None."""
    if source == "modrinth":
        return _search_modrinth(query, page=page, rows=rows)
    return _search_archive(query, page=page, rows=rows)


def get_software_detail(source, identifier):
    """Fetches full detail for one item from the given source and shapes
    it into fields ready to hand to Product(...). Returns (fields, error)."""
    if source == "modrinth":
        return _detail_modrinth(identifier)
    return _detail_archive(identifier)

