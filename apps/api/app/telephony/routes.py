"""Inbound Twilio webhooks — WhatsApp messages and Voice calls. Both are
public-by-necessity (Twilio calls them directly, no session/CSRF token
possible) and are protected instead by verifying Twilio's HMAC signature
on every request (see verify_twilio_signature) and by picking a specific
Agent Studio persona to answer with (never full tool access — these run
tool-free, like the public chat widgets, since a random caller/WhatsApp
sender should never be able to trigger real site actions by talking to
a phone number).
"""
from flask import Blueprint, request, Response, current_app
from app.utils.settings import get_setting
from app.utils.twilio_integration import verify_twilio_signature, twiml_message, twiml_gather_say

telephony_bp = Blueprint("telephony", __name__)

_CALL_HISTORY = {}  # call_sid -> [{"role":..., "content":...}, ...] — in-process only, see note below.
_CALL_HISTORY_CAP = 20


def _run_configured_agent(system_extra, user_message, history):
    """Runs the Twilio-designated agent (Admin -> Settings -> Twilio ->
    'Agent for calls/WhatsApp') tool-free, same safety posture as the
    embeddable widget — a phone caller or WhatsApp sender is an anonymous
    stranger and should never get real site actions, only conversation."""
    from app.models.core import Agent
    from app.ai_tools.routes import _call_ai

    agent_id = get_setting("twilio_agent_id")
    agent = Agent.query.get(int(agent_id)) if agent_id else None
    base_instructions = agent.instructions if agent else "You are a helpful assistant for this business."
    name = agent.name if agent else "Assistant"

    system = (
        f"You are {name}. {base_instructions}\n\n{system_extra}\n\n"
        "You do NOT have tools or the ability to take real actions — conversation only. "
        "If asked to do something you can't do over this channel, say so and suggest contacting the business directly."
    )
    messages = list(history) + [{"role": "user", "content": user_message}]
    text, err = _call_ai(system, messages, max_tokens=400)
    if err:
        return "Sorry, I'm having trouble right now — please try again shortly."
    return text or "Sorry, could you say that again?"


@telephony_bp.route("/webhooks/twilio/whatsapp", methods=["POST"])
def twilio_whatsapp_webhook():
    form = request.form.to_dict()
    signature = request.headers.get("X-Twilio-Signature", "")
    if not verify_twilio_signature(request.url, form, signature):
        current_app.logger.warning("Rejected Twilio WhatsApp webhook: bad signature.")
        return Response(status=403)

    body = (form.get("Body") or "").strip()
    from_number = form.get("From", "")
    if not body:
        return Response(twiml_message("Sorry, I can only handle text messages right now."), mimetype="text/xml")

    reply = _run_configured_agent(
        "You're replying to a WhatsApp message. Keep it concise — this is a chat conversation, not an email.",
        body, [],
    )
    return Response(twiml_message(reply), mimetype="text/xml")


@telephony_bp.route("/webhooks/twilio/voice", methods=["POST"])
def twilio_voice_webhook():
    form = request.form.to_dict()
    signature = request.headers.get("X-Twilio-Signature", "")
    if not verify_twilio_signature(request.url, form, signature):
        current_app.logger.warning("Rejected Twilio Voice webhook: bad signature.")
        return Response(status=403)

    call_sid = form.get("CallSid", "")
    speech_result = (form.get("SpeechResult") or "").strip()
    action_url = request.url  # Twilio POSTs back to the same URL on each <Gather> turn.

    history = _CALL_HISTORY.get(call_sid, [])

    if not speech_result:
        # First hit for this call — no speech yet, just greet and listen.
        greeting_agent_id = get_setting("twilio_agent_id")
        from app.models.core import Agent
        agent = Agent.query.get(int(greeting_agent_id)) if greeting_agent_id else None
        greeting = agent.public_greeting if (agent and agent.public_greeting) else "Hi, thanks for calling! How can I help you today?"
        return Response(twiml_gather_say(greeting, action_url), mimetype="text/xml")

    reply = _run_configured_agent(
        "You're on a live phone call — keep replies SHORT (1-2 sentences), since this is spoken aloud, not read.",
        speech_result, history,
    )
    history.append({"role": "user", "content": speech_result})
    history.append({"role": "assistant", "content": reply})
    _CALL_HISTORY[call_sid] = history[-_CALL_HISTORY_CAP:]

    hang_up = any(w in reply.lower() for w in ["goodbye", "have a great day", "bye now", "take care"])
    if hang_up:
        _CALL_HISTORY.pop(call_sid, None)
    return Response(twiml_gather_say(reply, action_url, hang_up=hang_up), mimetype="text/xml")


# ── Per-customer WhatsApp Bot connection ────────────────────────────────
# Distinct from the /webhooks/twilio/whatsapp route above, which answers
# with the single site-wide Admin -> Settings -> Twilio agent. This one
# is per-bot: each customer pastes their OWN Twilio Account SID/Auth
# Token/WhatsApp-approved number into their WhatsApp Bot builder (see
# dashboard.chatbot_builder_connect_whatsapp), gets back a webhook URL
# unique to their bot, and pastes THAT into their own Twilio console —
# so their bot replies from their own WhatsApp number using their own
# configured flows/keywords/AI, not the platform owner's.
@telephony_bp.route("/webhooks/twilio/whatsapp/<int:bot_id>", methods=["POST"])
def twilio_whatsapp_webhook_per_bot(bot_id):
    from app.models.platform import UserChatbot
    # BUG FIX: this used to filter_by(platform="whatsapp", ...), but no
    # code path ever sets that value — chatbot_builder.html creates every
    # new bot with platform='Web Widget' (see its newBot()/create logic)
    # and WhatsApp connection is a separate, independent toggle
    # (whatsapp_credentials_encrypted / the whatsapp_connected property),
    # not a platform value. Since whatsapp_connected is a Python @property
    # (derived from an encrypted column), it can't be used in filter_by()
    # either — that's presumably why "whatsapp" got typed in as a
    # stand-in filter instead. The real, consistently reproducible result
    # (verified: created a bot exactly the way the UI does, connected
    # WhatsApp, then ran this exact query — it matched nothing) was that
    # every single Twilio webhook call 404'd, silently, for every bot,
    # regardless of how correctly a customer set up their connection.
    # Filtering on active=True and checking whatsapp_connected in Python
    # after the fetch (which the code was already about to do on the next
    # line anyway) is the correct fix.
    bot = UserChatbot.query.filter_by(id=bot_id, active=True).first()
    if not bot or not bot.whatsapp_connected:
        return Response(status=404)

    creds = bot.get_whatsapp_credentials()
    form = request.form.to_dict()
    signature = request.headers.get("X-Twilio-Signature", "")
    if not verify_twilio_signature(request.url, form, signature, auth_token=creds.get("auth_token")):
        current_app.logger.warning(f"Rejected Twilio WhatsApp webhook for bot_id={bot_id}: bad signature.")
        return Response(status=403)

    body = (form.get("Body") or "").strip()
    if not body:
        return Response(twiml_message("Sorry, I can only handle text messages right now."), mimetype="text/xml")

    from app.extensions import db
    bot.message_count = (bot.message_count or 0) + 1
    db.session.commit()

    # 1. Keyword rules first (same priority order as the public web widget's
    #    chatbot_reply endpoint), then AI if enabled, then a fallback reply
    #    — reusing that exact logic here (not duplicating it) so a bot
    #    behaves identically whether a customer messages it on WhatsApp or
    #    on the embedded web widget.
    reply = None
    for kw in (bot.keywords or []):
        pattern = (kw.get("pattern") or "").strip().lower()
        if not pattern:
            continue
        type_ = kw.get("type", "contains")
        if type_ == "exact" and body.lower() == pattern:
            reply = kw.get("reply", "")
            break
        if type_ == "contains" and pattern in body.lower():
            reply = kw.get("reply", "")
            break
    if reply is None and bot.ai_enabled:
        from app.utils.knowledge import generate_bot_reply
        ai_reply, err = generate_bot_reply(
            bot.ai_instructions, bot.faqs, bot.knowledge_text, body,
            unknown_reply=bot.unknown_reply, sources=bot.knowledge_sources,
            charge_user_id=bot.user_id,
        )
        if not err and ai_reply:
            reply = ai_reply
    if reply is None:
        reply = "Thank you for your message. We have received it and will get back to you shortly!"

    return Response(twiml_message(reply), mimetype="text/xml")
