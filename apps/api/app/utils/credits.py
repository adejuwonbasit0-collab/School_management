"""AI credit ledger helpers. Every balance change goes through
add_credits/deduct_credits so User.credits and the CreditTransaction
ledger can never drift apart — no other code path should touch
user.credits directly. Mirrors the existing app/utils/wallet.py pattern.

Also implements the 12-hour free-credit refill: users.credits stays the
single TOTAL balance every AI tool already deducts from; free_credits_available
just tracks how much of that total is currently "free allotment" (capped
at FREE_CREDIT_CAP, refills every FREE_CREDIT_REFILL_HOURS) so free and
purchased can be shown separately and free is always spent first, without
needing a second real balance to keep in sync. Refill eligibility is
checked backend-side on every balance read/deduction (ensure_free_refill)
— never on a frontend timer — so it works even if the user was offline
when the 12 hours elapsed.
"""
from datetime import datetime, timedelta
from app.extensions import db

FREE_CREDIT_CAP = 2
FREE_CREDIT_REFILL_HOURS = 12


def ensure_free_refill(user):
    """Backend-authoritative refill check. If FREE_CREDIT_REFILL_HOURS
    have passed since the last check/grant, tops the user's free
    allotment back up to FREE_CREDIT_CAP (never higher — this does not
    stack across missed periods, so someone offline for a week comes
    back to 2 free credits, not dozens) and adds only the difference to
    their total balance. Purchased credits are never touched here — this
    function only ever adds, never subtracts. Safe to call as often as
    needed; it's a no-op outside the refill window. Returns True if a
    top-up was actually granted this call.
    """
    from app.models.platform import CreditTransaction
    now = datetime.utcnow()
    last = user.last_free_credit_refill
    if last is not None and (now - last) < timedelta(hours=FREE_CREDIT_REFILL_HOURS):
        return False

    current_free = user.free_credits_available if user.free_credits_available is not None else 0
    topup = FREE_CREDIT_CAP - current_free
    granted = False
    if topup > 0:
        user.credits = (user.credits or 0) + topup
        user.free_credits_available = FREE_CREDIT_CAP
        db.session.add(CreditTransaction(
            user_id=user.id, type="free_refill", amount=topup, balance_after=user.credits,
            reason="12-hour free credit refill",
        ))
        granted = True
    else:
        user.free_credits_available = FREE_CREDIT_CAP
    user.last_free_credit_refill = now
    db.session.commit()
    return granted


def get_credit_status(user_id):
    """Returns the full picture for the AI Credits dashboard card: total
    balance, the free/purchased split, and when the next free refill
    lands. Runs ensure_free_refill first so the numbers are always
    current, not stale from before an elapsed 12-hour window."""
    from app.models.user import User
    user = User.query.get(user_id)
    if not user:
        return None
    ensure_free_refill(user)
    free = user.free_credits_available or 0
    total = user.credits or 0
    purchased = max(0, total - free)
    next_refill_at = (user.last_free_credit_refill or datetime.utcnow()) + timedelta(hours=FREE_CREDIT_REFILL_HOURS)
    seconds_until_refill = max(0, int((next_refill_at - datetime.utcnow()).total_seconds())) if free < FREE_CREDIT_CAP else 0
    return {
        "total": total, "free": free, "purchased": purchased,
        "free_cap": FREE_CREDIT_CAP, "free_full": free >= FREE_CREDIT_CAP,
        "next_refill_at": next_refill_at.isoformat(), "seconds_until_refill": seconds_until_refill,
    }


def get_balance(user_id):
    from app.models.user import User
    user = User.query.get(user_id)
    if not user:
        return 0
    ensure_free_refill(user)
    return user.credits or 0


def add_credits(user_id, amount, type, reason=None, reference=None, created_by=None):
    """Adds `amount` (must be positive) to the user's credit balance and
    records a ledger row. Returns the updated balance. Never touches
    free_credits_available — a purchase or admin grant is purchased
    credit, not free allotment, so it's correctly excluded from the free
    refill's bookkeeping."""
    from app.models.user import User
    from app.models.platform import CreditTransaction
    amount = int(amount)
    if amount <= 0:
        raise ValueError("add_credits amount must be positive")
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"No such user: {user_id}")
    user.credits = (user.credits or 0) + amount
    db.session.add(CreditTransaction(
        user_id=user_id, type=type, amount=amount, balance_after=user.credits,
        reason=reason, reference=reference, created_by=created_by,
    ))
    db.session.commit()
    return user.credits


def deduct_credits(user_id, amount, type="usage", reason=None, reference=None):
    """Removes `amount` (must be positive) from the user's credit balance,
    if available. Checks free-refill eligibility first (so a user who
    crossed the 12-hour mark while offline gets topped up before the
    balance check, not after), then spends free credits before purchased
    ones. Returns (ok, balance_or_error) — on insufficient balance
    nothing is changed and ok is False."""
    from app.models.user import User
    from app.models.platform import CreditTransaction
    amount = int(amount)
    if amount <= 0:
        raise ValueError("deduct_credits amount must be positive")
    user = User.query.get(user_id)
    if not user:
        return False, "No such user."
    ensure_free_refill(user)
    current = user.credits or 0
    if current < amount:
        return False, f"Insufficient credits (has {current}, needs {amount})"
    free_used = min(user.free_credits_available or 0, amount)
    user.free_credits_available = (user.free_credits_available or 0) - free_used
    user.credits = current - amount
    db.session.add(CreditTransaction(
        user_id=user_id, type=type, amount=-amount, balance_after=user.credits,
        reason=reason, reference=reference,
    ))
    db.session.commit()
    return True, user.credits


AI_REPLY_CREDIT_COST = 1


def charge_ai_reply(user_id):
    """Deducts the cost of one AI Chatbot / WhatsApp Bot reply from the
    BOT OWNER's credit balance (never the visitor's — visitors don't have
    accounts here). Free credits are spent first automatically since
    deduct_credits() already handles that split. Returns (ok,
    message_or_None). On insufficient credits, returns the Doc 9 §22
    unavailable-message so every reply surface (public widget, WhatsApp
    webhook, test panels) shows the same honest, non-crashing response
    instead of silently failing or spending an API call that can't be
    paid for."""
    ok, result = deduct_credits(
        user_id, AI_REPLY_CREDIT_COST, type="usage",
        reason="AI chatbot reply", reference="ai_chatbot_reply",
    )
    if not ok:
        return False, ("This AI assistant is temporarily unavailable. "
                        "The account owner needs to add more AI credits.")
    return True, None


def grant_purchased_credits(purchase):
    """Idempotently finalizes a CreditPurchase: marks it paid, credits the
    user, logs the ledger row, and sends a notification — exactly once.
    Safe to call more than once for the same purchase (e.g. a gateway
    callback firing twice, or a webhook + browser redirect race) since it
    is guarded on purchase.status, the same pattern _mark_order_paid()
    uses for marketplace orders."""
    if purchase.status == "paid":
        return False  # already granted — no-op, not an error
    purchase.status = "paid"
    purchase.updated_at = datetime.utcnow()
    db.session.commit()

    new_balance = add_credits(
        purchase.user_id, purchase.credits, type="purchase",
        reason=f"Purchased {purchase.package.name if purchase.package else 'credit package'}",
        reference=f"credit_purchase:{purchase.id}",
    )

    try:
        from app.utils.notifications import notify_user
        from flask import url_for
        notify_user(
            purchase.user_id,
            type="credits_added",
            title="🎉 Credits Added",
            body=f"{purchase.credits:,} AI credits have been added to your account. New balance: {new_balance:,}.",
            link=url_for("dashboard.credits_home"),
        )
        db.session.commit()
    except Exception:
        from flask import current_app
        current_app.logger.exception(
            "notify_user failed after credit grant for purchase_id=%s user_id=%s — "
            "credits were still granted correctly.", purchase.id, purchase.user_id,
        )
    return True


# ── Custom "quantity stepper" pricing ───────────────────────────────────
# The dashboard's quick-buy widget: N units x credit_unit_size credits at
# credit_unit_price each, e.g. the default 1 unit = 10 credits = $0.50, so
# 2 units = 20 credits = $1.00, and so on linearly. Admin-editable under
# Admin -> Credit Packages -> Pricing (see admin.update_credit_pricing).
# Uses the existing generic settings table (get_setting/set_setting) —
# no dedicated model needed for three numbers.
DEFAULT_CREDIT_UNIT_SIZE = 10
DEFAULT_CREDIT_UNIT_PRICE = 0.5
DEFAULT_CREDIT_MAX_UNITS = 50


def get_credit_unit_pricing():
    from app.utils.settings import get_setting
    return {
        "unit_size": int(get_setting("credit_unit_size", DEFAULT_CREDIT_UNIT_SIZE)),
        "unit_price": float(get_setting("credit_unit_price", DEFAULT_CREDIT_UNIT_PRICE)),
        "max_units": int(get_setting("credit_max_units", DEFAULT_CREDIT_MAX_UNITS)),
    }


def compute_custom_credit_price(units):
    """Given a whole number of units, returns (credits, amount) at the
    current admin-set rate. Raises ValueError for an out-of-range unit
    count so callers get one clear place to validate."""
    pricing = get_credit_unit_pricing()
    units = int(units)
    if units < 1 or units > pricing["max_units"]:
        raise ValueError(f"Quantity must be between 1 and {pricing['max_units']} units.")
    credits = units * pricing["unit_size"]
    amount = round(units * pricing["unit_price"], 2)
    return credits, amount
