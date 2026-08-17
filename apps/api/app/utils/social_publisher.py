"""
Multi-Platform Direct Social Media Publishing Engine, Persona Presets & Share Tools.

Supports direct publishing to:
- Twitter/X (via Twitter API v2)
- Facebook Page (via Meta Graph API)
- Instagram Feed (via Meta Graph API Media Container)
- LinkedIn Feed (via LinkedIn UGC API)
- Telegram Channels
"""
import urllib.parse
import logging
import requests

logger = logging.getLogger(__name__)

# Pre-defined AI Sales Agent Personas
PERSONA_PRESETS = {
    "sales_rep": {
        "name": "💼 High-Converting Sales Representative",
        "instructions": (
            "You are an energetic, high-converting Sales Representative. "
            "Your primary goal is to qualify leads, highlight product benefits, answer pricing questions compellingly, "
            "and guide the customer toward booking a call or making a purchase. Keep your tone professional yet enthusiastic."
        ),
        "temperature": 0.7
    },
    "tech_advisor": {
        "name": "🛠️ Technical Advisor & Solutions Architect",
        "instructions": (
            "You are a knowledgeable Technical Advisor & Solutions Architect. "
            "Your goal is to answer deep technical questions, explain software specifications, system architecture options, "
            "and integration requirements clearly and precisely. Provide helpful technical detail while emphasizing scalability."
        ),
        "temperature": 0.5
    },
    "customer_support": {
        "name": "🎧 Patient Customer Support Specialist",
        "instructions": (
            "You are a patient and helpful Customer Support Specialist. "
            "Your focus is troubleshooting customer issues, providing clear step-by-step guidance, answering FAQs, "
            "and ensuring high satisfaction. Maintain an empathetic, calm, and reassuring tone at all times."
        ),
        "temperature": 0.4
    },
    "lead_converter": {
        "name": "🎯 Strategic Lead Converter",
        "instructions": (
            "You are a strategic Lead Conversion Specialist. "
            "Your goal is to identify prospect pain points, ask qualifying questions, highlight relevant solutions from our catalog, "
            "and capture contact information or schedule a demo."
        ),
        "temperature": 0.8
    }
}


def generate_share_links(url: str, title: str = "") -> dict:
    """Generates direct 1-click social share links for a given page URL and title."""
    encoded_url = urllib.parse.quote(url)
    encoded_title = urllib.parse.quote(title)
    
    return {
        "twitter": f"https://twitter.com/intent/tweet?url={encoded_url}&text={encoded_title}",
        "facebook": f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
        "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}",
        "whatsapp": f"https://api.whatsapp.com/send?text={encoded_title}%20{encoded_url}",
        "telegram": f"https://t.me/share/url?url={encoded_url}&text={encoded_title}",
        "pinterest": f"https://pinterest.com/pin/create/button/?url={encoded_url}&description={encoded_title}"
    }


def post_to_twitter(channel, message: str, media_url: str = None) -> dict:
    """Posts a Tweet via Twitter API v2."""
    if channel.platform != "twitter":
        raise ValueError("post_to_twitter only works for Twitter/X channels")
    creds = channel.credentials or {}
    bearer_token = creds.get("bearer_token") or creds.get("access_token")
    if not bearer_token:
        raise RuntimeError("Twitter channel is missing bearer_token or access_token in credentials.")
        
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    payload = {"text": message}
    
    resp = requests.post("https://api.twitter.com/2/tweets", headers=headers, json=payload, timeout=15)
    data = resp.json()
    if resp.status_code >= 400 or "errors" in data:
        err_msg = data.get("detail") or str(data.get("errors", "Twitter API call failed"))
        raise RuntimeError(f"Twitter API error: {err_msg}")
    return data


def publish_to_channels(channels: list, message: str, image_url: str = None, link: str = None) -> dict:
    """Broadcasting utility — publishes text/image to all connected active social channels."""
    from app.utils.social_bots import post_to_facebook_page, post_to_instagram_feed, post_to_linkedin
    
    results = {}
    for ch in channels:
        if not ch.active:
            continue
        try:
            if ch.platform == "facebook":
                res = post_to_facebook_page(ch, message, link=link)
                results[f"{ch.label} (Facebook)"] = {"success": True, "data": res}
            elif ch.platform == "instagram":
                if not image_url:
                    results[f"{ch.label} (Instagram)"] = {"success": False, "error": "Instagram requires an image URL."}
                else:
                    res = post_to_instagram_feed(ch, message, image_url)
                    results[f"{ch.label} (Instagram)"] = {"success": True, "data": res}
            elif ch.platform == "linkedin":
                res = post_to_linkedin(ch, message)
                results[f"{ch.label} (LinkedIn)"] = {"success": True, "data": res}
            elif ch.platform == "twitter":
                res = post_to_twitter(ch, message, media_url=image_url)
                results[f"{ch.label} (Twitter)"] = {"success": True, "data": res}
            else:
                results[f"{ch.label} ({ch.platform})"] = {"success": False, "error": "Platform does not support direct broadcasting."}
        except Exception as e:
            logger.exception("Failed auto-publishing to %s", ch.label)
            results[f"{ch.label} ({ch.platform})"] = {"success": False, "error": str(e)}
            
    return results
