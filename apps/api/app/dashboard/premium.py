"""Premium product access control for user dashboard features."""
import functools
from flask import redirect, url_for, flash, abort, current_app
from flask_login import current_user
from app.extensions import db


# ── Canonical product slugs ──────────────────────────────────────────
# Only these are real, sellable, user-dashboard products — buy once,
# configure yourself, use from your own dashboard. Everything else that
# used to be listed here (website-builder, ai-chatbot, automation-studio,
# graphics-studio, content-studio, video-studio, social-bot, prompt-library)
# is an ADMIN-ONLY tool, not a product — it was wrongly auto-seeded into
# the marketplace before; that seeding is what needs deleting from your
# Products list, not something this file can undo on its own since the
# rows already exist in your database. Voice Studio is free, and lives in
# public Dev Tools instead of here.

PREMIUM_PRODUCTS = {
    "invoice-generator":      {"name": "Invoice Generator",      "icon": "file-text",     "category": "Finance", "color": "#F59E0B", "endpoint": "dashboard.invoice_generator"},
    "funnel-builder":         {"name": "Sales Funnel Builder",   "icon": "filter",        "category": "Finance", "color": "#8B5CF6", "endpoint": "dashboard.funnel_builder"},
    "payment-link-generator": {"name": "Payment Link Generator", "icon": "link",          "category": "Finance", "color": "#3B82F6", "endpoint": "dashboard.payment_links"},
    "whatsapp-bot":           {"name": "WhatsApp Business Bot",  "icon": "message-circle","category": "Bots",    "color": "#25D366", "endpoint": "dashboard.chatbot_builder"},
    "whatsapp-widget":        {"name": "WhatsApp Chat Widget",   "icon": "message-square-more","category": "Bots", "color": "#25D366", "endpoint": "dashboard.whatsapp_widget"},
    "voice-studio":           {"name": "AI Voice Studio",        "icon": "mic",                "category": "AI Tools", "color": "#8B5CF6", "endpoint": "dashboard.voice_studio"},
    "ai-chatbot":             {"name": "AI Chatbot",             "icon": "bot",           "category": "Bots",    "color": "#A855F7", "endpoint": "dashboard.ai_chatbot"},
}


def ensure_dashboard_tool_products():
    """Idempotently make sure every PREMIUM_PRODUCTS slug has a matching
    Product row, so the Admin > Customer Tools page always has something
    real to manage (pricing, images, demo link, feature list, visibility)
    even on a fresh install where nobody has run a seed script. Safe to
    call on every page load — it only creates rows that don't exist yet
    and never overwrites anything an admin has already edited.
    Returns the list of slugs it had to create (empty list = nothing to do).
    """
    from app.models.commerce import Product
    created = []
    for slug, info in PREMIUM_PRODUCTS.items():
        existing = Product.query.filter_by(slug=slug).first()
        if existing:
            continue
        p = Product(
            title=info["name"],
            slug=slug,
            description=f"{info['name']} — part of your dashboard tool suite.",
            category=info.get("category", "SaaS Tool"),
            type="dashboard_tool",
            price=0,
            status="active",
            license="standard",
            version="1.0.0",
            billing_period="one_time",
            features=[],
            tags=["dashboard-tool"],
        )
        db.session.add(p)
        created.append(slug)
    if created:
        db.session.commit()
    return created


def has_product_access(user, product_slug):
    """Check if a user has active access to a premium product."""
    if user.is_admin():
        return True  # admins have access to everything
    from app.models.commerce import Product
    try:
        product = Product.query.filter_by(slug=product_slug, status="active").first()
        if product and product.effective_price <= 0:
            # A dashboard tool priced at $0 is free — access shouldn't
            # depend on a purchase record that will never exist. Without
            # this, "Launch Tool" on a free tool bounced straight back to
            # "purchase required" since nothing ever calls
            # grant_product_access() for a $0 order.
            return True
    except Exception:
        current_app.logger.exception(f"Product lookup failed for slug={product_slug}")
        db.session.rollback()
    from app.models.platform import UserProductAccess
    from datetime import datetime
    try:
        access = UserProductAccess.query.filter_by(
            user_id=user.id, product_slug=product_slug, active=True
        ).first()
    except Exception:
        # If the UserProductAccess table doesn't exist yet (a pending
        # `flask db upgrade` on this environment) this used to throw a raw
        # 500 the instant anyone opened My Products or clicked a locked
        # tool. Fail closed (no access) instead of crashing the page —
        # the real fix is still running migrations, but nobody should get
        # an error page over it.
        current_app.logger.exception("UserProductAccess lookup failed — have migrations been run? (flask db upgrade)")
        db.session.rollback()
        return False
    if not access:
        # Self-healing fallback: UserProductAccess has no row, but check
        # whether a paid Order for this product exists anyway. This is the
        # exact deadlock a customer could get stuck in otherwise — the
        # checkout page blocks a repurchase because Order.status=="paid"
        # already exists, while this page shows "Buy Now" forever because
        # the automatic grant-on-payment silently never fired. If a paid
        # order is found, grant access now (repairing it permanently)
        # instead of leaving the customer stuck with no way forward.
        try:
            from app.models.commerce import Order
            paid_order = (Order.query.join(Product, Order.product_id == Product.id)
                          .filter(Order.user_id == user.id, Order.status == "paid", Product.slug == product_slug)
                          .first())
        except Exception:
            current_app.logger.exception(f"Fallback paid-order lookup failed for user={user.id}, product={product_slug}")
            db.session.rollback()
            paid_order = None
        if paid_order:
            current_app.logger.warning(
                f"Repairing missing UserProductAccess: user={user.id} has a paid order (#{paid_order.id}) "
                f"for '{product_slug}' but was never granted access. Granting now."
            )
            grant_product_access(user, product_slug, order=paid_order)
            return True
        return False
    if access.expires_at and access.expires_at < datetime.utcnow():
        return False
    return True


def require_premium(product_slug):
    """Decorator that checks premium product access before allowing route."""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this feature.", "info")
                return redirect(url_for("auth.login"))
            if not has_product_access(current_user, product_slug):
                flash(f"This feature requires the {PREMIUM_PRODUCTS.get(product_slug, {}).get('name', product_slug)} product. Purchase it from the marketplace to unlock.", "warning")
                return redirect(url_for("marketplace.product_detail", slug=product_slug))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_any_premium(*product_slugs):
    """Like require_premium, but passes if the user owns ANY one of
    several products — for shared infrastructure pages that more than
    one premium product depends on.

    Added because /payment-gateways (where Stripe/Paystack/etc.
    credentials get connected) was gated to payment-link-generator
    only, even though funnel_checkout.py's live checkout pages read
    from that same UserPaymentGateway table via
    get_user_enabled_gateways(). A customer who bought only the Sales
    Funnel Builder — never Payment Links — had no way to reach the page
    that lets them connect a gateway at all, so every funnel checkout
    they built would show "No payment methods are available" with no
    way to fix it from inside the product they actually paid for."""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this feature.", "info")
                return redirect(url_for("auth.login"))
            if not any(has_product_access(current_user, slug) for slug in product_slugs):
                names = " or ".join(PREMIUM_PRODUCTS.get(s, {}).get("name", s) for s in product_slugs)
                flash(f"This feature requires {names}. Purchase one from the marketplace to unlock.", "warning")
                return redirect(url_for("marketplace.product_detail", slug=product_slugs[0]))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def grant_product_access(user, product_slug, order=None, expires_at=None):
    """Grant a user access to a premium dashboard product."""
    from app.models.platform import UserProductAccess
    existing = UserProductAccess.query.filter_by(
        user_id=user.id, product_slug=product_slug
    ).first()
    if existing:
        existing.active = True
        existing.activated_at = __import__('datetime').datetime.utcnow()
        if order:
            existing.order_id = order.id
        if expires_at:
            existing.expires_at = expires_at
        db.session.commit()
        return existing
    access = UserProductAccess(
        user_id=user.id,
        product_slug=product_slug,
        order_id=order.id if order else None,
        expires_at=expires_at,
    )
    db.session.add(access)
    db.session.commit()
    return access


def revoke_product_access(user, product_slug):
    """Revoke a user's access to a premium dashboard product."""
    from app.models.platform import UserProductAccess
    access = UserProductAccess.query.filter_by(
        user_id=user.id, product_slug=product_slug
    ).first()
    if access:
        access.active = False
        db.session.commit()
    return access


def get_user_products(user):
    """Return a list of all premium products with their access status for
    this user. Uses has_product_access() as the single source of truth —
    previously this had its OWN separate, incomplete reimplementation
    (only checked UserProductAccess rows, missing both the $0-free-product
    rule and the paid-order reconciliation fallback that has_product_access()
    already had), so the sidebar/My Products could show a locked padlock —
    and a dead '#' link when no marketplace Product row existed yet either —
    on a tool the user could actually already use. One canonical check now."""
    products = []
    for slug, info in PREMIUM_PRODUCTS.items():
        from app.models.commerce import Product
        try:
            mp_product = Product.query.filter_by(slug=slug, status="active").first()
        except Exception:
            current_app.logger.exception(f"Product lookup failed for slug={slug}")
            db.session.rollback()
            mp_product = None
        unlocked = bool(user.is_authenticated) and has_product_access(user, slug)
        products.append({
            "slug": slug,
            "name": info["name"],
            "icon": info["icon"],
            "category": info["category"],
            "color": info["color"],
            "endpoint": info.get("endpoint"),
            "unlocked": unlocked,
            "price": float(mp_product.effective_price) if mp_product else None,
            "currency": mp_product.currency if mp_product else None,
            "product_id": mp_product.id if mp_product else None,
            "product_slug": mp_product.slug if mp_product else slug,
        })
    return products
