"""
Google Sheets integration for the Automation Studio's "Append Row to
Google Sheet" action.

Uses a Google Cloud **service account**, not full per-customer OAuth.
That's a deliberate, honest scoping choice:

  - Service account (this file): you create one JSON key, paste it once
    in Admin -> Settings -> Integrations, and share your target Google
    Sheet with that service account's email address (found inside the
    JSON as "client_email") the same way you'd share it with a person.
    That's the entire setup — no consent screen, no per-user login flow.

  - Full OAuth (NOT built here): would let each of YOUR customers connect
    their OWN Google account through a real Google consent screen. That
    needs a verified Google Cloud OAuth app (Google reviews it), a
    callback flow, and per-user token storage/refresh — a materially
    bigger, separate project. If you want that later, it's buildable,
    just not something to fake as a side effect of this feature.

Requires `google-auth` (added to requirements.txt) — it's used only to
build a signed JWT and exchange it for an access token; the actual
Sheets calls below are plain REST via `requests`, no heavy Google client
library needed.
"""
import json


def _get_access_token(service_account_json: str) -> str:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleAuthRequest

    if not service_account_json:
        raise RuntimeError(
            "No Google service account configured — paste the JSON key in "
            "Admin -> Settings -> Integrations first."
        )
    try:
        info = json.loads(service_account_json)
    except json.JSONDecodeError:
        raise RuntimeError("Google service account key isn't valid JSON — paste the whole key file contents.")

    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    creds.refresh(GoogleAuthRequest())
    return creds.token


def get_oauth_access_token(refresh_token: str, client_id: str, client_secret: str) -> str:
    """For a CLIENT's own connected Google account (real OAuth, see
    app/social/routes.py google_oauth_*), instead of your service account.
    Google access tokens only last ~1 hour, so every real call refreshes
    one from the stored refresh_token — nothing is cached across requests,
    keeping this stateless and simple."""
    import requests
    if not refresh_token:
        raise RuntimeError("This Google connection has no refresh token stored — reconnect it.")
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "grant_type": "refresh_token", "refresh_token": refresh_token,
        "client_id": client_id, "client_secret": client_secret,
    }, timeout=15)
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(data.get("error_description", data.get("error", "Google token refresh failed")))
    return data["access_token"]


def append_row_with_token(access_token: str, spreadsheet_id: str, sheet_range: str, values: list):
    """Same as append_row() but takes an already-obtained access token —
    shared by both the service-account path and the per-client OAuth path."""
    import requests
    if not spreadsheet_id:
        raise RuntimeError("No spreadsheet ID configured for this action.")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_range}:append"
    resp = requests.post(
        url,
        params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"values": [values]},
        timeout=15,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Google Sheets append failed ({resp.status_code}): {resp.text[:300]}")
    return resp.json()


def append_row(service_account_json: str, spreadsheet_id: str, sheet_range: str, values: list):
    """Appends one row of values to the given sheet/range using your site-
    wide service account. Google finds the next empty row itself —
    sheet_range just needs to point at the right sheet/columns, e.g.
    "Sheet1!A:Z"."""
    token = _get_access_token(service_account_json)
    return append_row_with_token(token, spreadsheet_id, sheet_range, values)


def test_connection(service_account_json: str, spreadsheet_id: str) -> str:
    """Round-trips a real API call to confirm the key is valid and the
    sheet is actually shared with the service account. Returns the
    spreadsheet's title on success, raises Google's real error otherwise
    (most common: 'The caller does not have permission' — means the
    sheet hasn't been shared with the service account's email yet)."""
    import requests
    token = _get_access_token(service_account_json)
    resp = requests.get(
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
        params={"fields": "properties.title"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code >= 400:
        try:
            msg = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
        except ValueError:
            msg = f"HTTP {resp.status_code}"
        raise RuntimeError(msg)
    return resp.json().get("properties", {}).get("title", "Untitled Sheet")
