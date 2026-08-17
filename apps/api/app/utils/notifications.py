"""Canonical helper for creating in-app notifications.

The Notification model has existed for a while and was already being
written to in many places (admin/routes.py, cms/routes.py, comms/routes.py,
payments, automation) — but always via a hand-rolled `Notification(...)`
call with no shared function, and the dashboard bell that's supposed to
surface these to the user was dead UI (static badge, no dropdown, no
click handler). This module is the single place new notification-creating
code should call through, and the dashboard bell (see
app/dashboard/routes.py notification endpoints) is the first real reader.
"""
from datetime import datetime
from app.extensions import db


def notify_user(user_id, type, title, body=None, link=None):
    """Create and persist a notification for a user. Does NOT commit —
    caller decides transaction boundaries (so it can be added to an
    existing commit, e.g. right after marking an order paid)."""
    from app.models.core import Notification
    n = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        link=link,
        read=False,
        created_at=datetime.utcnow(),
    )
    db.session.add(n)
    return n
