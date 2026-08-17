"""
Processes due steps for email drip sequences (Welcome Series, Follow-Up,
etc.). Run via an external cron hitting /cron/send-email-sequences, same
pattern as the scheduled-broadcast and DB-backup crons elsewhere in this
project — there's no internal task queue/scheduler set up, so something
outside the app has to actually trigger this on a timer (e.g. hourly).
"""
from datetime import datetime, timedelta


def enroll_subscriber(sequence, subscriber):
    """Enrolls a subscriber in a sequence, unless already enrolled."""
    from app.extensions import db
    from app.models.core import EmailSequenceEnrollment

    existing = EmailSequenceEnrollment.query.filter_by(
        sequence_id=sequence.id, subscriber_id=subscriber.id).first()
    if existing:
        return existing
    enrollment = EmailSequenceEnrollment(sequence_id=sequence.id, subscriber_id=subscriber.id)
    db.session.add(enrollment)
    db.session.commit()
    return enrollment


def send_due_sequence_emails():
    """Finds every enrollment whose next step is due, sends it, and
    advances that enrollment to the following step. Returns how many
    emails actually went out (for the cron endpoint's response)."""
    from app.extensions import db
    from app.models.core import EmailSequenceEnrollment
    from app.utils.email import send_email

    sent = 0
    enrollments = EmailSequenceEnrollment.query.filter_by(completed=False).all()
    for enr in enrollments:
        seq = enr.sequence
        sub = enr.subscriber
        if not seq or not seq.active or not sub:
            enr.completed = True
            db.session.commit()
            continue
        if sub.unsubscribed:
            enr.completed = True
            db.session.commit()
            continue

        steps = seq.steps  # ordered by step_order
        if enr.current_step >= len(steps):
            enr.completed = True
            db.session.commit()
            continue

        step = steps[enr.current_step]
        due_at = enr.enrolled_at + timedelta(days=step.delay_days)
        if datetime.utcnow() < due_at:
            continue  # not due yet

        body = (step.body_html or "").replace("{{name}}", sub.name or "there").replace(
            "{{unsubscribe_url}}", f"/newsletter/unsubscribe/{sub.ensure_token()}")
        try:
            ok = send_email(sub.email, step.subject, body)
        except Exception:
            ok = False
        if ok:
            enr.current_step += 1
            enr.last_sent_at = datetime.utcnow()
            if enr.current_step >= len(steps):
                enr.completed = True
            db.session.commit()
            sent += 1
        # if send fails (e.g. SMTP down), leave the enrollment as-is —
        # the next cron run will just retry the same step, nothing is lost
    return sent
