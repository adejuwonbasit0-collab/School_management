import re
from datetime import datetime
from markupsafe import Markup
import markdown as md

def register_filters(app):
    @app.template_filter("display_currency_as")
    def display_currency_as_filter(amount, from_currency, to_currency):
        """{{ price | display_currency_as(product.currency, 'NGN') }} — like
        display_currency but for an explicit target currency, used for
        showing a price in several currencies at once regardless of the
        site's configured display currency."""
        from app.utils.currency import display_price
        return display_price(amount, from_currency, to_currency)

    @app.template_filter("display_currency")
    def display_currency_filter(amount, from_currency=None):
        """{{ product.price | display_currency(product.currency) }} —
        converts to the site's configured currency (flask.g.currency, set
        from the site_currency admin setting). If a stored value's own
        currency isn't passed in, it's assumed to already be in the site's
        currency — NOT hardcoded to USD, which was the bug that kept
        showing dollar signs after switching the site to Naira."""
        from flask import g
        from app.utils.currency import display_price
        to_currency = getattr(g, "currency", "NGN")
        source_currency = from_currency or to_currency
        # This filter previously fell straight through to video_embed_filter's
        # definition with no return statement — every {{ x | display_currency }}
        # in every template silently rendered as blank/None. That's fixed here;
        # nothing above this line changed.
        return display_price(amount, source_currency, to_currency)
    @app.template_filter("video_embed")
    def video_embed_filter(url):
        if not url:
            return {"type": "none"}
        url_str = str(url).strip()
        yt_match = re.search(r"(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})", url_str)
        if yt_match:
            video_id = yt_match.group(1)
            return {
                "type": "youtube",
                "embed_url": f"https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1&loop=1&playlist={video_id}&controls=0&showinfo=0&autohide=1&playsinline=1"
            }
        vimeo_match = re.search(r"vimeo\.com/(?:video/)?([0-9]+)", url_str)
        if vimeo_match:
            video_id = vimeo_match.group(1)
            return {
                "type": "vimeo",
                "embed_url": f"https://player.vimeo.com/video/{video_id}?autoplay=1&loop=1&muted=1&background=1"
            }
        return {"type": "direct", "url": url_str}

    @app.template_filter("markdown")
    def markdown_filter(text):
        if not text:
            return ""
        return Markup(md.markdown(text, extensions=["fenced_code", "tables"]))

    @app.template_filter("timeago")
    def timeago_filter(dt):
        if not dt:
            return ""
        diff = datetime.utcnow() - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:    return "just now"
        if seconds < 3600:  return f"{seconds // 60}m ago"
        if seconds < 86400: return f"{seconds // 3600}h ago"
        if seconds < 604800: return f"{seconds // 86400}d ago"
        return dt.strftime("%b %d, %Y")

    @app.template_filter("money")
    def money_filter(value, currency=None):
        """Defaults to the site's configured currency (site_currency
        setting) — no more hardcoded '$' regardless of what the admin
        actually set the site to."""
        from flask import g
        from app.utils.currency import format_amount
        try:
            code = currency or getattr(g, "currency", "NGN")
            return format_amount(float(value), code)
        except (TypeError, ValueError):
            return str(value)

    @app.template_filter("truncate_words")
    def truncate_words_filter(text, length=30):
        if not text:
            return ""
        words = str(text).split()
        return " ".join(words[:length]) + ("..." if len(words) > length else "")

    @app.template_filter("slugify")
    def slugify_filter(text):
        text = str(text).lower()
        text = re.sub(r"[^a-z0-9]+", "-", text)
        return text.strip("-")

    @app.template_filter("from_json")
    def from_json_filter(value):
        import json
        if not value:
            return None
        try:
            return json.loads(value)
        except Exception:
            return None
