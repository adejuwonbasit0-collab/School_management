from flask import Blueprint, request, jsonify
from flask_login import current_user
from app.extensions import db
from app.models.platform import PageView

analytics_bp = Blueprint("analytics", __name__)


def _detect_device(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if any(k in ua for k in ("ipad", "tablet")):
        return "tablet"
    if any(k in ua for k in ("mobi", "iphone", "android")):
        return "mobile"
    return "desktop"


@analytics_bp.route("/track", methods=["POST"])
def track():
    try:
        data = request.get_json(silent=True) or {}
        path = data.get("path", request.referrer or "/")
        pv = PageView(
            path=path,
            referrer=request.referrer or "",
            device=_detect_device(request.headers.get("User-Agent", "")),
            session_id=request.cookies.get("session", ""),
            user_id=current_user.id if current_user.is_authenticated else None,
        )
        db.session.add(pv)
        db.session.commit()
    except Exception:
        db.session.rollback()
    return jsonify({"ok": True})
