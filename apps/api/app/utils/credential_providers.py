"""
Automation Studio — Credential Providers
==========================================
A small registry describing how to collect and *actually verify* a
connection to an external app. Each provider defines:
  - the form fields needed to collect the secret(s)
  - how those fields map into an Authorization/auth header
  - a real test() function that makes a genuine, low-cost, read-only API
    call to confirm the credential actually works — not a fake green
    checkmark. Where a provider has no safe way to verify without a paid
    or write-side call, `test_supported` is False and the UI says so
    honestly instead of pretending to have checked.

This is intentionally a curated subset (the providers with a real
"who am I" style endpoint), not all 103 integration_catalog entries —
growing this list is how more providers get real one-click-verified
connections over time.
"""
import base64

import requests


def _ok(message):
    return True, message


def _fail(message):
    return False, message


def _test_slack(secret):
    token = secret.get("token", "")
    r = requests.get("https://slack.com/api/auth.test",
                      headers={"Authorization": f"Bearer {token}"}, timeout=10)
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if data.get("ok"):
        return _ok(f"Connected as {data.get('user', 'unknown user')} in {data.get('team', 'unknown workspace')}")
    return _fail(data.get("error", f"HTTP {r.status_code}"))


def _test_github(secret):
    token = secret.get("token", "")
    r = requests.get("https://api.github.com/user",
                      headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}, timeout=10)
    if r.status_code == 200:
        return _ok(f"Connected as {r.json().get('login', 'unknown user')}")
    return _fail(f"GitHub returned HTTP {r.status_code}")


def _test_notion(secret):
    token = secret.get("token", "")
    r = requests.get("https://api.notion.com/v1/users/me",
                      headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}, timeout=10)
    if r.status_code == 200:
        return _ok(f"Connected as {r.json().get('name', 'unknown user')}")
    return _fail(f"Notion returned HTTP {r.status_code}")


def _test_openai(secret):
    token = secret.get("token", "")
    r = requests.get("https://api.openai.com/v1/models",
                      headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code == 200:
        return _ok("Connected — API key is valid")
    return _fail(f"OpenAI returned HTTP {r.status_code}")


def _test_stripe(secret):
    token = secret.get("token", "")
    r = requests.get("https://api.stripe.com/v1/balance",
                      headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code == 200:
        return _ok("Connected — secret key is valid")
    return _fail(f"Stripe returned HTTP {r.status_code}")


def _test_airtable(secret):
    token = secret.get("token", "")
    r = requests.get("https://api.airtable.com/v0/meta/whoami",
                      headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code == 200:
        return _ok("Connected — token is valid")
    return _fail(f"Airtable returned HTTP {r.status_code}")


def _test_sendgrid(secret):
    token = secret.get("token", "")
    r = requests.get("https://api.sendgrid.com/v3/user/profile",
                      headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code == 200:
        return _ok("Connected — API key is valid")
    return _fail(f"SendGrid returned HTTP {r.status_code}")


def _test_hubspot(secret):
    token = secret.get("token", "")
    r = requests.get("https://api.hubapi.com/crm/v3/objects/contacts?limit=1",
                      headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code == 200:
        return _ok("Connected — access token is valid")
    return _fail(f"HubSpot returned HTTP {r.status_code}")


def _test_telegram(secret):
    token = secret.get("token", "")
    r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if data.get("ok"):
        return _ok(f"Connected as @{data.get('result', {}).get('username', 'unknown bot')}")
    return _fail(data.get("description", f"HTTP {r.status_code}"))


def _test_discord_bot(secret):
    token = secret.get("token", "")
    r = requests.get("https://discord.com/api/v10/users/@me",
                      headers={"Authorization": f"Bot {token}"}, timeout=10)
    if r.status_code == 200:
        return _ok(f"Connected as {r.json().get('username', 'unknown bot')}")
    return _fail(f"Discord returned HTTP {r.status_code}")


def _test_twilio(secret):
    sid = secret.get("account_sid", "")
    token = secret.get("auth_token", "")
    basic = base64.b64encode(f"{sid}:{token}".encode()).decode()
    r = requests.get(f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json",
                      headers={"Authorization": f"Basic {basic}"}, timeout=10)
    if r.status_code == 200:
        return _ok(f"Connected — account {r.json().get('friendly_name', sid)}")
    return _fail(f"Twilio returned HTTP {r.status_code}")


def _test_gmail(secret):
    token = secret.get("token", "")
    r = requests.get("https://gmail.googleapis.com/gmail/v1/users/me/profile",
                      headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code == 200:
        return _ok(f"Connected as {r.json().get('emailAddress', 'unknown account')}")
    if r.status_code == 401:
        return _fail("Token rejected — Gmail access tokens expire quickly (~1hr); paste a fresh one from the OAuth flow.")
    return _fail(f"Gmail returned HTTP {r.status_code}")


def _test_google_gemini(secret):
    token = secret.get("token", "")
    r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={token}", timeout=10)
    if r.status_code == 200:
        count = len(r.json().get("models", []))
        return _ok(f"Connected — API key is valid ({count} models visible)")
    return _fail(f"Google Gemini returned HTTP {r.status_code}")


def _test_elevenlabs(secret):
    token = secret.get("token", "")
    r = requests.get("https://api.elevenlabs.io/v1/user",
                      headers={"xi-api-key": token}, timeout=10)
    if r.status_code == 200:
        data = r.json()
        tier = (data.get("subscription") or {}).get("tier", "unknown tier")
        return _ok(f"Connected — {tier} plan")
    return _fail(f"ElevenLabs returned HTTP {r.status_code}")


def _test_replicate(secret):
    token = secret.get("token", "")
    r = requests.get("https://api.replicate.com/v1/account",
                      headers={"Authorization": f"Token {token}"}, timeout=10)
    if r.status_code == 200:
        return _ok(f"Connected as {r.json().get('username', 'unknown user')}")
    return _fail(f"Replicate returned HTTP {r.status_code}")


def _test_stability_ai(secret):
    token = secret.get("token", "")
    r = requests.get("https://api.stability.ai/v1/user/account",
                      headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code == 200:
        return _ok(f"Connected as {r.json().get('email', 'unknown account')}")
    return _fail(f"Stability AI returned HTTP {r.status_code}")


PROVIDERS = {
    "slack":       {"label": "Slack", "auth_type": "bearer",
                     "fields": [{"key": "token", "label": "Bot Token (xoxb-...)", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bearer {token}",
                     "test": _test_slack, "test_supported": True},
    "github":      {"label": "GitHub", "auth_type": "bearer",
                     "fields": [{"key": "token", "label": "Personal Access Token", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bearer {token}",
                     "test": _test_github, "test_supported": True},
    "notion":      {"label": "Notion", "auth_type": "bearer",
                     "fields": [{"key": "token", "label": "Internal Integration Token", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bearer {token}",
                     "test": _test_notion, "test_supported": True},
    "openai":      {"label": "OpenAI", "auth_type": "bearer",
                     "fields": [{"key": "token", "label": "API Key", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bearer {token}",
                     "test": _test_openai, "test_supported": True},
    "stripe":      {"label": "Stripe", "auth_type": "bearer",
                     "fields": [{"key": "token", "label": "Secret Key", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bearer {token}",
                     "test": _test_stripe, "test_supported": True},
    "airtable":    {"label": "Airtable", "auth_type": "bearer",
                     "fields": [{"key": "token", "label": "Personal Access Token", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bearer {token}",
                     "test": _test_airtable, "test_supported": True},
    "sendgrid":    {"label": "SendGrid", "auth_type": "bearer",
                     "fields": [{"key": "token", "label": "API Key", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bearer {token}",
                     "test": _test_sendgrid, "test_supported": True},
    "hubspot":     {"label": "HubSpot", "auth_type": "bearer",
                     "fields": [{"key": "token", "label": "Private App Access Token", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bearer {token}",
                     "test": _test_hubspot, "test_supported": True},
    "telegram":    {"label": "Telegram", "auth_type": "custom",
                     "fields": [{"key": "token", "label": "Bot Token", "secret": True}],
                     "auth_header": None, "auth_template": None,  # token goes in the URL path, not a header
                     "test": _test_telegram, "test_supported": True},
    "discord":     {"label": "Discord", "auth_type": "bot",
                     "fields": [{"key": "token", "label": "Bot Token", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bot {token}",
                     "test": _test_discord_bot, "test_supported": True},
    "twilio":      {"label": "Twilio", "auth_type": "basic",
                     "fields": [{"key": "account_sid", "label": "Account SID", "secret": False},
                                {"key": "auth_token", "label": "Auth Token", "secret": True}],
                     "auth_header": "Authorization", "auth_template": None,  # built specially (basic b64)
                     "test": _test_twilio, "test_supported": True},
    # These 5 were referenced by real integration_catalog.py items
    # (provider: "gmail" / "google_gemini" / "elevenlabs" / "replicate" /
    # "stability_ai") but had no registry entry at all — so a node using
    # one of those catalog items could show "Select Connection" with
    # nothing to ever select, since list_providers() only returns what's
    # registered here. Now registered with real, verified test() calls,
    # same as the providers above.
    "gmail":       {"label": "Gmail", "auth_type": "bearer",
                     "fields": [{"key": "token", "label": "OAuth Access Token", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bearer {token}",
                     "test": _test_gmail, "test_supported": True},
    "google_gemini": {"label": "Google Gemini", "auth_type": "custom",
                     "fields": [{"key": "token", "label": "API Key", "secret": True}],
                     "auth_header": None, "auth_template": None,  # key goes in the URL query string, not a header
                     "test": _test_google_gemini, "test_supported": True},
    "elevenlabs":  {"label": "ElevenLabs", "auth_type": "custom",
                     "fields": [{"key": "token", "label": "API Key", "secret": True}],
                     "auth_header": "xi-api-key", "auth_template": "{token}",
                     "test": _test_elevenlabs, "test_supported": True},
    "replicate":   {"label": "Replicate", "auth_type": "custom",
                     "fields": [{"key": "token", "label": "API Token", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Token {token}",
                     "test": _test_replicate, "test_supported": True},
    "stability_ai": {"label": "Stability AI", "auth_type": "bearer",
                     "fields": [{"key": "token", "label": "API Key", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bearer {token}",
                     "test": _test_stability_ai, "test_supported": True},
    # Providers below can be saved and used in nodes, but don't yet have a
    # verified safe read-only endpoint wired up here — the UI tells the
    # admin honestly that the connection is unverified rather than faking
    # a green check. Adding real test() calls for these is exactly the
    # kind of small, low-risk addition this registry is designed for.
    "anthropic":   {"label": "Anthropic", "auth_type": "custom",
                     "fields": [{"key": "token", "label": "API Key", "secret": True}],
                     "auth_header": "x-api-key", "auth_template": "{token}",
                     "test": None, "test_supported": False},
    "paystack":    {"label": "Paystack", "auth_type": "bearer",
                     "fields": [{"key": "token", "label": "Secret Key", "secret": True}],
                     "auth_header": "Authorization", "auth_template": "Bearer {token}",
                     "test": None, "test_supported": False},
    "generic":     {"label": "Generic API Key", "auth_type": "custom",
                     "fields": [{"key": "header_name", "label": "Header name (e.g. Authorization)", "secret": False},
                                {"key": "header_value", "label": "Header value (e.g. Bearer xxxx)", "secret": True}],
                     "auth_header": None, "auth_template": None,
                     "test": None, "test_supported": False},
}


def get_provider(key):
    return PROVIDERS.get(key)


def list_providers():
    return [{"key": k, **{kk: vv for kk, vv in v.items() if kk != "test"}} for k, v in PROVIDERS.items()]


def build_auth_header(provider_key, secret):
    """Given a provider key and its decrypted secret dict, return
    (header_name, header_value) to merge into a node's request headers —
    or (None, None) for providers (Telegram, generic) that don't inject
    via a header."""
    p = PROVIDERS.get(provider_key)
    if not p:
        return None, None
    if provider_key == "twilio":
        basic = base64.b64encode(f"{secret.get('account_sid','')}:{secret.get('auth_token','')}".encode()).decode()
        return "Authorization", f"Basic {basic}"
    if provider_key == "generic":
        return secret.get("header_name") or None, secret.get("header_value") or None
    if not p.get("auth_header") or not p.get("auth_template"):
        return None, None
    try:
        return p["auth_header"], p["auth_template"].format(**secret)
    except KeyError:
        return None, None


def test_connection(provider_key, secret):
    p = PROVIDERS.get(provider_key)
    if not p or not p.get("test_supported") or not p.get("test"):
        return None  # caller should treat this as "not verifiable", not failure
    try:
        return p["test"](secret)
    except requests.RequestException as e:
        return False, f"Could not reach {p['label']}: {e}"
    except Exception as e:
        return False, f"Unexpected error testing connection: {e}"
