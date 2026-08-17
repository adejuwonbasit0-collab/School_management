"""Real numbers for "what happened over this period" — used by the
get_achievement_summary agent tool. Every figure here is a real DB query,
not a guess or an AI-invented estimate."""
from datetime import datetime, timedelta


def _period_start(period):
    now = datetime.utcnow()
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # default: week (last 7 days, rolling — simpler and more useful than
    # "since Monday" when this could be asked on any day)
    return now - timedelta(days=7)


def get_achievement_summary(period="week"):
    if period not in ("today", "week", "month"):
        period = "week"
    since = _period_start(period)

    from app.models.platform import Lead, ClientProject, Invoice
    from app.models.commerce import Order
    from app.models.user import User
    from app.extensions import db
    from sqlalchemy import func

    new_leads = Lead.query.filter(Lead.created_at >= since).count()
    won_leads = Lead.query.filter(Lead.deal_stage == "won", Lead.created_at >= since).count()
    won_value = db.session.query(func.coalesce(func.sum(Lead.deal_value), 0)) \
        .filter(Lead.deal_stage == "won", Lead.created_at >= since).scalar() or 0

    completed_projects = ClientProject.query.filter(
        ClientProject.status == "completed", ClientProject.completed_at >= since
    ).count()

    invoice_revenue = db.session.query(func.coalesce(func.sum(Invoice.amount_paid), 0)) \
        .filter(Invoice.status == "paid", Invoice.paid_at >= since).scalar() or 0
    order_revenue = db.session.query(func.coalesce(func.sum(Order.amount), 0)) \
        .filter(Order.status == "paid", Order.updated_at >= since).scalar() or 0
    total_revenue = float(invoice_revenue) + float(order_revenue)

    new_signups = User.query.filter(User.created_at >= since).count()

    label = {"today": "today", "week": "the last 7 days", "month": "this month"}[period]
    return (
        f"Achievement summary for {label}:\n"
        f"- New leads: {new_leads}\n"
        f"- Deals won: {won_leads} (worth {won_value:,.2f})\n"
        f"- Projects completed: {completed_projects}\n"
        f"- Revenue collected: {total_revenue:,.2f}\n"
        f"- New signups: {new_signups}"
    )
