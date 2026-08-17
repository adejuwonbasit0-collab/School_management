from flask import Blueprint, render_template, request, jsonify, abort, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from app.extensions import db, limiter
from app.models.core import Message
from app.models.user import User

comms_bp = Blueprint("comms", __name__)


def _thread_id(uid1: int, uid2: int) -> str:
    a, b = sorted([int(uid1), int(uid2)])
    return f"{a}-{b}"


def _other_user_id(thread_id: str, my_id: int) -> int:
    a, b = thread_id.split("-")
    a, b = int(a), int(b)
    return b if a == my_id else a


@comms_bp.route("/messages")
@login_required
def messages():
    """Conversation list: latest message per thread, with unread counts."""
    my_id = current_user.id
    all_msgs = (Message.query
                .filter(or_(Message.sender_id == my_id, Message.receiver_id == my_id))
                .order_by(Message.created_at.desc())
                .all())
    threads = {}
    for m in all_msgs:
        tid = m.thread_id or _thread_id(m.sender_id, m.receiver_id)
        if tid not in threads:
            other_id = m.receiver_id if m.sender_id == my_id else m.sender_id
            other = User.query.get(other_id)
            threads[tid] = {
                "thread_id": tid,
                "other_user": other,
                "last_message": m,
                "unread_count": 0,
            }
    # unread counts
    unread_rows = (db.session.query(Message.thread_id, func.count(Message.id))
                   .filter(Message.receiver_id == my_id, Message.read == False)  # noqa: E712
                   .group_by(Message.thread_id).all())
    for tid, count in unread_rows:
        if tid in threads:
            threads[tid]["unread_count"] = count
    conversations = sorted(threads.values(), key=lambda t: t["last_message"].created_at, reverse=True)
    total_unread = sum(c["unread_count"] for c in conversations)
    return render_template("comms/messages.html", conversations=conversations, total_unread=total_unread)


@comms_bp.route("/messages/<thread_id>")
@login_required
def thread(thread_id):
    my_id = current_user.id
    try:
        other_id = _other_user_id(thread_id, my_id)
    except Exception:
        abort(404)
    other = User.query.get_or_404(other_id)
    msgs = (Message.query
            .filter(Message.thread_id == thread_id)
            .order_by(Message.created_at.asc())
            .all())
    if not msgs:
        # fall back to legacy rows created before thread_id existed
        msgs = (Message.query
                .filter(or_(
                    db.and_(Message.sender_id == my_id, Message.receiver_id == other_id),
                    db.and_(Message.sender_id == other_id, Message.receiver_id == my_id),
                ))
                .order_by(Message.created_at.asc()).all())
    # mark incoming as read
    unread = [m for m in msgs if m.receiver_id == my_id and not m.read]
    for m in unread:
        m.read = True
    if unread:
        db.session.commit()
    return render_template("comms/thread.html", other_user=other, thread_id=thread_id, msgs=msgs)


@comms_bp.route("/messages/<thread_id>/poll")
@login_required
def poll_thread(thread_id):
    """Lightweight polling endpoint for new messages since a given message id."""
    my_id = current_user.id
    since = request.args.get("since", 0, type=int)
    try:
        other_id = _other_user_id(thread_id, my_id)
    except Exception:
        return jsonify({"error": "Invalid thread"}), 400
    new_msgs = (Message.query
                .filter(Message.thread_id == thread_id, Message.id > since)
                .order_by(Message.created_at.asc()).all())
    # auto-mark incoming as read since the user has the thread open
    incoming_unread = [m for m in new_msgs if m.receiver_id == my_id and not m.read]
    for m in incoming_unread:
        m.read = True
    if incoming_unread:
        db.session.commit()
    return jsonify({
        "messages": [
            {
                "id": m.id,
                "content": m.content,
                "sender_id": m.sender_id,
                "is_mine": m.sender_id == my_id,
                "created_at": m.created_at.strftime("%H:%M"),
            } for m in new_msgs
        ]
    })


@comms_bp.route("/messages/send", methods=["POST"])
@login_required
def send_message():
    receiver_id = request.form.get("receiver_id", type=int) or (request.get_json(silent=True) or {}).get("receiver_id")
    content = (request.form.get("content") or (request.get_json(silent=True) or {}).get("content") or "").strip()
    if not receiver_id or not content:
        return jsonify({"error": "Missing fields"}), 400
    receiver_id = int(receiver_id)
    if receiver_id == current_user.id:
        return jsonify({"error": "Cannot message yourself."}), 400
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({"error": "Recipient not found."}), 404
    tid = _thread_id(current_user.id, receiver_id)
    msg = Message(sender_id=current_user.id, receiver_id=receiver_id, content=content, thread_id=tid)
    db.session.add(msg)

    from app.models.core import Notification
    from app.utils.email import send_email
    preview = content if len(content) <= 120 else content[:117] + "…"
    
    # Context-aware routing for message notifications
    notif_link = url_for("comms.thread", thread_id=tid)
    if receiver and receiver.is_client():
        notif_link = url_for("dashboard.home") + "?tab=messages"

    db.session.add(Notification(
        user_id=receiver_id, type="message", title=f"New message from {current_user.name or current_user.email}",
        body=preview, link=notif_link,
    ))
    db.session.commit()
    if receiver.email:
        send_email(
            to=receiver.email, subject=f"New message from {current_user.name or current_user.email}",
            body_html=f"<p><strong>{current_user.name or current_user.email}</strong> sent you a message:</p>"
                      f"<blockquote style='border-left:3px solid #1DB954;padding-left:12px;color:#555'>{preview}</blockquote>"
                      f"<p><a href='{url_for('comms.thread', thread_id=tid, _external=True)}' "
                      f"style='display:inline-block;padding:10px 20px;background:#1DB954;color:#000;text-decoration:none;border-radius:8px;font-weight:bold'>Reply</a></p>",
        )
    return jsonify({
        "success": True, "id": msg.id, "thread_id": tid,
        "created_at": msg.created_at.strftime("%H:%M"),
    })


@comms_bp.route("/messages/search-users")
@login_required
def search_users():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"users": []})
    results = (User.query
               .filter(User.id != current_user.id)
               .filter(or_(User.email.ilike(f"%{q}%"), User.name.ilike(f"%{q}%")))
               .limit(10).all())
    return jsonify({"users": [{"id": u.id, "name": u.name or u.email, "email": u.email} for u in results]})


@comms_bp.route("/messages/unread-count")
@login_required
@limiter.exempt
def unread_count():
    count = Message.query.filter_by(receiver_id=current_user.id, read=False).count()
    return jsonify({"count": count})
