"""
TOTP-based two-factor authentication helpers (Google Authenticator /
Authy / 1Password compatible — standard RFC 6238 TOTP, no proprietary
SDK or paid service needed).
"""
import io
import base64
import pyotp
import qrcode


def generate_secret():
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, email: str, issuer: str = "Bazillin Studio") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def get_qr_code_data_uri(uri: str) -> str:
    """Returns a base64 data: URI so the QR code can be shown inline
    with an <img> tag, no file storage needed."""
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def verify_totp_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code.strip().replace(" ", ""), valid_window=1)
