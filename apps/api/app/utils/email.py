import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app, render_template_string
import requests as _requests


def _live_smtp_settings():
    """Admin -> Settings -> Email saves mail_server/mail_port/mail_username/
    mail_password to the database (SiteSetting), but Flask-Mail's extension
    only reads MAIL_* from the environment once at process boot -- so those
    saved values were previously never actually used. This reads the DB
    settings fresh on every send, falling back to the env-based app.config
    only if the admin hasn't configured anything in the dashboard yet."""
    from app.utils.settings import get_setting
    host = get_setting("mail_server") or current_app.config.get("MAIL_SERVER", "")
    port = int(get_setting("mail_port") or current_app.config.get("MAIL_PORT", 587) or 587)
    username = get_setting("mail_username") or current_app.config.get("MAIL_USERNAME", "")
    password = get_setting("mail_password") or current_app.config.get("MAIL_PASSWORD", "")
    use_tls_raw = get_setting("mail_use_tls")
    use_tls = (use_tls_raw.lower() in ("true", "1", "yes", "on")) if use_tls_raw else current_app.config.get("MAIL_USE_TLS", True)
    sender = get_setting("mail_default_sender") or current_app.config.get("MAIL_DEFAULT_SENDER") or username or "noreply@bazillin.studio"
    return host, port, username, password, use_tls, sender


def _send_via_smtp(to, recipients, subject, body_html, body_text, from_name, reply_to):
    host, port, username, password, use_tls, sender = _live_smtp_settings()
    if not host or not username or not password:
        current_app.logger.error(
            "Email send skipped: SMTP is not configured. Set SMTP Host/Username/Password "
            "in Admin -> Settings -> Email."
        )
        return False
    from_display = f'"{from_name}" <{sender}>' if from_name else sender
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        # Actual SMTP relay is always this one account (single set of
        # credentials), so the envelope sender can't be swapped per
        # customer — but the DISPLAY name can, and Reply-To can point
        # replies straight at the customer instead of you. That's what
        # lets a customer's automated emails look like they're from
        # their own business without needing their own SMTP account.
        msg["From"] = from_display
        if reply_to:
            msg["Reply-To"] = reply_to
        msg["To"] = ", ".join(recipients)
        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(host, port, timeout=15) as server:
            if use_tls:
                server.starttls()
            server.login(username, password)
            # msg.as_bytes() (not as_string()) is what avoids the
            # 'ascii' codec can't encode character ... crash — as_string()
            # flattens the message through Python's default str codec,
            # which chokes the moment body_html/body_text contains any
            # non-ASCII character (curly quotes, →, emoji, names with
            # accents, etc). as_bytes() lets each MIME part's own charset
            # (set to utf-8 above) handle its own encoding correctly.
            server.sendmail(sender, recipients, msg.as_bytes())
        return True
    except Exception as e:
        current_app.logger.error(f"Email send failed via SMTP ({host}:{port}): {e}")
        return False


def _send_via_sendgrid(to, recipients, subject, body_html, body_text, from_name, reply_to):
    from app.utils.settings import get_setting
    api_key = (get_setting("sendgrid_api_key") or "").strip()
    sender = (get_setting("mail_default_sender") or "noreply@bazillin.studio").strip()
    if not api_key:
        current_app.logger.error("Email send skipped: SendGrid selected but sendgrid_api_key isn't set.")
        return False
    payload = {
        "personalizations": [{"to": [{"email": r} for r in recipients]}],
        "from": {"email": sender, "name": from_name} if from_name else {"email": sender},
        "subject": subject,
        "content": [{"type": "text/html", "value": body_html}],
    }
    if reply_to:
        payload["reply_to"] = {"email": reply_to}
    try:
        resp = _requests.post("https://api.sendgrid.com/v3/mail/send",
                               headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                               json=payload, timeout=15)
        if resp.status_code >= 400:
            current_app.logger.error(f"SendGrid send failed: HTTP {resp.status_code}: {resp.text[:500]}")
            return False
        return True
    except _requests.exceptions.RequestException as e:
        current_app.logger.error(f"SendGrid send failed (network): {e}")
        return False


def _send_via_mailgun(to, recipients, subject, body_html, body_text, from_name, reply_to):
    from app.utils.settings import get_setting
    api_key = (get_setting("mailgun_api_key") or "").strip()
    domain = (get_setting("mailgun_domain") or "").strip()
    sender = (get_setting("mail_default_sender") or "noreply@bazillin.studio").strip()
    if not api_key or not domain:
        current_app.logger.error("Email send skipped: Mailgun selected but mailgun_api_key/mailgun_domain isn't set.")
        return False
    from_field = f"{from_name} <{sender}>" if from_name else sender
    data = {"from": from_field, "to": recipients, "subject": subject, "html": body_html}
    if body_text:
        data["text"] = body_text
    if reply_to:
        data["h:Reply-To"] = reply_to
    try:
        resp = _requests.post(f"https://api.mailgun.net/v3/{domain}/messages",
                               auth=("api", api_key), data=data, timeout=15)
        if resp.status_code >= 400:
            current_app.logger.error(f"Mailgun send failed: HTTP {resp.status_code}: {resp.text[:500]}")
            return False
        return True
    except _requests.exceptions.RequestException as e:
        current_app.logger.error(f"Mailgun send failed (network): {e}")
        return False


def _send_via_postmark(to, recipients, subject, body_html, body_text, from_name, reply_to):
    from app.utils.settings import get_setting
    token = (get_setting("postmark_server_token") or "").strip()
    sender = (get_setting("mail_default_sender") or "noreply@bazillin.studio").strip()
    if not token:
        current_app.logger.error("Email send skipped: Postmark selected but postmark_server_token isn't set.")
        return False
    from_field = f"{from_name} <{sender}>" if from_name else sender
    payload = {"From": from_field, "To": ", ".join(recipients), "Subject": subject, "HtmlBody": body_html}
    if body_text:
        payload["TextBody"] = body_text
    if reply_to:
        payload["ReplyTo"] = reply_to
    try:
        resp = _requests.post("https://api.postmarkapp.com/email",
                               headers={"X-Postmark-Server-Token": token, "Content-Type": "application/json", "Accept": "application/json"},
                               json=payload, timeout=15)
        if resp.status_code >= 400:
            current_app.logger.error(f"Postmark send failed: HTTP {resp.status_code}: {resp.text[:500]}")
            return False
        return True
    except _requests.exceptions.RequestException as e:
        current_app.logger.error(f"Postmark send failed (network): {e}")
        return False


def _send_via_resend(to, recipients, subject, body_html, body_text, from_name, reply_to):
    from app.utils.settings import get_setting
    api_key = (get_setting("resend_api_key") or "").strip()
    sender = (get_setting("mail_default_sender") or "noreply@bazillin.studio").strip()
    if not api_key:
        current_app.logger.error("Email send skipped: Resend selected but resend_api_key isn't set.")
        return False
    from_field = f"{from_name} <{sender}>" if from_name else sender
    payload = {"from": from_field, "to": recipients, "subject": subject, "html": body_html}
    if reply_to:
        payload["reply_to"] = reply_to
    try:
        resp = _requests.post("https://api.resend.com/emails",
                               headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                               json=payload, timeout=15)
        if resp.status_code >= 400:
            current_app.logger.error(f"Resend send failed: HTTP {resp.status_code}: {resp.text[:500]}")
            return False
        return True
    except _requests.exceptions.RequestException as e:
        current_app.logger.error(f"Resend send failed (network): {e}")
        return False


def _send_via_mailchimp_transactional(to, recipients, subject, body_html, body_text, from_name, reply_to):
    """Mailchimp's transactional (single-email) sending is actually a
    separate product, Mandrill — Mailchimp's own audience/campaign API
    doesn't send one-off transactional emails like a signup or receipt at
    all. Told plainly here rather than silently pretending the main
    Mailchimp API covers this."""
    from app.utils.settings import get_setting
    api_key = (get_setting("mailchimp_api_key") or "").strip()
    sender = (get_setting("mail_default_sender") or "noreply@bazillin.studio").strip()
    if not api_key:
        current_app.logger.error("Email send skipped: Mailchimp Transactional selected but mailchimp_api_key isn't set.")
        return False
    payload = {
        "key": api_key,
        "message": {
            "html": body_html,
            "subject": subject,
            "from_email": sender,
            "from_name": from_name or "",
            "to": [{"email": r, "type": "to"} for r in recipients],
        },
    }
    if reply_to:
        payload["message"]["headers"] = {"Reply-To": reply_to}
    try:
        resp = _requests.post("https://mandrillapp.com/api/1.0/messages/send.json", json=payload, timeout=15)
        if resp.status_code >= 400:
            current_app.logger.error(f"Mailchimp Transactional send failed: HTTP {resp.status_code}: {resp.text[:500]}")
            return False
        results = resp.json() if resp.content else []
        if isinstance(results, list) and any(r.get("status") == "rejected" for r in results):
            current_app.logger.error(f"Mailchimp Transactional rejected the message: {results}")
            return False
        return True
    except _requests.exceptions.RequestException as e:
        current_app.logger.error(f"Mailchimp Transactional send failed (network): {e}")
        return False


_PROVIDERS = {
    "smtp": _send_via_smtp,
    "sendgrid": _send_via_sendgrid,
    "mailgun": _send_via_mailgun,
    "postmark": _send_via_postmark,
    "resend": _send_via_resend,
    "mailchimp": _send_via_mailchimp_transactional,
}


def test_smtp_credentials(host, port, username, password, use_tls=True):
    """Real connection + login test against the given SMTP server —
    same 'catch a mistake at Connect time, not on the first missed
    customer email' pattern as test_twilio_credentials(). Doesn't send
    anything; NOOP/QUIT-only against a live connection.
    Returns (ok, message)."""
    host = (host or "").strip()
    username = (username or "").strip()
    if not host or not username or not password:
        return False, "Host, username, and password are all required."
    try:
        port = int(port or 587)
    except (TypeError, ValueError):
        return False, "Port must be a number."
    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_tls:
                server.starttls()
            server.login(username, password)
    except smtplib.SMTPAuthenticationError:
        return False, "That server rejected the username/password — double-check your credentials."
    except smtplib.SMTPConnectError:
        return False, f"Couldn't connect to {host}:{port} — double-check the host and port."
    except (smtplib.SMTPException, OSError, TimeoutError) as e:
        return False, f"Couldn't connect: {e}"
    return True, "Connected and authenticated successfully."


def _send_via_custom_smtp(creds, to, recipients, subject, body_html, body_text, from_name, reply_to):
    """Real per-seller sending — mail actually originates from the
    funnel owner's own SMTP account, not the platform's. This is the
    genuine version of the earlier From-name/Reply-To cosmetic
    override: here the envelope sender IS their address too."""
    host = creds.get("host", "")
    port = int(creds.get("port") or 587)
    username = creds.get("username", "")
    password = creds.get("password", "")
    use_tls = creds.get("use_tls", True)
    sender = creds.get("from_email") or username
    if not host or not username or not password:
        current_app.logger.error("Custom SMTP send skipped: incomplete credentials.")
        return False
    from_display = f'"{from_name}" <{sender}>' if from_name else sender
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_display
        if reply_to:
            msg["Reply-To"] = reply_to
        msg["To"] = ", ".join(recipients)
        if body_text:
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))
        with smtplib.SMTP(host, port, timeout=15) as server:
            if use_tls:
                server.starttls()
            server.login(username, password)
            server.sendmail(sender, recipients, msg.as_bytes())
        return True
    except Exception as e:
        current_app.logger.error(f"Email send failed via custom SMTP ({host}:{port}): {e}")
        return False


def send_email(to, subject, body_html, body_text=None, from_name=None, reply_to=None, smtp_override=None):
    """Sends an email through whichever provider is configured in Admin ->
    Settings -> Email (default: SMTP, unchanged from before). All 6
    providers share the same signature and the same True/False + logged-
    error contract, so every existing caller in the app works unmodified
    no matter which provider an admin picks.

    smtp_override: optional dict (host/port/username/password/from_email/
    use_tls) — when given, bypasses the platform provider entirely and
    sends through THAT SMTP account instead. This is what lets a funnel
    owner's receipts genuinely originate from their own mail account
    rather than the platform's shared relay (see UserFunnel.get_smtp_credentials()).

    Note on "Nodemailer" (something the user asked to add as an option):
    Nodemailer is a Node.js *library*, not an email service — it doesn't
    have an API a Python backend could call. Its most common real-world
    use is sending mail through plain SMTP (already supported here as the
    "smtp" provider, works with Gmail/Outlook/any SMTP host) or through
    one of the provider APIs above. Listing it as its own option would
    have been decorative — it has no functional difference from "smtp"
    from this side.
    """
    from app.utils.settings import get_setting
    recipients = [to] if isinstance(to, str) else list(to)

    header_img = get_setting("email_header_image")
    if header_img:
        body_html = (
            f'<div style="text-align:center;padding:20px 0;background:#0a0a0a">'
            f'<img src="{header_img}" alt="" style="max-height:56px;max-width:280px"/></div>'
            f'{body_html}'
        )

    if smtp_override:
        return _send_via_custom_smtp(smtp_override, to, recipients, subject, body_html, body_text, from_name, reply_to)

    provider = (get_setting("email_provider") or "smtp").strip().lower()
    if provider not in _PROVIDERS:
        current_app.logger.error(f"Email send skipped: unknown email_provider '{provider}', falling back to smtp.")
        provider = "smtp"
    sender_fn = _PROVIDERS[provider]
    return sender_fn(to, recipients, subject, body_html, body_text, from_name, reply_to)


def send_template_email(to, template_id, context=None):
    try:
        from app.models.core import EmailTemplate
        tpl = EmailTemplate.query.filter_by(template_id=template_id, active=True).first()
        if not tpl:
            return False
        ctx = context or {}
        subject = render_template_string(tpl.subject, **ctx)
        body    = render_template_string(tpl.body,    **ctx)
        return send_email(to, subject, body)
    except Exception as e:
        current_app.logger.error(f"Template email failed: {e}")
        return False
