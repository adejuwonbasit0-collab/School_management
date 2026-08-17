"""Real URL shortener — DB-backed redirect, not a stub."""
import random
import string
from datetime import datetime

from flask import Blueprint, redirect, abort, request
from app.extensions import db
from app.models.platform import ShortUrl

shorturl_bp = Blueprint("shorturl", __name__)

ALPHABET = string.ascii_letters + string.digits


def generate_code(length: int = 6) -> str:
    for _ in range(10):
        code = "".join(random.choices(ALPHABET, k=length))
        if not ShortUrl.query.filter_by(code=code).first():
            return code
    # extremely unlikely fallback with a longer code
    return "".join(random.choices(ALPHABET, k=length + 4))


@shorturl_bp.route("/s/<code>")
def resolve(code):
    link = ShortUrl.query.filter_by(code=code).first()
    if not link:
        abort(404)
    link.click_count = (link.click_count or 0) + 1
    link.last_clicked = datetime.utcnow()
    db.session.commit()
    return redirect(link.target_url)
