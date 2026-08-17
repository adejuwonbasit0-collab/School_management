from flask import request
from flask_login import current_user
from app.extensions import db


def log_event(event, path=None, value=None, metadata=None):
    """Record a conversion/outflow event (purchase, signup, form submit,
    download, etc). PageView (written by the /track JS beacon) already
    covers inbound traffic; this is what was missing — nothing in the
    codebase ever wrote to AnalyticsEvent, so the admin dashboard could
    show how many people arrived but nothing about what they actually did.
    Never let a broken analytics write break the real request — same
    fire-and-forget pattern as the audit logger.
    """
    try:
        from app.models.platform import AnalyticsEvent
        try:
            uid = current_user.id if current_user.is_authenticated else None
        except Exception:
            uid = None
        ev = AnalyticsEvent(
            event=event,
            path=path or (request.path if request else None),
            value=str(value) if value is not None else None,
            user_id=uid,
            session_id=(request.cookies.get("session", "") if request else ""),
            event_metadata=metadata or {},
        )
        db.session.add(ev)
        db.session.commit()
    except Exception:
        db.session.rollback()
