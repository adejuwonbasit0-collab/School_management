"""
Public webhook endpoints the social platforms POST to. Each channel has its
own random `webhook_secret` baked into its URL (see SocialChannel.ensure_secret)
so these endpoints don't need auth headers — the secret IS the auth, same
approach Stripe/GitHub webhooks use with signing secrets, just simpler since
we don't need signature verification for the two platforms that don't
support it out of the box (Telegram has no signing; WhatsApp/Facebook use
X-Hub-Signature-256, verified below when an app_secret is configured).
"""
import hashlib
import hmac
import secrets as secrets_lib
from flask import Blueprint, request, jsonify, abort, redirect, url_for, render_template, flash, session, current_app
from flask_login import login_required, current_user

social_bp = Blueprint("social", __name__)


def _get_channel(platform, secret):
    from app.models.platform import SocialChannel
    channel = SocialChannel.query.filter_by(platform=platform, webhook_secret=secret, active=True).first()
    if not channel:
        abort(404)
    return channel


def _verify_meta_signature(channel):
    """If the admin configured an app secret, verify X-Hub-Signature-256 so
    only real Meta payloads are processed. Optional because getting the app
    secret right during setup is fiddly and we'd rather a channel work
    without it than silently reject everything until it's perfect —
    the webhook_secret in the URL already keeps randoms out."""
    app_secret = (channel.credentials or {}).get("app_secret")
    if not app_secret:
        return True
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not sig.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig[7:], expected)


# ─────────────────────────────── Telegram ───────────────────────────────

@social_bp.route("/webhooks/telegram/<secret>", methods=["POST"])
def telegram_webhook(secret):
    from app.utils.social_bots import handle_inbound_message
    channel = _get_channel("telegram", secret)
    update = request.get_json(silent=True) or {}
    msg = update.get("message") or update.get("edited_message")
    if msg and msg.get("text"):
        chat_id = msg["chat"]["id"]
        sender_name = msg.get("from", {}).get("first_name") or msg.get("from", {}).get("username")
        handle_inbound_message(channel, str(chat_id), msg["text"], sender_name)
    # Telegram only cares about a 200 — content is ignored, but a non-2xx
    # response makes it retry the same update repeatedly.
    return jsonify({"ok": True})


# ─────────────────────────────── WhatsApp ────────────────────────────────

@social_bp.route("/webhooks/whatsapp/<secret>", methods=["GET"])
def whatsapp_verify(secret):
    from app.models.platform import SocialChannel
    channel = SocialChannel.query.filter_by(platform="whatsapp", webhook_secret=secret).first()
    if not channel:
        abort(404)
    verify_token = (channel.credentials or {}).get("verify_token", "")
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == verify_token:
        return request.args.get("hub.challenge", ""), 200
    return "Verification failed", 403


@social_bp.route("/webhooks/whatsapp/<secret>", methods=["POST"])
def whatsapp_webhook(secret):
    from app.utils.social_bots import handle_inbound_message
    channel = _get_channel("whatsapp", secret)
    if not _verify_meta_signature(channel):
        abort(403)
    data = request.get_json(silent=True) or {}
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    if msg.get("type") != "text":
                        continue
                    from_number = msg["from"]
                    contact_name = None
                    for c in value.get("contacts", []):
                        if c.get("wa_id") == from_number:
                            contact_name = c.get("profile", {}).get("name")
                    handle_inbound_message(channel, from_number, msg["text"]["body"], contact_name)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("WhatsApp webhook parse failed")
    return jsonify({"ok": True})


# ────────────────────────────── Facebook ─────────────────────────────────

@social_bp.route("/webhooks/facebook/<secret>", methods=["GET"])
def facebook_verify(secret):
    from app.models.platform import SocialChannel
    channel = SocialChannel.query.filter_by(platform="facebook", webhook_secret=secret).first()
    if not channel:
        abort(404)
    verify_token = (channel.credentials or {}).get("verify_token", "")
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == verify_token:
        return request.args.get("hub.challenge", ""), 200
    return "Verification failed", 403


@social_bp.route("/webhooks/facebook/<secret>", methods=["POST"])
def facebook_webhook(secret):
    from app.utils.social_bots import handle_inbound_message
    channel = _get_channel("facebook", secret)
    if not _verify_meta_signature(channel):
        abort(403)
    data = request.get_json(silent=True) or {}
    try:
        for entry in data.get("entry", []):
            for messaging in entry.get("messaging", []):
                msg = messaging.get("message")
                if not msg or msg.get("is_echo") or not msg.get("text"):
                    continue
                psid = messaging["sender"]["id"]
                handle_inbound_message(channel, psid, msg["text"], None)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Facebook webhook parse failed")
    return jsonify({"ok": True})


# ────────────────────────────── Instagram ────────────────────────────────
# Instagram Direct messages are configured as a webhook on the same linked
# Facebook Page (Meta routes them through the Page's app subscription), but
# arrive with "object": "instagram" instead of "page" — kept as its own
# channel/platform here so auto-reply rules and the inbox can be scoped
# per-platform instead of lumped in with Messenger.

@social_bp.route("/webhooks/instagram/<secret>", methods=["GET"])
def instagram_verify(secret):
    from app.models.platform import SocialChannel
    channel = SocialChannel.query.filter_by(platform="instagram", webhook_secret=secret).first()
    if not channel:
        abort(404)
    verify_token = (channel.credentials or {}).get("verify_token", "")
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == verify_token:
        return request.args.get("hub.challenge", ""), 200
    return "Verification failed", 403


@social_bp.route("/webhooks/instagram/<secret>", methods=["POST"])
def instagram_webhook(secret):
    from app.utils.social_bots import handle_inbound_message
    channel = _get_channel("instagram", secret)
    if not _verify_meta_signature(channel):
        abort(403)
    data = request.get_json(silent=True) or {}
    try:
        for entry in data.get("entry", []):
            for messaging in entry.get("messaging", []):
                msg = messaging.get("message")
                if not msg or msg.get("is_echo") or not msg.get("text"):
                    continue
                igsid = messaging["sender"]["id"]
                handle_inbound_message(channel, igsid, msg["text"], None)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Instagram webhook parse failed")
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────────────────
# Real OAuth "Connect your account" flow for CLIENTS. The whole point:
# the client logs into their OWN Facebook, approves access on Facebook's
# own consent screen, and the token comes back to us directly — nobody
# on our side (not you, not the platform) ever sees or handles their
# raw credentials, unlike the admin-side manual paste-a-token flow.
# ─────────────────────────────────────────────────────────────────────────

def _oauth_serializer():
    from itsdangerous import URLSafeTimedSerializer
    return URLSafeTimedSerializer(current_app.secret_key)


def _external_url(endpoint, **kwargs):
    from flask import request, url_for
    from app.utils.settings import get_setting
    app_url = (get_setting("app_url") or "").strip()
    url = url_for(endpoint, _external=True, **kwargs)
    if app_url.startswith("https://") and url.startswith("http://"):
        url = "https://" + url.split("://", 1)[1]
    elif request.headers.get("X-Forwarded-Proto") == "https" and url.startswith("http://"):
        url = "https://" + url.split("://", 1)[1]
    return url


@social_bp.route("/connect/facebook/start")
@login_required
def facebook_oauth_start():
    from app.utils.settings import get_setting
    from app.models.platform import ClientProject

    project_id = request.args.get("project_id", type=int)
    project = ClientProject.query.get_or_404(project_id)
    if project.client_id != current_user.id and not current_user.is_admin():
        abort(403)

    app_id = get_setting("facebook_app_id")
    if not app_id:
        flash("Facebook connections aren't set up on this site yet — the site admin needs to add a Facebook App ID in Settings first.", "warning")
        return redirect(url_for("dashboard.home"))

    state = _oauth_serializer().dumps({"project_id": project_id, "user_id": current_user.id})
    redirect_uri = _external_url("social.facebook_oauth_callback")
    scopes = "pages_show_list,pages_manage_posts,pages_messaging,pages_read_engagement,instagram_basic,instagram_content_publish"
    auth_url = (
        "https://www.facebook.com/v19.0/dialog/oauth"
        f"?client_id={app_id}&redirect_uri={redirect_uri}&scope={scopes}&state={state}"
    )
    return redirect(auth_url)


@social_bp.route("/connect/facebook/callback")
@login_required
def facebook_oauth_callback():
    from itsdangerous import BadSignature, SignatureExpired
    from app.utils.settings import get_setting
    import requests

    error = request.args.get("error")
    if error:
        flash(f"Facebook connection was cancelled: {request.args.get('error_description', error)}", "warning")
        return redirect(url_for("dashboard.home"))

    code = request.args.get("code")
    state = request.args.get("state", "")
    try:
        data = _oauth_serializer().loads(state, max_age=600)
    except (BadSignature, SignatureExpired):
        abort(400)
    if data.get("user_id") != current_user.id:
        abort(403)
    project_id = data["project_id"]

    app_id = get_setting("facebook_app_id")
    app_secret = get_setting("facebook_app_secret")
    redirect_uri = _external_url("social.facebook_oauth_callback")

    token_resp = requests.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
        "client_id": app_id, "client_secret": app_secret,
        "redirect_uri": redirect_uri, "code": code,
    }, timeout=15).json()
    if "error" in token_resp:
        flash(f"Facebook connection failed: {token_resp['error'].get('message')}", "danger")
        return redirect(url_for("dashboard.home"))
    short_token = token_resp["access_token"]

    # Exchange for a long-lived user token so the Page tokens derived from
    # it don't expire after a couple of hours.
    long_resp = requests.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": app_secret,
        "fb_exchange_token": short_token,
    }, timeout=15).json()
    long_token = long_resp.get("access_token", short_token)

    pages_resp = requests.get("https://graph.facebook.com/v19.0/me/accounts", params={
        "access_token": long_token,
    }, timeout=15).json()
    pages = pages_resp.get("data", [])
    if not pages:
        flash("Facebook connected, but no Pages were found — you need to be an admin of a Facebook Page to connect it.", "warning")
        return redirect(url_for("dashboard.home"))

    session["fb_oauth_pages"] = [{"id": p["id"], "name": p["name"], "access_token": p["access_token"]} for p in pages]
    session["fb_oauth_project_id"] = project_id

    if len(pages) == 1:
        return redirect(url_for("social.facebook_oauth_select", page_id=pages[0]["id"]))
    return render_template("social/facebook_select_page.html", pages=pages)


@social_bp.route("/connect/facebook/select/<page_id>")
@login_required
def facebook_oauth_select(page_id):
    from app.extensions import db
    from app.models.platform import SocialChannel
    from app.utils.social_bots import test_facebook_connection
    import requests

    pages = session.get("fb_oauth_pages") or []
    project_id = session.get("fb_oauth_project_id")
    page = next((p for p in pages if p["id"] == page_id), None)
    if not page or not project_id:
        abort(400)

    channel = SocialChannel.query.filter_by(platform="facebook", client_project_id=project_id).first()
    if not channel:
        channel = SocialChannel(platform="facebook", client_project_id=project_id)
        db.session.add(channel)
    channel.label = f"{page['name']} (Facebook)"
    channel.credentials = {
        "page_access_token": page["access_token"],
        "page_id": page["id"],
        "verify_token": secrets_lib.token_urlsafe(16),
        "connected_via": "oauth",
    }
    channel.ensure_secret()
    try:
        test_facebook_connection(page["access_token"])
        channel.connected = True
        channel.connection_error = None
    except Exception as e:
        channel.connected = False
        channel.connection_error = str(e)
    channel.active = True
    db.session.commit()

    # Bonus: if this Page has a linked Instagram Business account, connect
    # that too in the same step — same token, no extra consent needed.
    try:
        ig_lookup = requests.get(f"https://graph.facebook.com/v19.0/{page['id']}", params={
            "fields": "instagram_business_account", "access_token": page["access_token"],
        }, timeout=10).json()
        ig_account_id = (ig_lookup.get("instagram_business_account") or {}).get("id")
        if ig_account_id:
            ig_channel = SocialChannel.query.filter_by(platform="instagram", client_project_id=project_id).first()
            if not ig_channel:
                ig_channel = SocialChannel(platform="instagram", client_project_id=project_id)
                db.session.add(ig_channel)
            ig_channel.label = f"{page['name']} (Instagram)"
            ig_channel.credentials = {
                "page_access_token": page["access_token"],
                "ig_user_id": ig_account_id,
                "connected_via": "oauth",
            }
            ig_channel.ensure_secret()
            ig_channel.connected = True
            ig_channel.active = True
            db.session.commit()
    except Exception:
        pass  # Instagram linking is a bonus, not required — Facebook connection above already succeeded

    session.pop("fb_oauth_pages", None)
    session.pop("fb_oauth_project_id", None)
    flash(f'Connected "{page["name"]}" — you can see it in My Bots now.', "success")
    return redirect(url_for("dashboard.home"))


@social_bp.route("/connect/linkedin/start")
@login_required
def linkedin_oauth_start():
    from app.utils.settings import get_setting
    from app.models.platform import ClientProject
    from urllib.parse import quote

    project_id = request.args.get("project_id", type=int)
    project = ClientProject.query.get_or_404(project_id)
    if project.client_id != current_user.id and not current_user.is_admin():
        abort(403)

    client_id = get_setting("linkedin_client_id")
    if not client_id:
        flash("LinkedIn connections aren't set up on this site yet — the site admin needs to add a LinkedIn Client ID in Settings first.", "warning")
        return redirect(url_for("dashboard.home"))

    state = _oauth_serializer().dumps({"project_id": project_id, "user_id": current_user.id})
    redirect_uri = _external_url("social.linkedin_oauth_callback")
    scopes = "openid profile w_member_social"
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code&client_id={client_id}&redirect_uri={quote(redirect_uri, safe='')}"
        f"&scope={quote(scopes)}&state={state}"
    )
    return redirect(auth_url)


@social_bp.route("/connect/linkedin/callback")
@login_required
def linkedin_oauth_callback():
    from itsdangerous import BadSignature, SignatureExpired
    from app.utils.settings import get_setting
    from app.extensions import db
    from app.models.platform import SocialChannel
    import requests

    error = request.args.get("error")
    if error:
        flash(f"LinkedIn connection was cancelled: {request.args.get('error_description', error)}", "warning")
        return redirect(url_for("dashboard.home"))

    code = request.args.get("code")
    state = request.args.get("state", "")
    try:
        data = _oauth_serializer().loads(state, max_age=600)
    except (BadSignature, SignatureExpired):
        abort(400)
    if data.get("user_id") != current_user.id:
        abort(403)
    project_id = data["project_id"]

    client_id = get_setting("linkedin_client_id")
    client_secret = get_setting("linkedin_client_secret")
    redirect_uri = _external_url("social.linkedin_oauth_callback")

    token_resp = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": redirect_uri, "client_id": client_id, "client_secret": client_secret,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15).json()
    if "access_token" not in token_resp:
        flash(f"LinkedIn connection failed: {token_resp.get('error_description', token_resp.get('error', 'unknown error'))}", "danger")
        return redirect(url_for("dashboard.home"))
    access_token = token_resp["access_token"]
    refresh_token = token_resp.get("refresh_token")  # only present if LinkedIn granted your app refresh-token access

    userinfo = requests.get("https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}, timeout=10).json()
    sub = userinfo.get("sub")
    name = userinfo.get("name", "LinkedIn Profile")
    if not sub:
        flash("LinkedIn connected, but couldn't read your profile — try connecting again.", "warning")
        return redirect(url_for("dashboard.home"))
    person_urn = f"urn:li:person:{sub}"

    channel = SocialChannel.query.filter_by(platform="linkedin", client_project_id=project_id).first()
    if not channel:
        channel = SocialChannel(platform="linkedin", client_project_id=project_id)
        db.session.add(channel)
    channel.label = f"{name} (LinkedIn)"
    channel.credentials = {
        "access_token": access_token,
        "person_urn": person_urn,
        "connected_via": "oauth",
        **({"refresh_token": refresh_token} if refresh_token else {}),
    }
    channel.ensure_secret()
    channel.connected = True
    channel.connection_error = None
    channel.active = True
    db.session.commit()

    flash(f'Connected "{name}" — you can see it in My Bots now. Heads up: LinkedIn access tokens expire '
          f'(usually ~60 days) and there\'s currently no auto-refresh — you\'ll need to reconnect when it does.',
          "success")
    return redirect(url_for("dashboard.home"))


@social_bp.route("/connect/google/start")
@login_required
def google_oauth_start():
    from app.utils.settings import get_setting
    from app.models.platform import ClientProject
    from urllib.parse import quote

    project_id = request.args.get("project_id", type=int)
    project = ClientProject.query.get_or_404(project_id)
    if project.client_id != current_user.id and not current_user.is_admin():
        abort(403)

    client_id = get_setting("google_oauth_client_id")
    if not client_id:
        flash("Google connections aren't set up on this site yet — the site admin needs to add a Google OAuth Client ID in Settings first.", "warning")
        return redirect(url_for("dashboard.home"))

    state = _oauth_serializer().dumps({"project_id": project_id, "user_id": current_user.id})
    redirect_uri = _external_url("social.google_oauth_callback")
    scopes = "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/userinfo.email"
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?response_type=code&client_id={client_id}&redirect_uri={quote(redirect_uri, safe='')}"
        f"&scope={quote(scopes)}&state={state}"
        "&access_type=offline&prompt=consent"  # access_type=offline + prompt=consent is what makes Google actually hand back a refresh_token
    )
    return redirect(auth_url)


@social_bp.route("/connect/google/callback")
@login_required
def google_oauth_callback():
    from itsdangerous import BadSignature, SignatureExpired
    from app.utils.settings import get_setting
    from app.extensions import db
    from app.models.platform import SocialChannel
    import requests

    error = request.args.get("error")
    if error:
        flash(f"Google connection was cancelled: {error}", "warning")
        return redirect(url_for("dashboard.home"))

    code = request.args.get("code")
    state = request.args.get("state", "")
    try:
        data = _oauth_serializer().loads(state, max_age=600)
    except (BadSignature, SignatureExpired):
        abort(400)
    if data.get("user_id") != current_user.id:
        abort(403)
    project_id = data["project_id"]

    client_id = get_setting("google_oauth_client_id")
    client_secret = get_setting("google_oauth_client_secret")
    redirect_uri = _external_url("social.google_oauth_callback")

    token_resp = requests.post("https://oauth2.googleapis.com/token", data={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": redirect_uri, "client_id": client_id, "client_secret": client_secret,
    }, timeout=15).json()
    if "access_token" not in token_resp:
        flash(f"Google connection failed: {token_resp.get('error_description', token_resp.get('error', 'unknown error'))}", "danger")
        return redirect(url_for("dashboard.home"))
    refresh_token = token_resp.get("refresh_token")
    if not refresh_token:
        # Happens if they'd already granted access before and Google skipped
        # re-issuing one — ask them to revoke access in their Google Account
        # and reconnect so we get a fresh refresh_token.
        flash("Google connected, but no long-term access was granted (you may have connected before). "
              "Remove this app's access in your Google Account permissions, then connect again.", "warning")
        return redirect(url_for("dashboard.home"))

    userinfo = requests.get("https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {token_resp['access_token']}"}, timeout=10).json()
    email = userinfo.get("email", "Google Account")

    channel = SocialChannel.query.filter_by(platform="google_sheets", client_project_id=project_id).first()
    if not channel:
        channel = SocialChannel(platform="google_sheets", client_project_id=project_id)
        db.session.add(channel)
    channel.label = f"{email} (Google Sheets)"
    channel.credentials = {"refresh_token": refresh_token, "google_email": email, "connected_via": "oauth"}
    channel.ensure_secret()
    channel.connected = True
    channel.connection_error = None
    channel.active = True
    db.session.commit()

    flash(f'Connected "{email}" — pick it in any "Append Row to Google Sheet" automation step now.', "success")
    return redirect(url_for("dashboard.home"))
