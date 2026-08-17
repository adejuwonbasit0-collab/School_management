"""Wallet helpers. Every balance change goes through credit_wallet/debit_wallet
so Wallet.balance and its WalletTransaction ledger can never drift apart —
there is no other code path anywhere that should touch wallet.balance
directly."""
from datetime import datetime
from decimal import Decimal
from app.extensions import db


def get_or_create_wallet(user_id):
    from app.models.platform import Wallet
    from app.utils.settings import default_site_currency
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0, pending_balance=0, currency=default_site_currency())
        db.session.add(wallet)
        db.session.commit()
    return wallet


def credit_wallet(user_id, amount, kind, note=None, reference=None, created_by=None):
    """Adds `amount` (must be positive) to the user's wallet balance and
    records a ledger row. Returns the updated Wallet."""
    from app.models.platform import WalletTransaction
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("credit_wallet amount must be positive")
    wallet = get_or_create_wallet(user_id)
    wallet.balance = Decimal(str(wallet.balance or 0)) + amount
    wallet.updated_at = datetime.utcnow()
    db.session.add(WalletTransaction(wallet_id=wallet.id, kind=kind, amount=amount,
                                      note=note, reference=reference, created_by=created_by))
    db.session.commit()
    return wallet


def debit_wallet(user_id, amount, kind, note=None, reference=None, created_by=None):
    """Removes `amount` (must be positive) from the user's wallet balance,
    if available. Returns (wallet, error) — error is a plain string if the
    balance was insufficient, in which case nothing is changed."""
    from app.models.platform import WalletTransaction
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("debit_wallet amount must be positive")
    wallet = get_or_create_wallet(user_id)
    current_balance = Decimal(str(wallet.balance or 0))
    if current_balance < amount:
        return wallet, f"Insufficient wallet balance (has {current_balance}, needs {amount})"
    wallet.balance = current_balance - amount
    wallet.updated_at = datetime.utcnow()
    db.session.add(WalletTransaction(wallet_id=wallet.id, kind=kind, amount=-amount,
                                      note=note, reference=reference, created_by=created_by))
    db.session.commit()
    return wallet, None


def transfer_wallet(from_user_id, to_user_id, amount, note=None):
    """Moves `amount` from one user's wallet to another's — two ledger
    rows (a debit on the sender, a credit on the recipient), same amount,
    same moment, or neither happens. Returns (ok, error)."""
    amount = Decimal(str(amount))
    if amount <= 0:
        return False, "Amount must be greater than zero."
    if from_user_id == to_user_id:
        return False, "Can't transfer to your own wallet."

    from_wallet, err = debit_wallet(
        from_user_id, amount, kind="transfer_out",
        note=note or "Wallet transfer sent", reference=f"to_user:{to_user_id}",
    )
    if err:
        return False, err
    credit_wallet(
        to_user_id, amount, kind="transfer_in",
        note=note or "Wallet transfer received", reference=f"from_user:{from_user_id}",
    )
    return True, None
