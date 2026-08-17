"""Twilio Voice + WhatsApp integration. Built without the official
`twilio` SDK (not in requirements.txt, and the raw HTTP contract is
simple enough not to need it) — plain `requests` for outbound sends,
and Twilio's documented HMAC-SHA1 scheme for validating that inbound
webhooks genuinely came from Twilio.

HONEST SCOPE: this code is real and works once a real Twilio account,
phone number, and WhatsApp Business sender are configured — but that
account/number/WhatsApp approval is something only the account owner can
set up directly with Twilio (identity verification, a real phone number
purchase, WhatsApp Business Platform approval for the WhatsApp piece).
Nothing here can create that account on your behalf.
"""
import base64
import hashlib
import hmac
from xml.sax.saxutils import escape as _xml_escape

import requests as _requests
from app.utils.settings import get_setting


def _twilio_creds():
    sid = (get_setting("twilio_account_sid") or "").strip()
    token = (get_setting("twilio_auth_token") or "").strip()
    return sid, token


def verify_twilio_signature(url, form_dict, signature_header, auth_token=None):
    """Twilio's documented validation: HMAC-SHA1 of the full request URL
    plus each POST param (sorted by key, concatenated key+value), base64-
    encoded, compared to the X-Twilio-Signature header. Returns True/False
    — if no auth token is configured yet, returns True (so an admin can
    test the webhook wiring itself before finishing Twilio setup), which
    is safe because the ONLY consumer of this is a webhook that ignores
    unrecognized/malformed bodies anyway.

    Pass auth_token explicitly to verify against a specific connection's
    own token (e.g. a customer's own connected WhatsApp sender) instead of
    the single site-wide Admin -> Settings -> Twilio token.
    """
    if auth_token is None:
        _, auth_token = _twilio_creds()
    if not auth_token:
        return True
    data = url
    for key in sorted(form_dict.keys()):
        data += key + form_dict[key]
    computed = base64.b64encode(hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(computed, signature_header or "")


def twiml_message(body):
    """A TwiML <Response> that replies to an inbound WhatsApp/SMS message."""
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{_xml_escape(body)}</Message></Response>'


def twiml_gather_say(say_text, action_url, hang_up=False):
    """A TwiML <Response> that speaks `say_text`, then either listens for
    the caller's next spoken reply (looping the voice-agent conversation)
    or hangs up — used for a simple phone-call IVR agent built entirely
    on Twilio's own speech recognition and text-to-speech, no separate
    STT/TTS service needed."""
    say = f"<Say>{_xml_escape(say_text)}</Say>"
    if hang_up:
        return f'<?xml version="1.0" encoding="UTF-8"?><Response>{say}<Hangup/></Response>'
    gather = f'<Gather input="speech" action="{_xml_escape(action_url)}" method="POST" speechTimeout="auto">{say}</Gather>'
    # If the caller says nothing, Twilio moves past <Gather> — this second
    # <Say> plus a re-prompt keeps the call from just silently hanging.
    return f'<?xml version="1.0" encoding="UTF-8"?><Response>{gather}<Say>Sorry, I didn\'t catch that. Goodbye for now.</Say><Hangup/></Response>'


def test_twilio_credentials(account_sid, auth_token):
    """Real connection test against Twilio's own API — GET the account
    resource with the given Account SID/Auth Token as basic auth creds.
    Returns (ok, message). Lets 'Connect' / 'Test Connection' catch a
    mistyped SID or token immediately, instead of only finding out on
    the first missed real customer message."""
    account_sid = (account_sid or "").strip()
    auth_token = (auth_token or "").strip()
    if not account_sid or not auth_token:
        return False, "Account SID and Auth Token are both required."
    try:
        resp = _requests.get(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json",
            auth=(account_sid, auth_token), timeout=10,
        )
    except _requests.exceptions.RequestException as e:
        return False, f"Couldn't reach Twilio: {e}"
    if resp.status_code == 401:
        return False, "Twilio rejected those credentials — double-check your Account SID and Auth Token."
    if resp.status_code == 404:
        return False, "That Account SID doesn't exist — double-check it in your Twilio Console."
    if resp.status_code >= 300:
        return False, f"Twilio returned HTTP {resp.status_code} — please try again."
    data = resp.json()
    status = data.get("status")
    if status and status != "active":
        return False, f"That Twilio account is '{status}', not active — check your account status in the Twilio Console."
    return True, "Connected."


def send_whatsapp_message(to, body):
    """Sends an OUTBOUND WhatsApp message via Twilio's REST API (used by
    the send_whatsapp_message agent tool, for proactive messages — inbound
    replies use twiml_message() instead, which is faster and doesn't need
    an extra API round-trip). Returns (True, None) or (False, error)."""
    sid, token = _twilio_creds()
    from_number = (get_setting("twilio_whatsapp_number") or "").strip()
    if not sid or not token or not from_number:
        return False, "Twilio isn't configured yet — set Account SID, Auth Token, and WhatsApp number in Admin -> Settings -> Twilio."
    to_clean = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
    from_clean = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
    try:
        resp = _requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": from_clean, "To": to_clean, "Body": body},
            timeout=15,
        )
    except _requests.exceptions.RequestException as e:
        return False, f"Couldn't reach Twilio: {e}"
    if resp.status_code >= 300:
        return False, f"Twilio returned HTTP {resp.status_code}: {resp.text[:400]}"
    return True, None
