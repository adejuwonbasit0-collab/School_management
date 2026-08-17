"""
Social bot agents — WhatsApp / Telegram / Facebook Messenger.

Each platform's webhook route (see app/social/routes.py) normalizes the
inbound payload down to (external_id, sender_name, text) and calls
handle_inbound_message(). Everything after that point is platform-agnostic:
log it, check human-takeover, match auto-reply rules (keyword reply,
product search, or fallback), send the reply back through the right
platform's send function, and fire the generic automation engine too so
admins can wire emails/webhooks/Slack notifications off channel messages
the exact same way they wire up hire-me leads or newsletter signups.

Runs synchronously in-request, same as the rest of this platform's
background-task-shaped code (no queue/cron configured) — kept fast
(a handful of REST calls) and every external call is wrapped so a bot
failure never 500s the webhook (Telegram/Meta will retry-storm you if
your webhook doesn't return 200).
"""
import logging
import os
import requests
from flask import url_for

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
WHATSAPP_API = "https://graph.facebook.com/v19.0/{phone_number_id}/messages"
FACEBOOK_API = "https://graph.facebook.com/v19.0/me/messages"
INSTAGRAM_API = "https://graph.facebook.com/v19.0/me/messages"  # IG DMs route through the same Send API as the linked Page


def _proxies():
    """PythonAnywhere (and some other hosts) require outbound HTTPS requests
    to go through an internal proxy on certain plans. That proxy is usually
    only exported as an env var (https_proxy/http_proxy) inside an
    interactive bash console via .bashrc — the actual web app's WSGI
    process does NOT source .bashrc, so it silently has no proxy configured
    even though a console test works fine. Reading it from a DB setting
    instead makes it work regardless of how the WSGI process was started.
    Configure this in Admin -> Settings -> Outbound Proxy if your host
    needs one; leave blank if it doesn't (most hosts don't)."""
    try:
        from app.utils.settings import get_setting
        proxy_url = get_setting("outbound_proxy_url")
    except Exception:
        proxy_url = None
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}


def _request(method, url, **kwargs):
    kwargs.setdefault("timeout", 10)
    proxies = _proxies()
    if proxies:
        kwargs["proxies"] = proxies
    return requests.request(method, url, **kwargs)


# ─────────────────────────── outbound senders ───────────────────────────

def send_telegram_message(channel, chat_id, text):
    token = (channel.credentials or {}).get("bot_token")
    if not token:
        raise ValueError("Telegram channel has no bot_token configured")
    url = TELEGRAM_API.format(token=token, method="sendMessage")
    resp = _request("POST", url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    if resp.status_code >= 400:
        raise RuntimeError(f"Telegram sendMessage failed: {resp.status_code} {resp.text[:300]}")
    return resp.json()


def send_telegram_audio(channel, chat_id, filepath, caption=None):
    """Real multipart upload to Telegram's sendAudio — used by the
    voice_reply automation action. Uploads the local MP3 file directly
    (no need to expose it at a public URL first) so this works the same
    on a dev box or behind a firewall as it does in production.
    sendAudio (not sendVoice) is used deliberately: Telegram's sendVoice
    endpoint requires OGG/OPUS-encoded audio for the round "voice memo"
    bubble UI, but edge-tts/gTTS/ElevenLabs all produce MP3 here — sendAudio
    accepts MP3 as-is and still delivers as a real playable voice message,
    just with the standard audio-player bubble instead of the round one.
    """
    token = (channel.credentials or {}).get("bot_token")
    if not token:
        raise ValueError("Telegram channel has no bot_token configured")
    if not os.path.exists(filepath):
        raise ValueError(f"Voice audio file not found: {filepath}")
    url = TELEGRAM_API.format(token=token, method="sendAudio")
    with open(filepath, "rb") as f:
        files = {"audio": (os.path.basename(filepath), f, "audio/mpeg")}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        resp = requests.post(url, data=data, files=files, timeout=20)
    if resp.status_code >= 400:
        raise RuntimeError(f"Telegram sendAudio failed: {resp.status_code} {resp.text[:300]}")
    return resp.json()


def send_whatsapp_message(channel, to, text):
    creds = channel.credentials or {}
    phone_number_id = creds.get("phone_number_id")
    access_token = creds.get("access_token")
    if not phone_number_id or not access_token:
        raise ValueError("WhatsApp channel missing phone_number_id/access_token")
    url = WHATSAPP_API.format(phone_number_id=phone_number_id)
    resp = _request("POST", url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
        timeout=10)
    if resp.status_code >= 400:
        raise RuntimeError(f"WhatsApp send failed: {resp.status_code} {resp.text[:300]}")
    return resp.json()


def send_facebook_message(channel, psid, text):
    access_token = (channel.credentials or {}).get("page_access_token")
    if not access_token:
        raise ValueError("Facebook channel has no page_access_token configured")
    resp = _request("POST", FACEBOOK_API,
        params={"access_token": access_token},
        json={"recipient": {"id": psid}, "message": {"text": text}},
        timeout=10)
    if resp.status_code >= 400:
        raise RuntimeError(f"Facebook send failed: {resp.status_code} {resp.text[:300]}")
    return resp.json()


def send_instagram_message(channel, igsid, text):
    access_token = (channel.credentials or {}).get("page_access_token")
    if not access_token:
        raise ValueError("Instagram channel has no page_access_token configured")
    resp = _request("POST", INSTAGRAM_API,
        params={"access_token": access_token},
        json={"recipient": {"id": igsid}, "message": {"text": text}},
        timeout=10)
    if resp.status_code >= 400:
        raise RuntimeError(f"Instagram send failed: {resp.status_code} {resp.text[:300]}")
    return resp.json()


def send_reply(channel, external_id, text):
    if channel.platform == "telegram":
        return send_telegram_message(channel, external_id, text)
    if channel.platform == "whatsapp":
        return send_whatsapp_message(channel, external_id, text)
    if channel.platform == "facebook":
        return send_facebook_message(channel, external_id, text)
    if channel.platform == "instagram":
        return send_instagram_message(channel, external_id, text)
    if channel.platform == "linkedin":
        # Fallback to posting to feed if rules match, or log it
        return post_to_linkedin(channel, text)
    raise ValueError(f"Unknown platform: {channel.platform}")


def post_to_facebook_page(channel, message, link=None):
    """Publishes to the connected Page's public feed — a real post, not a
    reply to any one person. Uses the SAME Page Access Token already
    stored for messaging, since a token with pages_manage_posts scope
    can do both; no separate OAuth flow needed. Requires the token to
    have been granted that permission when it was created in Meta's
    Graph API Explorer / your Meta App — if it wasn't, this fails with a
    clear permissions error from Facebook itself."""
    if channel.platform != "facebook":
        raise ValueError("post_to_facebook_page only works for Facebook Page channels")
    page_id = (channel.credentials or {}).get("page_id")
    token = (channel.credentials or {}).get("page_access_token")
    if not page_id or not token:
        raise RuntimeError("This channel is missing its page_id — reconnect it under Social Channels so it's captured.")
    payload = {"message": message, "access_token": token}
    if link:
        payload["link"] = link
    resp = _request("POST", f"https://graph.facebook.com/v19.0/{page_id}/feed", data=payload, timeout=15)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "Facebook post failed"))
    return data  # {"id": "<page_id>_<post_id>"}


def _resolve_instagram_business_id(channel):
    """The Page Access Token used for Instagram DMs is also what's needed
    for feed publishing, but publishing needs the IG *Business Account ID*
    (different from the numeric IGSID used for messaging), which isn't
    captured at connect-time. Resolve it once via Graph API and cache it
    on the channel so we don't call this every post."""
    creds = channel.credentials or {}
    ig_user_id = creds.get("ig_user_id")
    if ig_user_id:
        return ig_user_id
    token = creds.get("page_access_token")
    if not token:
        raise RuntimeError("Instagram channel has no page_access_token configured")
    resp = _request("GET", "https://graph.facebook.com/v19.0/me",
        params={"fields": "instagram_business_account", "access_token": token}, timeout=10)
    data = resp.json()
    ig_account = (data.get("instagram_business_account") or {}).get("id")
    if not ig_account:
        raise RuntimeError(
            "Could not find an Instagram Business Account linked to this Page token. "
            "Make sure the Instagram account is a Business/Creator account connected "
            "to a Facebook Page, and the token has instagram_content_publish permission."
        )
    from app.extensions import db
    channel.credentials["ig_user_id"] = ig_account
    db.session.commit()
    return ig_account


def post_to_instagram_feed(channel, caption, image_url):
    """Publishes a real photo post to the connected Instagram feed.

    Unlike Facebook/LinkedIn, Instagram's API has no text-only post — every
    feed post needs an image or video, so this requires a public image_url
    (Content Studio only writes captions; the image itself has to come from
    somewhere hosted, e.g. a URL you paste in). Uses Meta's two-step
    container flow: create a media container, then publish it.
    """
    if channel.platform != "instagram":
        raise ValueError("post_to_instagram_feed only works for Instagram channels")
    if not image_url:
        raise RuntimeError("Instagram feed posts require an image URL — Instagram has no text-only post type.")
    token = (channel.credentials or {}).get("page_access_token")
    if not token:
        raise RuntimeError("Missing page access token for this Instagram channel")
    ig_user_id = _resolve_instagram_business_id(channel)

    create_resp = _request("POST", f"https://graph.facebook.com/v19.0/{ig_user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token}, timeout=20)
    create_data = create_resp.json()
    if "error" in create_data:
        raise RuntimeError(create_data["error"].get("message", "Instagram media container failed"))
    creation_id = create_data.get("id")
    if not creation_id:
        raise RuntimeError("Instagram did not return a media container id")

    publish_resp = _request("POST", f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token}, timeout=20)
    publish_data = publish_resp.json()
    if "error" in publish_data:
        raise RuntimeError(publish_data["error"].get("message", "Instagram publish step failed"))
    return publish_data  # {"id": "<ig_media_id>"}


def post_to_linkedin(channel, message):
    """Publishes a post directly to the connected LinkedIn member's feed."""
    if channel.platform != "linkedin":
        raise ValueError("post_to_linkedin only works for LinkedIn channels")
    creds = channel.credentials or {}
    token = creds.get("access_token")
    if not token:
        raise RuntimeError("Missing access token for LinkedIn")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }

    person_urn = creds.get("person_urn")
    if not person_urn:
        resp = _request("GET", "https://api.linkedin.com/v2/me", headers=headers, timeout=10)
        data = resp.json()
        if "id" in data:
            person_id = data["id"]
            person_urn = f"urn:li:person:{person_id}"
            from app.extensions import db
            channel.credentials["person_urn"] = person_urn
            db.session.commit()
        else:
            resp2 = _request("GET", "https://api.linkedin.com/v2/userinfo", headers=headers, timeout=10)
            data2 = resp2.json()
            if "sub" in data2:
                person_id = data2["sub"]
                person_urn = f"urn:li:person:{person_id}"
                from app.extensions import db
                channel.credentials["person_urn"] = person_urn
                db.session.commit()
            else:
                err_msg = data.get("message", data2.get("message", "Could not retrieve LinkedIn profile URN"))
                raise RuntimeError(err_msg)

    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": message
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    resp = _request("POST", "https://api.linkedin.com/v2/ugcPosts", headers=headers, json=payload, timeout=15)
    data = resp.json()
    if resp.status_code >= 400 or "error" in data:
        err = data.get("message", "Unknown error")
        raise RuntimeError(f"LinkedIn API error: {err}")
    return data


# ─────────────────────────── connection tests ───────────────────────────

def test_telegram_connection(bot_token):
    resp = _request("GET", TELEGRAM_API.format(token=bot_token, method="getMe"), timeout=10)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "Invalid bot token"))
    return data["result"]  # {"id":..., "username": "...", "first_name": "..."}


def register_telegram_webhook(bot_token, webhook_url):
    resp = _request("POST", TELEGRAM_API.format(token=bot_token, method="setWebhook"),
                          json={"url": webhook_url}, timeout=10)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "setWebhook failed"))
    return data


def test_whatsapp_connection(phone_number_id, access_token):
    resp = _request("GET", f"https://graph.facebook.com/v19.0/{phone_number_id}",
                         params={"access_token": access_token, "fields": "verified_name,display_phone_number"},
                         timeout=10)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "Invalid WhatsApp credentials"))
    return data


def test_facebook_connection(page_access_token):
    resp = _request("GET", "https://graph.facebook.com/v19.0/me",
                         params={"access_token": page_access_token, "fields": "name,id"}, timeout=10)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "Invalid Page access token"))
    return data


def test_instagram_connection(page_access_token):
    # Instagram Direct messaging is configured through the same linked
    # Facebook Page as Messenger — verify the token the same way and
    # additionally confirm an Instagram Business Account is actually
    # attached, since that's the part specific to Instagram.
    resp = _request("GET", "https://graph.facebook.com/v19.0/me",
                         params={"access_token": page_access_token, "fields": "name,instagram_business_account"},
                         timeout=10)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "Invalid Page access token"))
    if not data.get("instagram_business_account"):
        raise RuntimeError("This Page has no Instagram professional account linked. Link one in Meta Business Suite first.")
    return data


def test_linkedin_connection(access_token):
    """Validates the LinkedIn Access Token by requesting member profile."""
    # Try the standard v2/me endpoint
    resp = _request("GET", "https://api.linkedin.com/v2/me",
                    headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
    data = resp.json()
    if "serviceErrorCode" in data or resp.status_code >= 400:
        # Fallback to the newer OIDC userinfo endpoint
        resp2 = _request("GET", "https://api.linkedin.com/v2/userinfo",
                         headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        data2 = resp2.json()
        if resp2.status_code >= 400 or "error" in data2:
            err_msg = data.get("message", data2.get("message", "Invalid LinkedIn access token"))
            raise RuntimeError(err_msg)
        return {"id": data2.get("sub"), "name": data2.get("name", "LinkedIn Member")}
    
    first = data.get("localizedFirstName", "")
    last = data.get("localizedLastName", "")
    name = f"{first} {last}".strip() or "LinkedIn Member"
    return {"id": data.get("id"), "name": name}


# ─────────────────────────── inbound handling ───────────────────────────

def _get_or_create_contact(channel, external_id, display_name=None):
    from app.extensions import db
    from app.models.platform import ChatContact
    from datetime import datetime
    contact = ChatContact.query.filter_by(channel_id=channel.id, external_id=external_id).first()
    if not contact:
        contact = ChatContact(channel_id=channel.id, external_id=external_id, display_name=display_name)
        db.session.add(contact)
    elif display_name and not contact.display_name:
        contact.display_name = display_name
    contact.last_message_at = datetime.utcnow()
    db.session.commit()
    return contact


def _log_message(contact, direction, body, sent_by="bot"):
    from app.extensions import db
    from app.models.platform import ChatMessage
    db.session.add(ChatMessage(contact_id=contact.id, direction=direction, body=body, sent_by=sent_by))
    db.session.commit()


def _match_rule(text, rules):
    import re
    low = (text or "").lower().strip()
    original_text = text or ""
    for rule in (rules or []):
        keywords = [k.strip() for k in rule.get("keywords", []) if k.strip()]
        if not keywords:
            continue
        match_type = rule.get("match", "contains")
        
        if match_type == "regex":
            for kw in keywords:
                try:
                    if re.search(kw, original_text, re.IGNORECASE):
                        return rule
                except Exception:
                    pass
        elif match_type == "starts_with":
            if any(low.startswith(kw.lower()) for kw in keywords):
                return rule
        elif match_type == "exact":
            if any(low == kw.lower() for kw in keywords):
                return rule
        elif match_type in ("contains", "contains_any"):
            if any(kw.lower() in low for kw in keywords):
                return rule
    return None


def _product_card_text(products):
    if not products:
        return "I couldn't find a product matching that — could you tell me the name, or ask to see everything we offer?"
    lines = []
    for p in products[:5]:
        line = f"🛍️ <b>{p['title']}</b>\n{p['price']} — {(p['description'] or '')[:100]}"
        if p.get("link"):
            line += f"\n🔗 {p['link']}"
        if p.get("image"):
            # Not a native image attachment (that needs a per-platform media
            # send call this doesn't add) — just the URL, which Telegram/
            # WhatsApp/etc. mostly render as a link preview anyway.
            line += f"\n🖼️ {p['image']}"
        lines.append(line)
    return "\n\n".join(lines)


def _search_products(term, channel=None):
    """Searches a channel's own custom_catalog first (the product/service
    list a CUSTOMER's bot needs, since it isn't your marketplace) and
    falls back to your own marketplace Product table only when this
    channel has no custom catalog set — i.e. when it's your own bot."""
    catalog = (channel.custom_catalog if channel else None) or []
    if catalog:
        term_low = (term or "").lower()
        matches = [c for c in catalog if not term_low or term_low in (c.get("name") or "").lower()]
        results = matches or catalog
        return [{"title": c.get("name", ""), "price": c.get("price", ""), "description": c.get("description", ""),
                 "link": c.get("link", ""), "image": c.get("image", "")}
                for c in results[:5]]

    from app.models.commerce import Product
    q = Product.query.filter_by(status="active")
    if term:
        like = f"%{term}%"
        q = q.filter(Product.title.ilike(like))
    products = q.order_by(Product.featured.desc()).limit(5).all()
    return [{"title": p.title, "price": f"${p.sale_price}" if p.sale_price else f"${p.price}",
             "description": p.description, "link": url_for("marketplace.product_detail", slug=p.slug, _external=True) if p.slug else "",
             "image": (p.images[0] if p.images else "")} for p in products]


def handle_inbound_message(channel, external_id, text, sender_name=None):
    """The one function every platform's webhook route calls. Never raises —
    the webhook route always needs to return 200 to the platform regardless
    of what happens here, or Telegram/Meta will keep retrying the same
    message and hammer the endpoint."""
    try:
        from app.extensions import db
        from app.models.platform import SocialChannel
        from app.utils.automation import trigger as automation_trigger

        from app.models.platform import ChatContact
        try:
            is_new_contact = not db.session.query(
                ChatContact.query.filter_by(channel_id=channel.id, external_id=external_id).exists()
            ).scalar()
        except Exception:
            logger.exception("new-contact check failed for channel %s — skipping welcome message this time", channel.id)
            is_new_contact = False
        contact = _get_or_create_contact(channel, external_id, sender_name)
        _log_message(contact, "in", text, sent_by="customer")
        channel.message_count = (channel.message_count or 0) + 1
        db.session.commit()

        # First-ever message from this contact: send the configured welcome
        # (e.g. "Hi! What can I help you with today? You can ask about
        # products, pricing, or say 'agent' to reach a human.") instead of
        # running keyword rules against it — greet first, let them state
        # what they want on their next message.
        if is_new_contact and (channel.welcome_message or "").strip():
            reply = channel.welcome_message.strip()
            send_reply(channel, external_id, reply)
            _log_message(contact, "out", reply, sent_by="bot")
            return

        # Fire the generic automation engine too — this is what lets an
        # admin bolt on "email me", "post to Slack via webhook", etc. on
        # top of channel messages the exact same way every other trigger
        # in this platform works, without a bespoke integration per need.
        automation_trigger("channel_message_received", {
            "platform": channel.platform, "channel_label": channel.label,
            "contact": sender_name or external_id, "message": text,
        })

        low = (text or "").lower()
        takeover_kw = [k.lower() for k in (channel.human_takeover_keywords or [])]
        if takeover_kw and any(kw in low for kw in takeover_kw) and not contact.human_takeover:
            contact.human_takeover = True
            db.session.commit()
            reply = "Got it — connecting you with a real person now. They'll be with you shortly!"
            send_reply(channel, external_id, reply)
            _log_message(contact, "out", reply, sent_by="bot")
            return

        if contact.human_takeover:
            # Bot stays silent — a human is handling this conversation from
            # the admin inbox now. Still logged above so nothing is lost.
            return

        rule = _match_rule(text, channel.auto_reply_rules)
        if rule and rule.get("show_products"):
            products = _search_products(rule.get("product_search") or text, channel)
            reply = _product_card_text(products)
        elif rule:
            reply = rule.get("reply") or channel.fallback_reply
        elif channel.ai_agent_enabled and (channel.ai_agent_instructions or "").strip():
            reply = _ai_agent_reply(channel, contact, text)
        else:
            reply = channel.fallback_reply or "Thanks for your message! A team member will get back to you shortly."

        send_reply(channel, external_id, reply)
        _log_message(contact, "out", reply, sent_by="bot")

    except Exception:
        logger.exception("handle_inbound_message failed for channel %s", getattr(channel, "id", None))


def _ai_agent_reply(channel, contact, latest_text):
    """Generates a live reply from the channel's configured persona/
    instructions plus recent conversation history and its own product
    catalog. Falls back to the static default reply if the AI call fails
    for any reason — a bot must always say SOMETHING back."""
    try:
        from app.models.platform import ChatMessage
        history = ChatMessage.query.filter_by(contact_id=contact.id).order_by(ChatMessage.created_at.desc()).limit(10).all()
        history.reverse()
        convo = "\n".join(f"{'Customer' if m.direction == 'in' else 'Assistant'}: {m.body}" for m in history)
        text, err = _generate_agent_reply_text(channel, convo)
        if err or not text:
            raise RuntimeError(err or "empty response")
        return text.strip()
    except Exception:
        logger.exception("AI agent reply failed for channel %s — using fallback", channel.id)
        return channel.fallback_reply or "Thanks for your message! A team member will get back to you shortly."


def _generate_agent_reply_text(channel, convo_text):
    """The actual generation step, shared by the live webhook path above
    (which swallows errors — a customer must always get SOME reply) and
    test_ai_agent_reply below (which does NOT swallow errors — an admin
    testing this from the dashboard needs to see exactly why it failed,
    not a generic fallback that looks identical whether AI Agent Mode is
    working perfectly or completely broken)."""
    from app.ai_tools.routes import _call_ai
    catalog_note = ""
    if channel.custom_catalog:
        items = ", ".join(c.get("name", "") for c in channel.custom_catalog[:10])
        catalog_note = f"\n\nProducts/services offered: {items}"
    system = ((channel.ai_agent_instructions or "").strip() + catalog_note +
              "\n\nReply to the customer's latest message. Keep it short and natural for a chat conversation. "
              "Return only the reply text, nothing else.")
    return _call_ai(system, [{"role": "user", "content": convo_text}],
                     max_tokens=300, temperature=channel.ai_agent_temperature or 0.7)


def test_ai_agent_reply(channel, test_message):
    """Used ONLY by the admin's 'Test AI Reply' button
    (app/admin/routes.py test_channel_ai_reply) — runs the exact same
    generation as a real customer message would, but returns the real
    error instead of a silent generic fallback, so 'is this actually
    configured and working' has a real answer instead of a guess."""
    if not channel.ai_agent_enabled:
        return None, "AI Agent Mode isn't enabled for this channel — toggle it on in Admin -> Social Channels -> this channel."
    if not (channel.ai_agent_instructions or "").strip():
        return None, ("No AI Agent instructions have been set for this channel yet — this is a required field, "
                       "not an AI-provider problem. Go to Admin -> Social Channels -> this channel and fill in "
                       "'AI Agent Instructions' (the persona/system prompt it replies with), then test again.")
    text, err = _generate_agent_reply_text(channel, f"Customer: {test_message}")
    if err:
        return None, err
    if not text:
        return None, "The AI returned an empty reply."
    return text.strip(), None
