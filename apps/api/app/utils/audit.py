from flask import request
from app.extensions import db

def log_action(user_id, action, target=None, detail=None):
    try:
        from app.models.core import AuditLog
        log = AuditLog(
            user_id=user_id,
            action=action,
            target=target,
            detail=detail,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:500],
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
