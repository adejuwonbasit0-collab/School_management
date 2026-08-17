"""
Domain availability + subdomain validation helpers for the hosting module.

Domain availability uses a raw WHOIS query (stdlib `socket` only — same
technique as app/ai_tools/browser_tools.py's WHOIS tool) rather than a
paid registrar API, since actually *registering* a new domain requires
a registrar reseller account (Namecheap/GoDaddy/etc. API key) that
isn't configured here. This gives real, accurate availability info for
free; wire in a registrar API under `register_domain()` below once
credentials are available.
"""
import re
import socket

RESERVED_SUBDOMAINS = {
    "www", "mail", "ftp", "admin", "api", "app", "blog", "shop", "store",
    "dashboard", "portal", "cpanel", "webmail", "ns1", "ns2", "smtp", "pop",
    "imap", "vpn", "test", "staging", "dev", "beta", "status", "support",
    "help", "docs", "cdn", "static", "assets", "media", "files", "download",
    "billing", "pay", "payment", "checkout", "secure", "login", "signup",
    "register", "account", "accounts", "bazillin", "root", "system",
}

SUBDOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

_TLD_SERVERS = {
    "com": "whois.verisign-grs.com", "net": "whois.verisign-grs.com",
    "org": "whois.pir.org", "io": "whois.nic.io", "dev": "whois.nic.google",
    "app": "whois.nic.google", "co": "whois.nic.co", "info": "whois.afilias.net",
    "biz": "whois.nic.biz", "me": "whois.nic.me", "ai": "whois.nic.ai",
    "xyz": "whois.nic.xyz", "tech": "whois.nic.tech",
}

_NOT_FOUND_MARKERS = (
    "no match", "not found", "no data found", "no entries found",
    "status: free", "no object found", "domain not found",
    "is available for registration",
)


def validate_subdomain_format(value: str):
    """Returns (ok: bool, error: str|None)."""
    value = (value or "").strip().lower()
    if not value:
        return False, "Enter a subdomain."
    if len(value) < 3:
        return False, "Must be at least 3 characters."
    if len(value) > 63:
        return False, "Must be 63 characters or fewer."
    if not SUBDOMAIN_RE.match(value):
        return False, "Only lowercase letters, numbers, and hyphens (can't start/end with a hyphen)."
    if value in RESERVED_SUBDOMAINS:
        return False, f'"{value}" is reserved. Please choose another.'
    return True, None


def check_whois(domain: str, timeout=8):
    """Raw WHOIS query. Returns (raw_text, server) or raises."""
    domain = domain.strip().lower().replace("http://", "").replace("https://", "").split("/")[0]
    tld = domain.rsplit(".", 1)[-1]
    server = _TLD_SERVERS.get(tld, "whois.iana.org")

    def query(host, query_domain):
        with socket.create_connection((host, 43), timeout=timeout) as sock:
            sock.sendall((query_domain + "\r\n").encode())
            chunks = []
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                chunks.append(data)
            return b"".join(chunks).decode(errors="replace")

    raw = query(server, domain)
    for line in raw.splitlines():
        if line.lower().startswith("registrar whois server:"):
            referral = line.split(":", 1)[1].strip()
            if referral and referral != server:
                try:
                    raw = query(referral, domain)
                except Exception:
                    pass
            break
    return raw, server


def check_domain_availability(domain: str):
    """
    Returns dict: {domain, available: bool|None, reason}.
    available=None means we couldn't determine it (unsupported TLD /
    WHOIS server didn't respond in a recognizable format) — the UI
    should show "couldn't check" rather than a false positive/negative.
    """
    domain = (domain or "").strip().lower()
    if not domain or "." not in domain or " " in domain:
        return {"domain": domain, "available": None, "reason": "Enter a valid domain name."}
    try:
        raw, server = check_whois(domain)
    except Exception as e:
        return {"domain": domain, "available": None, "reason": f"Could not reach WHOIS: {e}"}

    lowered = raw.lower()
    if any(marker in lowered for marker in _NOT_FOUND_MARKERS):
        return {"domain": domain, "available": True, "reason": "No registration found."}
    if "domain name:" in lowered or "registrar:" in lowered or "creation date:" in lowered:
        return {"domain": domain, "available": False, "reason": "Already registered."}
    return {"domain": domain, "available": None, "reason": "WHOIS response was inconclusive for this TLD."}


def register_domain(domain: str, years: int = 1):
    """
    Not wired to a real registrar yet — actually purchasing/registering
    a domain requires a reseller API account (Namecheap/GoDaddy/etc).
    Raises so callers fail loudly instead of pretending to succeed.
    """
    raise NotImplementedError(
        "Domain registration requires a registrar API key (e.g. Namecheap "
        "Reseller API) that isn't configured yet. Availability checks work "
        "without one; wire your registrar's API here to enable purchases."
    )
