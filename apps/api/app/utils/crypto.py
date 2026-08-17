"""Encrypts sensitive JSON blobs (payment gateway API keys/secrets) at
rest, so a database dump/leak doesn't hand out every customer's
payment credentials in plaintext.

Key is derived from the app's SECRET_KEY, so it stays stable across
restarts without needing a separate secret to manage — but it also
means: if SECRET_KEY ever changes, previously-stored credentials
become undecryptable and users will need to reconnect their gateways.
Keep SECRET_KEY stable in production (it already needs to be, for
session/cookie security).
"""
import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def _fernet():
    secret = current_app.config.get("SECRET_KEY", "")
    if not secret:
        raise RuntimeError("SECRET_KEY is not set — cannot encrypt/decrypt credentials.")
    # Fernet needs a urlsafe-base64-encoded 32-byte key; derive one
    # deterministically from SECRET_KEY so we don't need a new secret.
    derived = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(derived)
    return Fernet(key)


def encrypt_json(data: dict) -> str:
    payload = json.dumps(data or {}).encode("utf-8")
    return _fernet().encrypt(payload).decode("utf-8")


def decrypt_json(token: str) -> dict:
    if not token:
        return {}
    try:
        raw = _fernet().decrypt(token.encode("utf-8"))
    except InvalidToken:
        raise ValueError("Could not decrypt credentials — SECRET_KEY may have changed.")
    return json.loads(raw.decode("utf-8"))


def mask_secret(value: str, keep: int = 4) -> str:
    """For display only — never send full secrets back to the browser."""
    if not value:
        return ""
    if len(value) <= keep:
        return "•" * len(value)
    return "•" * (len(value) - keep) + value[-keep:]
