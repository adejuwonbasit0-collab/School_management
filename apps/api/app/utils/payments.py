import stripe
import requests
from flask import current_app

CURRENCY_SYMBOLS = {"NGN": "₦", "USD": "$", "GBP": "£", "EUR": "€", "GHS": "GH₵", "KES": "KSh", "ZAR": "R"}

def get_site_currency():
    from app.utils.settings import get_setting
    return get_setting("site_currency", "NGN")

def currency_symbol(code=None):
    return CURRENCY_SYMBOLS.get(code or get_site_currency(), (code or get_site_currency()) + " ")

# Which currencies each gateway CAN technically process, at a protocol
# level. This is a TECHNICAL CEILING, not a guarantee your specific
# merchant account is approved for it — Paystack in particular will often
# silently process a transaction in your account's actual default
# currency (NGN) even when a different `currency` is passed, if that
# currency was never approved on your account, rather than cleanly
# rejecting it. That's exactly what caused "I asked for $30 and it showed
# ₦30" — the request looked fine, the API call succeeded, but the account
# wasn't actually enabled for USD, so Paystack fell back to NGN silently.
#
# Because gateways don't reliably self-report this, the real source of
# truth has to be the admin manually confirming, per gateway, which
# currencies their account is ACTUALLY approved for (Payment Config ->
# Enabled Currencies). Until the admin explicitly enables anything beyond
# the site's own base currency for a gateway, that gateway only ever
# charges in the base currency — the safe default — even if this
# technical ceiling would allow more.
GATEWAY_CURRENCIES = {
    "paystack":    {"NGN", "USD", "GHS", "ZAR", "KES"},
    "flutterwave": {"NGN", "USD", "GBP", "EUR", "GHS", "KES", "ZAR"},
    "stripe":      {"USD", "EUR", "GBP", "GHS", "ZAR"},  # Stripe does not settle in NGN or KES
    "paypal":      {"USD", "EUR", "GBP"},                # PayPal does not support NGN, GHS, KES, or ZAR at all
}

def admin_enabled_currencies(gateway):
    """The currencies the ADMIN has explicitly confirmed their gateway
    account is actually approved for (set in Payment Config). Defaults to
    just the site's base currency — the one thing every gateway here is
    definitely set up for, since it's what the business actually settles
    in — until the admin opts a gateway into more. This is intersected
    with GATEWAY_CURRENCIES (the technical ceiling) so a typo or stale
    setting can never enable something the gateway couldn't do anyway."""
    import json
    from app.utils.settings import get_setting
    base = get_site_currency()
    raw = get_setting(f"{gateway}_enabled_currencies_json")
    if not raw:
        return {base}
    try:
        admin_list = {c.upper() for c in json.loads(raw)}
    except (ValueError, TypeError):
        return {base}
    technical_ceiling = GATEWAY_CURRENCIES.get(gateway, set())
    return (admin_list & technical_ceiling) | {base}

def resolve_checkout_currency(gateway, preferred_currency):
    """Decides what currency to actually charge a customer in for a given
    gateway. If the visitor's chosen display currency is one the admin has
    confirmed this gateway account is actually approved for, use it —
    otherwise fall back to the site's base currency (converting the
    amount correctly) rather than attempting a charge the account isn't
    really set up for. Returns (currency_to_charge, matched_preference:
    bool) so the caller can tell the customer when their preferred
    currency wasn't available."""
    preferred = (preferred_currency or get_site_currency()).upper()
    if preferred in admin_enabled_currencies(gateway):
        return preferred, True
    return get_site_currency(), False

def reconcile_charged_currency(order, gateway_currency, gateway_amount_minor_or_major, is_minor_unit=True):
    """After a gateway confirms a payment, some gateways (Paystack in
    particular, on accounts not approved for the requested currency) will
    silently process it in a DIFFERENT currency than what was requested —
    the request succeeds, but what was actually charged doesn't match
    what we asked for. Call this right after a successful verify/capture,
    before marking the order paid, so Order.currency/amount (and
    therefore Financials/Analytics) always reflect what the customer was
    ACTUALLY charged, never just what we intended. Returns True if a
    mismatch was found and corrected (worth logging/telling the admin
    about), False if everything matched."""
    if not gateway_currency:
        return False
    gateway_currency = gateway_currency.upper()
    gateway_amount = float(gateway_amount_minor_or_major) / (100 if is_minor_unit else 1)
    mismatch = gateway_currency != (order.currency or "").upper()
    if mismatch:
        order.currency = gateway_currency
        order.amount = gateway_amount
    return mismatch

def get_active_gateway():
    from app.utils.settings import get_setting
    return get_setting("active_gateway", current_app.config.get("ACTIVE_GATEWAY", "stripe"))

def get_enabled_gateways():
    """Returns the list of gateways an admin has turned on — customers
    choose among these at checkout instead of being locked to one.
    Returns an empty list (not a fabricated default) if nothing has been
    explicitly configured yet, so checkout can show a clear message
    instead of silently redirecting to a gateway that was never set up."""
    from app.utils.settings import get_setting
    raw = get_setting("enabled_gateways", "")
    if raw:
        return [g.strip() for g in raw.split(",") if g.strip()]
    # Legacy single-gateway sites: only trust this if it was explicitly
    # saved (not the hardcoded config default), so a brand new/reset
    # database doesn't pretend "stripe" is ready to accept payments.
    legacy = get_setting("active_gateway", "")
    return [legacy] if legacy else []

def get_user_gateway_credentials(user_id, gateway):
    """The decrypted credentials a specific user has connected for a
    given gateway, or None if they haven't connected it. Used by
    Payment Links so customer money goes into the LINK OWNER's own
    account, not the site admin's."""
    from app.models.platform import UserPaymentGateway
    from app.utils.crypto import decrypt_json
    row = UserPaymentGateway.query.filter_by(user_id=user_id, gateway=gateway, active=True).first()
    if not row or not row.credentials_encrypted:
        return None
    try:
        return decrypt_json(row.credentials_encrypted)
    except Exception:
        current_app.logger.exception("Failed to decrypt gateway credentials for user %s / %s", user_id, gateway)
        return None

def get_user_enabled_gateways(user_id):
    """Gateway names a user has actually connected and left active."""
    from app.models.platform import UserPaymentGateway
    rows = UserPaymentGateway.query.filter_by(user_id=user_id, active=True).all()
    return [r.gateway for r in rows]

def _paystack_keys(credentials=None):
    if credentials and credentials.get("secret_key"):
        return credentials["secret_key"]
    from app.utils.settings import get_setting
    mode = get_setting("paystack_mode", "test")
    if mode == "live":
        return get_setting("paystack_live_secret_key", "") or current_app.config.get("PAYSTACK_SECRET_KEY", "")
    return get_setting("paystack_test_secret_key", "") or current_app.config.get("PAYSTACK_SECRET_KEY", "")

def create_paystack_transaction(title, price, user, callback_url, metadata=None, credentials=None, currency=None):
    """Initializes a Paystack transaction, returns the authorization data.
    Paystack amounts are in the smallest currency unit (kobo for NGN,
    cents for USD/GHS). Works for any payable thing — marketplace
    product, hosting subscription, etc — not just Product objects.
    Pass `credentials` (a dict with secret_key) to charge through a
    specific user's own connected Paystack account instead of the site
    admin's — used by the Payment Link Generator. Pass `currency` to
    charge in something other than the site's base currency — the
    caller is responsible for having already converted `price` into
    that currency and confirmed the gateway/account supports it
    (see resolve_checkout_currency)."""
    secret = _paystack_keys(credentials)
    if not secret:
        raise ValueError("Paystack secret key is not configured")
    currency = currency or get_site_currency()
    amount_minor = int(float(price) * 100)
    resp = requests.post(
        "https://api.paystack.co/transaction/initialize",
        headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
        json={
            "email": user.email, "amount": amount_minor, "currency": currency,
            "callback_url": callback_url,
            "metadata": metadata or {},
        },
        timeout=15,
    )
    data = resp.json()
    if not data.get("status"):
        raise ValueError(data.get("message", "Paystack initialization failed"))
    return data["data"]  # contains authorization_url, access_code, reference

def create_stripe_session(title, price, user, success_url, cancel_url, metadata=None, credentials=None, currency=None):
    stripe.api_key = (credentials or {}).get("secret_key") or current_app.config["STRIPE_SECRET_KEY"]
    currency = (currency or get_site_currency()).lower()
    amount = int(float(price) * 100)
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price_data": {"currency": currency, "product_data": {"name": title}, "unit_amount": amount}, "quantity": 1}],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata or {},
    )
    return session

def _flutterwave_key(credentials=None):
    if credentials and credentials.get("secret_key"):
        return credentials["secret_key"]
    from app.utils.settings import get_setting
    return get_setting("flutterwave_secret_key", "") or current_app.config.get("FLUTTERWAVE_SECRET_KEY", "")

def create_flutterwave_transaction(title, price, user, order_ref, redirect_url, credentials=None, currency=None):
    secret = _flutterwave_key(credentials)
    if not secret:
        raise ValueError("Flutterwave secret key is not configured")
    currency = currency or get_site_currency()
    resp = requests.post(
        "https://api.flutterwave.com/v3/payments",
        headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
        json={
            "tx_ref": order_ref, "amount": str(price), "currency": currency,
            "redirect_url": redirect_url,
            "customer": {"email": user.email, "name": user.name},
            "customizations": {"title": title},
        },
        timeout=15,
    )
    data = resp.json()
    if data.get("status") != "success":
        raise ValueError(data.get("message", "Flutterwave initialization failed"))
    return data["data"]["link"]

def verify_flutterwave_payment(transaction_id, credentials=None):
    secret = _flutterwave_key(credentials)
    if not secret:
        return None
    resp = requests.get(
        f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",
        headers={"Authorization": f"Bearer {secret}"},
        timeout=10,
    )
    if resp.status_code == 200:
        data = resp.json()
        if data.get("data", {}).get("status") == "successful":
            return data["data"]
    return None

def verify_paystack_payment(reference, credentials=None):
    secret = _paystack_keys(credentials)
    if not secret:
        return None
    resp = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers={"Authorization": f"Bearer {secret}"},
        timeout=10,
    )
    if resp.status_code == 200:
        data = resp.json()
        if data.get("data", {}).get("status") == "success":
            return data["data"]
    return None


def _paypal_creds(credentials=None):
    if credentials and credentials.get("client_id") and credentials.get("client_secret"):
        mode = credentials.get("mode", "live")
        base = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
        return credentials["client_id"], credentials["client_secret"], base
    from app.utils.settings import get_setting
    mode = get_setting("paypal_mode", "sandbox")
    client_id = get_setting("paypal_client_id", "")
    secret = get_setting("paypal_client_secret", "")
    base = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"
    return client_id, secret, base

def _paypal_token(credentials=None):
    client_id, secret, base = _paypal_creds(credentials)
    if not client_id or not secret:
        raise ValueError("PayPal client ID/secret is not configured")
    resp = requests.post(
        f"{base}/v1/oauth2/token",
        auth=(client_id, secret),
        data={"grant_type": "client_credentials"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"], base

def create_paypal_order(title, price, success_url, cancel_url, credentials=None, currency=None):
    """Creates a PayPal Order (v2) and returns the approval URL the
    customer is redirected to, plus the order id used to capture later."""
    token, base = _paypal_token(credentials)
    currency = currency or get_site_currency()
    resp = requests.post(
        f"{base}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "intent": "CAPTURE",
            "purchase_units": [{
                "description": title[:127],
                "amount": {"currency_code": currency, "value": f"{float(price):.2f}"},
            }],
            "application_context": {
                "return_url": success_url,
                "cancel_url": cancel_url,
                "user_action": "PAY_NOW",
            },
        },
        timeout=15,
    )
    data = resp.json()
    if resp.status_code not in (200, 201):
        raise ValueError(data.get("message", "PayPal order creation failed"))
    approval_url = next((l["href"] for l in data.get("links", []) if l.get("rel") == "approve"), None)
    if not approval_url:
        raise ValueError("PayPal did not return an approval link")
    return data["id"], approval_url

def capture_paypal_order(order_id, credentials=None):
    """Captures (finalizes) an approved PayPal order. Returns the capture
    data on success, or None if it wasn't actually completed."""
    token, base = _paypal_token(credentials)
    resp = requests.post(
        f"{base}/v2/checkout/orders/{order_id}/capture",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=15,
    )
    data = resp.json()
    if resp.status_code in (200, 201) and data.get("status") == "COMPLETED":
        return data
    return None
