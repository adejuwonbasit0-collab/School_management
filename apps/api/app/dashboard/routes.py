"""
User Dashboard Blueprint
SaaS-grade workspace where users manage all purchased premium tools.
"""
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort, current_app, make_response
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.dashboard.premium import (
    PREMIUM_PRODUCTS, has_product_access, require_premium, require_any_premium,
    get_user_products, grant_product_access,
)

dashboard_bp = Blueprint("dashboard", __name__)


def _admin_only(f):
    """Website Builder / Graphics / Content / Video / Automation Studio
    aren't sellable products — they're admin-only tools that used to be
    wrongly gated behind @require_premium (meaning a regular user could
    buy their way in, and even the site admin couldn't use them without
    owning a "purchase" of their own tool). This just requires admin,
    same as the equivalent tools already in /admin."""
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Context processor: inject products into every dashboard template ──

@dashboard_bp.before_request
def _require_login():
    """All dashboard routes require authentication EXCEPT the public-facing
    ones: a customer's published website/funnel, someone paying a Payment
    Link, a chatbot widget embedded on a third-party site, and a public
    site's own form submissions. Those are used by anonymous visitors who
    will never have — and should never need — an account on this site.
    A blanket @login_required on the whole blueprint was silently
    redirecting every one of those visitors to /login instead of letting
    them see the actual page, which breaks the entire point of a
    published/sellable product having a public side at all."""
    public_endpoints = {
        "dashboard.serve_website",
        "dashboard.serve_funnel",
        "dashboard.funnel_track",
        "dashboard.funnel_lead_submit",
        "dashboard.funnel_checkout_start",
        "dashboard.funnel_checkout_callback",
        "dashboard.pay_link_view",
        "dashboard.pay_link_checkout",
        "dashboard.pay_link_callback",
        "dashboard.site_submit_form",
        "dashboard.chatbot_embed",
        "dashboard.chatbot_reply",
        # WhatsApp Chat Widget — same class of bug as the others above:
        # these are loaded/called by anonymous visitors on the WIDGET
        # OWNER'S website, not by the owner themselves. Without this
        # exemption, every third-party page embedding the widget gets a
        # login-page redirect back instead of the actual script, which
        # is why the widget silently failed to render anywhere it was
        # pasted.
        "dashboard.whatsapp_widget_public",
        "dashboard.whatsapp_widget_embed_js",
        "dashboard.whatsapp_widget_view",
        "dashboard.whatsapp_widget_click",
    }
    if request.endpoint in public_endpoints:
        return None
    if not current_user.is_authenticated:
        return current_app.login_manager.unauthorized()
    return None


@dashboard_bp.context_processor
def _inject_dashboard_context():
    """Make product access list and user info available in all dashboard templates."""
    products = get_user_products(current_user) if current_user.is_authenticated else []
    return {
        "products": products,
        "dash_products": products,
        "user_credits": current_user.credits if current_user.is_authenticated else 0,
    }


# ══════════════════════════════════════════════════════════════════════
#  DASHBOARD HOME
# ══════════════════════════════════════════════════════════════════════

@dashboard_bp.route("/")
def home():
    """Main unified user dashboard (the 'second dashboard').
    Provides summary of products, creations, notifications, and orders."""
    from app.models.commerce import Order, Product, Download
    from app.models.platform import (
        UserWebsite, UserFunnel, UserInvoice as UIModel, Invoice,
        UserPaymentLink, AutomationWorkflow, ProjectRequest, ClientProject
    )
    from app.models.core import Message, Notification

    # Stats
    orders = Order.query.filter_by(user_id=current_user.id, status="paid").all()
    total_spent = sum(float(o.amount or 0) for o in orders)
    download_count = Download.query.filter_by(user_id=current_user.id).count()
    credits = current_user.credits

    # Recent activity
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).limit(10).all()

    unread_count = Notification.query.filter_by(
        user_id=current_user.id, read=False
    ).count()

    # Recent orders
    recent_orders = Order.query.filter_by(
        user_id=current_user.id, status="paid"
    ).order_by(Order.created_at.desc()).limit(5).all()

    # Count user's creations
    try:
        website_count = UserWebsite.query.filter_by(user_id=current_user.id).count()
    except Exception:
        website_count = 0
    try:
        funnel_count = UserFunnel.query.filter_by(user_id=current_user.id).count()
    except Exception:
        funnel_count = 0
    try:
        invoice_count = UIModel.query.filter_by(user_id=current_user.id).count()
    except Exception:
        invoice_count = 0

    # Badges for sidebar
    pending_proposals = ProjectRequest.query.filter_by(user_id=current_user.id, status="quoted").count()
    unpaid_invoices = (Invoice.query.join(ClientProject, Invoice.project_id == ClientProject.id)
                       .filter(ClientProject.client_id == current_user.id, Invoice.status == "unpaid").count())
    unread_messages = Message.query.filter_by(receiver_id=current_user.id, read=False).count()
    badges = {
        "requests": pending_proposals,
        "billing": unpaid_invoices,
        "messages": unread_messages,
    }

    # Products access summary
    products = get_user_products(current_user)
    unlocked_count = sum(1 for p in products if p["unlocked"])

    return render_template("dashboard/home.html",
        total_spent=total_spent,
        download_count=download_count,
        credits=credits,
        notifications=notifications,
        unread_count=unread_count,
        recent_orders=recent_orders,
        unlocked_count=unlocked_count,
        total_products=len(products),
        website_count=website_count,
        funnel_count=funnel_count,
        invoice_count=invoice_count,
        badges=badges,
    )


# ══════════════════════════════════════════════════════════════════════
#  MY PRODUCTS
# ══════════════════════════════════════════════════════════════════════

@dashboard_bp.route("/products")
def my_products():
    """Grid of all premium products with lock/unlock status."""
    products = get_user_products(current_user)
    # Group by category
    categories = {}
    for p in products:
        cat = p["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(p)
    return render_template("dashboard/my_products.html",
        products=products,
        categories=categories,
    )


# ══════════════════════════════════════════════════════════════════════
#  SALES FUNNEL BUILDER — Foundation (Milestone 1)
#  Real per-page rows (FunnelPage) instead of a single JSON blob, with
#  a linear next_page_id chain plus optional branch_yes_id/branch_no_id
#  for upsell/downsell-style accept/decline routing.
# ══════════════════════════════════════════════════════════════════════

FUNNEL_TYPE_LABELS = {
    "landing": "Landing Page", "sales": "Sales Page", "checkout": "Checkout Page",
    "thank_you": "Thank You Page", "upsell": "Upsell", "downsell": "Downsell",
    "webinar_registration": "Webinar Registration", "webinar_replay": "Webinar Replay",
    "booking": "Booking Page", "lead_capture": "Lead Capture Page", "survey": "Survey",
    "quiz": "Quiz", "application": "Application Form",
    "membership_login": "Membership Login", "membership_registration": "Membership Registration",
    "order_confirmation": "Order Confirmation", "custom": "Custom Page",
}

FUNNEL_AI_TYPE_PROMPTS = {
    "landing": "high-converting landing page with email opt-in form, compelling headline, benefits list, social proof, and strong CTA",
    "sales": "long-form sales page with problem-agitation-solution structure, testimonials, pricing, guarantees, FAQ, and buy now buttons",
    "checkout": "clean checkout page with order summary, payment form, security badges, and money-back guarantee",
    "thank_you": "thank you / confirmation page with order details and next steps",
    "upsell": "one-time offer / upsell page with countdown timer, special deal pricing, and a Yes/No decision (use data-funnel-nav=\"accept\" on the accept button and data-funnel-nav=\"decline\" on the decline link)",
    "downsell": "downsell page with reduced offer and simple accept/decline (use data-funnel-nav=\"accept\" and data-funnel-nav=\"decline\" on the two buttons)",
    "webinar_registration": "webinar registration page with countdown, speaker bio, what you'll learn, and registration form",
    "webinar_replay": "webinar replay page with an embedded video player placeholder and a CTA below it",
    "booking": "appointment booking page with calendar placeholder, service details, and booking form",
    "lead_capture": "simple lead capture page with a short form (name + email) and one clear benefit statement",
    "survey": "short survey page with 3-5 multiple choice questions and a submit button",
    "quiz": "interactive-feeling quiz landing page with a start button",
    "application": "application form page with several qualifying questions",
    "membership_login": "clean membership login page with email/password fields",
    "membership_registration": "membership registration/signup page with a short form",
    "order_confirmation": "order confirmation page summarizing what was purchased",
    "custom": "clean, on-brand page",
}


def _funnel_page_url(funnel, page):
    if not page:
        return None
    return url_for("dashboard.serve_funnel", subdomain=funnel.subdomain, page_slug=page.slug)


def _serialize_funnel(f):
    from app.models.platform import FunnelPage
    pages = f.ordered_pages()
    smtp_creds = f.get_smtp_credentials() if f.smtp_connected else None
    return {
        "id": f.id, "title": f.title, "slug": f.slug,
        "published": bool(f.published), "subdomain": f.subdomain,
        "entry_page_id": f.entry_page_id,
        "pages": [p.to_dict() for p in pages],
        "settings": f.settings or {},
        "view_count": f.view_count or 0,
        "conversion_count": f.conversion_count or 0,
        "smtp_connected": bool(f.smtp_connected),
        "smtp_summary": {"host": smtp_creds.get("host"), "username": smtp_creds.get("username"),
                          "from_email": smtp_creds.get("from_email")} if smtp_creds else None,
        "canvas_positions": f.canvas_positions or {},
    }


def _relink_chain(funnel_id):
    """Re-derive the linear next_page_id chain from order_index. Called
    after add/delete/reorder so the main flow always matches what's
    shown in the visual builder. Branch links (accept/decline) are left
    untouched — they're set explicitly via the connect endpoint."""
    from app.models.platform import FunnelPage
    pages = FunnelPage.query.filter_by(funnel_id=funnel_id).order_by(FunnelPage.order_index.asc()).all()
    for i, p in enumerate(pages):
        p.next_page_id = pages[i + 1].id if i + 1 < len(pages) else None
    return pages


# @dashboard_bp.route("/funnel-builder")
# @require_premium("funnel-builder")
# def funnel_builder():
#     """Sales Funnel Builder workspace."""
#     from app.models.platform import UserFunnel
#     from app.utils.funnel_blocks import BLOCK_SCHEMAS
#     from app.utils.payments import get_user_enabled_gateways
#     funnels = UserFunnel.query.filter_by(
#         user_id=current_user.id
#     ).order_by(UserFunnel.updated_at.desc()).all()
#     funnels_json = [_serialize_funnel(f) for f in funnels]
#     return render_template(
#         "dashboard/funnel_builder.html", funnels=funnels, funnels_json=funnels_json,
#         page_types=FUNNEL_TYPE_LABELS, block_schemas=BLOCK_SCHEMAS,
#         connected_gateways=get_user_enabled_gateways(current_user.id),
#     )


@dashboard_bp.route("/funnel-builder")
@require_premium("funnel-builder")
def funnel_builder():
    """Sales Funnel Builder workspace."""
    from app.models.platform import UserFunnel
    from app.utils.funnel_blocks import BLOCK_SCHEMAS, DESIGN_SCHEMA
    from app.utils.payments import get_user_enabled_gateways
    funnels = UserFunnel.query.filter_by(
        user_id=current_user.id
    ).order_by(UserFunnel.updated_at.desc()).all()
    funnels_json = [_serialize_funnel(f) for f in funnels]
    return render_template(
        "dashboard/funnel_builder.html", funnels=funnels, funnels_json=funnels_json,
        page_types=FUNNEL_TYPE_LABELS, block_schemas=BLOCK_SCHEMAS,
        # Bug fix: this used to be built from BLOCK_SCHEMAS (wrong shape
        # entirely — block content fields, not style fields), which is why
        # the Design tab in the builder never had real typography/color/
        # spacing/animation controls to render. Now sourced from the real
        # DESIGN_SCHEMA in funnel_blocks.py.
        design_schema=DESIGN_SCHEMA,
        connected_gateways=get_user_enabled_gateways(current_user.id),
    )

@dashboard_bp.route("/funnel-builder/create", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_create():
    """Create a new, empty funnel."""
    from app.models.platform import UserFunnel
    import re, secrets
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Untitled Funnel").strip() or "Untitled Funnel"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "funnel"
    slug = f"{slug}-{secrets.token_hex(3)}"
    funnel = UserFunnel(user_id=current_user.id, title=title, slug=slug)
    db.session.add(funnel)
    db.session.commit()
    return jsonify({"funnel": _serialize_funnel(funnel), "message": "Funnel created."})


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/rename", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_rename(funnel_id):
    from app.models.platform import UserFunnel
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required."}), 400
    funnel.title = title
    funnel.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Funnel renamed.", "title": funnel.title})


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/delete", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_delete(funnel_id):
    """Delete a funnel (pages cascade automatically)."""
    from app.models.platform import UserFunnel, FunnelPage
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    # Pages can reference each other (next/accept/decline links), which
    # forms a cycle SQLAlchemy's cascade delete can't order on its own —
    # break the links first so the cascade delete below has nothing
    # circular left to resolve.
    FunnelPage.query.filter_by(funnel_id=funnel_id).update(
        {"next_page_id": None, "branch_yes_id": None, "branch_no_id": None}
    )
    db.session.flush()
    db.session.delete(funnel)
    db.session.commit()
    return jsonify({"message": "Funnel deleted."})


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/publish", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_publish(funnel_id):
    """Publish a funnel. The entry page is whichever page currently sits
    first in the order (order_index 0)."""
    from app.models.platform import UserFunnel
    import secrets
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    pages = funnel.ordered_pages()
    if not pages:
        return jsonify({"error": "Add at least one page before publishing."}), 400
    if not funnel.subdomain:
        funnel.subdomain = f"funnel-{secrets.token_hex(4)}"
    funnel.entry_page_id = pages[0].id
    funnel.published = True
    funnel.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({
        "message": "Funnel published!",
        "url": _funnel_page_url(funnel, pages[0]),
        "subdomain": funnel.subdomain,
    })


@dashboard_bp.route("/funnel-builder/templates")
@require_premium("funnel-builder")
def funnel_builder_templates():
    """List available starter page templates."""
    from app.utils.funnel_templates import list_templates
    return jsonify({"templates": list_templates()})


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/pages/add", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_page_add(funnel_id):
    """Add a page to the end of the funnel's flow. Optionally seeded from
    a starter template (data.template_id) — pre-fills real Blocks-mode
    content instead of a blank AI-mode page."""
    from app.models.platform import UserFunnel, FunnelPage
    from app.utils.funnel_templates import get_template
    from app.utils.funnel_blocks import render_blocks_to_html
    import re
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    template = get_template(data.get("template_id")) if data.get("template_id") else None
    page_type = (template["page_type"] if template else data.get("page_type", "custom"))
    if page_type not in FUNNEL_TYPE_LABELS:
        page_type = "custom"
    title = (data.get("title") or (template["label"] if template else FUNNEL_TYPE_LABELS[page_type])).strip()

    existing = funnel.ordered_pages()
    next_order = (existing[-1].order_index + 1) if existing else 0
    base_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or page_type
    slug = base_slug
    used = {p.slug for p in existing}
    n = 2
    while slug in used:
        slug = f"{base_slug}-{n}"
        n += 1

    if template:
        blocks = template["blocks"]
        page = FunnelPage(
            funnel_id=funnel.id, page_type=page_type, title=title, slug=slug,
            order_index=next_order, builder_mode="blocks", blocks=blocks,
            html_content="",
        )
    else:
        page = FunnelPage(
            funnel_id=funnel.id, page_type=page_type, title=title, slug=slug,
            order_index=next_order, html_content="", builder_mode="ai",
        )
    db.session.add(page)
    db.session.flush()
    if template:
        # Rendered after flush (not before) so a Form block's submit URL
        # can be baked in with a real page.id — rendering before the row
        # exists would leave the form posting to a URL with no id at all.
        page.html_content = render_blocks_to_html(template["blocks"], title=title, page_id=page.id)

    if existing:
        existing[-1].next_page_id = page.id
    else:
        funnel.entry_page_id = page.id
    funnel.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"page": page.to_dict(), "funnel": _serialize_funnel(funnel)})


@dashboard_bp.route("/funnel-builder/pages/<int:page_id>/update", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_page_update(page_id):
    """Update a page's title/type/HTML content."""
    from app.models.platform import FunnelPage, UserFunnel
    page = (FunnelPage.query.join(UserFunnel, FunnelPage.funnel_id == UserFunnel.id)
            .filter(FunnelPage.id == page_id, UserFunnel.user_id == current_user.id).first_or_404())
    data = request.get_json(silent=True) or {}
    if "title" in data and (data["title"] or "").strip():
        page.title = data["title"].strip()
    if "page_type" in data and data["page_type"] in FUNNEL_TYPE_LABELS:
        page.page_type = data["page_type"]
    if "html" in data:
        page.html_content = data["html"] or ""
        page.builder_mode = "code"
    page.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"page": page.to_dict(), "message": "Page saved."})


@dashboard_bp.route("/funnel-builder/pages/<int:page_id>/blocks/defaults")
@require_premium("funnel-builder")
def funnel_builder_page_blocks_defaults(page_id):
    """Starter blocks for a page that hasn't been built in Block mode yet."""
    from app.models.platform import FunnelPage, UserFunnel
    from app.utils.funnel_blocks import default_blocks_for_type
    page = (FunnelPage.query.join(UserFunnel, FunnelPage.funnel_id == UserFunnel.id)
            .filter(FunnelPage.id == page_id, UserFunnel.user_id == current_user.id).first_or_404())
    return jsonify({"blocks": default_blocks_for_type(page.page_type)})


@dashboard_bp.route("/funnel-builder/pages/<int:page_id>/blocks/preview", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_page_blocks_preview(page_id):
    """Render blocks to HTML for the live preview pane WITHOUT saving —
    lets the Block Builder show an accurate preview as you edit without
    writing to the database on every keystroke."""
    from app.models.platform import FunnelPage, UserFunnel
    from app.utils.funnel_blocks import render_blocks_to_html
    page = (FunnelPage.query.join(UserFunnel, FunnelPage.funnel_id == UserFunnel.id)
            .filter(FunnelPage.id == page_id, UserFunnel.user_id == current_user.id).first_or_404())
    data = request.get_json(silent=True) or {}
    blocks = data.get("blocks") or []
    if not isinstance(blocks, list):
        return jsonify({"error": "blocks must be a list."}), 400
    html = render_blocks_to_html(blocks, title=page.title, page_id=page.id)
    return jsonify({"html": html})


@dashboard_bp.route("/funnel-builder/pages/<int:page_id>/blocks/save", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_page_blocks_save(page_id):
    """Save the Block Builder's structured content. html_content is
    regenerated from blocks every save so `blocks` stays the single
    source of truth for pages built this way — the served page and the
    editor can never drift apart."""
    from app.models.platform import FunnelPage, UserFunnel
    from app.utils.funnel_blocks import render_blocks_to_html
    page = (FunnelPage.query.join(UserFunnel, FunnelPage.funnel_id == UserFunnel.id)
            .filter(FunnelPage.id == page_id, UserFunnel.user_id == current_user.id).first_or_404())
    data = request.get_json(silent=True) or {}
    blocks = data.get("blocks") or []
    if not isinstance(blocks, list):
        return jsonify({"error": "blocks must be a list."}), 400
    page.blocks = blocks
    page.html_content = render_blocks_to_html(blocks, title=page.title, page_id=page.id)
    page.builder_mode = "blocks"
    page.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"page": page.to_dict(), "message": "Page saved."})


@dashboard_bp.route("/funnel-builder/pages/<int:page_id>/delete", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_page_delete(page_id):
    """Delete a page and relink the pages around it."""
    from app.models.platform import FunnelPage, UserFunnel
    page = (FunnelPage.query.join(UserFunnel, FunnelPage.funnel_id == UserFunnel.id)
            .filter(FunnelPage.id == page_id, UserFunnel.user_id == current_user.id).first_or_404())
    funnel = page.funnel
    funnel_id = page.funnel_id

    # Clear anything pointing at this page (next/accept/decline links)
    # before it disappears, so we never leave a dangling reference.
    FunnelPage.query.filter_by(funnel_id=funnel_id, next_page_id=page.id).update({"next_page_id": None})
    FunnelPage.query.filter_by(funnel_id=funnel_id, branch_yes_id=page.id).update({"branch_yes_id": None})
    FunnelPage.query.filter_by(funnel_id=funnel_id, branch_no_id=page.id).update({"branch_no_id": None})

    was_entry = (funnel.entry_page_id == page.id)
    db.session.delete(page)
    db.session.flush()

    remaining = FunnelPage.query.filter_by(funnel_id=funnel_id).order_by(FunnelPage.order_index.asc()).all()
    for i, p in enumerate(remaining):
        p.order_index = i
    _relink_chain(funnel_id)
    if was_entry:
        funnel.entry_page_id = remaining[0].id if remaining else None
    funnel.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Page deleted.", "funnel": _serialize_funnel(funnel)})


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/pages/reorder", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_pages_reorder(funnel_id):
    """Reorder pages after a drag-and-drop move. Rebuilds the linear
    next_page_id chain to match; branch (accept/decline) links are
    untouched."""
    from app.models.platform import UserFunnel, FunnelPage
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    order = data.get("order") or []
    pages_by_id = {p.id: p for p in FunnelPage.query.filter_by(funnel_id=funnel_id).all()}
    if set(order) != set(pages_by_id.keys()):
        return jsonify({"error": "Reorder list doesn't match this funnel's pages."}), 400
    for idx, pid in enumerate(order):
        pages_by_id[pid].order_index = idx
    db.session.flush()
    ordered = _relink_chain(funnel_id)
    funnel.entry_page_id = ordered[0].id if ordered else None
    funnel.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"funnel": _serialize_funnel(funnel)})


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/canvas-positions", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_save_canvas_positions(funnel_id):
    """Persist Flow Builder node positions (drag layout only — the
    connections themselves are saved immediately by
    funnel_builder_page_connect below on every drag-to-connect; this
    just remembers where the boxes sit on screen). Purely cosmetic,
    never read by anything that affects actual funnel routing."""
    from app.models.platform import UserFunnel
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    positions = data.get("positions")
    if not isinstance(positions, dict):
        return jsonify({"error": "positions must be an object of page_id -> {x, y}."}), 400
    clean = {}
    for pid, pos in positions.items():
        try:
            clean[str(int(pid))] = {"x": float(pos.get("x", 0)), "y": float(pos.get("y", 0))}
        except (TypeError, ValueError, AttributeError):
            continue
    funnel.canvas_positions = clean
    funnel.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Layout saved."})


@dashboard_bp.route("/funnel-builder/pages/<int:page_id>/connect", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_page_connect(page_id):
    """Set an explicit connection from this page to another: the default
    'next' link, or (for upsell/downsell/quiz-style pages) the 'accept'
    or 'decline' branch. target_id=null clears that connection."""
    from app.models.platform import FunnelPage, UserFunnel
    page = (FunnelPage.query.join(UserFunnel, FunnelPage.funnel_id == UserFunnel.id)
            .filter(FunnelPage.id == page_id, UserFunnel.user_id == current_user.id).first_or_404())
    data = request.get_json(silent=True) or {}
    connection = data.get("connection")
    target_id = data.get("target_id")
    if connection not in ("next", "accept", "decline"):
        return jsonify({"error": "connection must be 'next', 'accept', or 'decline'."}), 400
    if target_id is not None:
        target = FunnelPage.query.filter_by(id=target_id, funnel_id=page.funnel_id).first()
        if not target:
            return jsonify({"error": "Target page not found in this funnel."}), 404
        if target.id == page.id:
            return jsonify({"error": "A page can't connect to itself."}), 400
    field = {"next": "next_page_id", "accept": "branch_yes_id", "decline": "branch_no_id"}[connection]
    setattr(page, field, target_id)
    page.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"page": page.to_dict(), "message": "Connection updated."})


@dashboard_bp.route("/funnel-builder/pages/<int:page_id>/generate", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_page_generate(page_id):
    """Generate this page's HTML with AI and save it immediately, so a
    generated page is never lost if the browser closes before a manual
    save."""
    from app.utils.website_builder import generate_website
    from app.models.platform import FunnelPage, UserFunnel
    page = (FunnelPage.query.join(UserFunnel, FunnelPage.funnel_id == UserFunnel.id)
            .filter(FunnelPage.id == page_id, UserFunnel.user_id == current_user.id).first_or_404())
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Please describe your funnel page."}), 400

    style = FUNNEL_AI_TYPE_PROMPTS.get(page.page_type, FUNNEL_AI_TYPE_PROMPTS["custom"])
    enhanced = f"""Create a professional {style} page:
{prompt}

REQUIREMENTS:
- Single-page, self-contained HTML with embedded CSS and JS
- Mobile responsive
- High-converting design with clear visual hierarchy
- Professional typography and spacing
- Animations and micro-interactions
- Images from https://picsum.photos/ or https://image.pollinations.ai/prompt/
- Modern gradient backgrounds and glassmorphic elements"""

    html, error, source = generate_website(enhanced)
    if error:
        return jsonify({"error": error}), 500
    page.html_content = html
    page.builder_mode = "ai"
    page.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"html": html, "source": source, "page": page.to_dict()})


@dashboard_bp.route("/funnel-builder/pages/<int:page_id>/settings", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_page_settings(page_id):
    """Save a page's Page Settings: SEO title/description, password
    protection, and custom header/footer scripts. Stored in the
    already-existing FunnelPage.settings JSON column — no migration
    needed, this just starts writing to a column that's existed since
    the Foundation migration but was reserved/unused until now."""
    from app.models.platform import FunnelPage, UserFunnel
    page = (FunnelPage.query.join(UserFunnel, FunnelPage.funnel_id == UserFunnel.id)
            .filter(FunnelPage.id == page_id, UserFunnel.user_id == current_user.id).first_or_404())
    data = request.get_json(silent=True) or {}
    settings = dict(page.settings or {})

    if "seo" in data:
        seo = data["seo"] or {}
        settings["seo"] = {
            "title": (seo.get("title") or "").strip()[:200],
            "description": (seo.get("description") or "").strip()[:400],
        }
    if "password" in data:
        pw = (data.get("password") or "").strip()
        settings["password"] = pw or None
    if "custom_scripts" in data:
        scripts = data["custom_scripts"] or {}
        settings["custom_scripts"] = {
            "header": (scripts.get("header") or "")[:5000],
            "footer": (scripts.get("footer") or "")[:5000],
        }

    page.settings = settings
    page.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"page": page.to_dict(), "message": "Page settings saved."})


@dashboard_bp.route("/funnel-builder/pages/<int:page_id>/checkout-config", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_page_checkout_config(page_id):
    """Save the Checkout page type's product/price config. Payment
    processing itself reuses the same app.utils.payments gateway layer
    Payment Links already uses in production — this only stores what
    the buyer sees and what gets charged."""
    from app.models.platform import FunnelPage, UserFunnel
    from decimal import Decimal, InvalidOperation
    page = (FunnelPage.query.join(UserFunnel, FunnelPage.funnel_id == UserFunnel.id)
            .filter(FunnelPage.id == page_id, UserFunnel.user_id == current_user.id).first_or_404())
    data = request.get_json(silent=True) or {}
    try:
        price = str(Decimal(str(data.get("price") or "0")))
    except (InvalidOperation, ValueError):
        return jsonify({"error": "Price must be a number."}), 400

    settings = dict(page.settings or {})
    delivery_type = data.get("delivery_type") or "redirect"
    if delivery_type not in ("redirect", "digital"):
        delivery_type = "redirect"
    settings["checkout"] = {
        "product_name": (data.get("product_name") or page.title or "Product").strip()[:200],
        "price": price,
        "currency": (data.get("currency") or "USD").strip()[:8].upper(),
        "description": (data.get("description") or "").strip()[:1000],
        # Delivery: "redirect" (default, existing behavior) sends the buyer
        # to the page's Accept/Next branch same as before. "digital" skips
        # branching entirely and shows a download link right on the
        # confirmation screen instead — for "they pay, they get a file,
        # nothing else happens" products (ebooks, PDFs, templates).
        "delivery_type": delivery_type,
        "digital_file_url": (data.get("digital_file_url") or "").strip()[:1000],
        "digital_file_label": (data.get("digital_file_label") or "Download your file").strip()[:200],
    }
    page.settings = settings
    if page.page_type != "checkout":
        page.page_type = "checkout"
    page.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"page": page.to_dict(), "message": "Checkout settings saved."})


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/settings", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_settings(funnel_id):
    """Save funnel-level settings: custom domain reference, plus (new)
    order notification email and buyer receipt customization — the
    "personal settings that are the funnel builder's own, not shared
    with Payment Links" Jackson asked for. These feed
    _send_funnel_order_emails() above. Actual DNS/SSL wiring for the
    domain is an infra step outside the app; this stores what the
    domain SHOULD be so it's not lost, and is surfaced back to the user
    in the Publish panel."""
    from app.models.platform import UserFunnel
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    settings = dict(funnel.settings or {})
    if "custom_domain" in data:
        settings["custom_domain"] = (data.get("custom_domain") or "").strip()[:256] or None
    if "emails" in data and isinstance(data["emails"], dict):
        e = data["emails"]
        settings["emails"] = {
            "notification_email": (e.get("notification_email") or "").strip()[:256],
            "buyer_subject": (e.get("buyer_subject") or "").strip()[:200],
            "buyer_body": (e.get("buyer_body") or "").strip()[:5000],
            # What the buyer sees as the sender, and where their "Reply"
            # actually goes — the SMTP relay itself is still the shared
            # platform account (see _send_via_smtp), but these two make
            # the email look and behave like it came from THIS funnel's
            # owner, not the platform.
            "sender_name": (e.get("sender_name") or "").strip()[:200],
            "reply_to": (e.get("reply_to") or "").strip()[:256],
        }
    funnel.settings = settings
    funnel.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"funnel": _serialize_funnel(funnel), "message": "Funnel settings saved."})


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/connect-smtp", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_connect_smtp(funnel_id):
    """Real per-seller SMTP — the thing flagged as 'not built yet' in
    earlier batches, now built the same way WhatsApp's Twilio connection
    already works in this codebase: test the credentials live against
    the real server before ever saving them, encrypt at rest, never
    echo the password back out."""
    from app.models.platform import UserFunnel
    from app.utils.email import test_smtp_credentials
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    host = data.get("host") or ""
    port = data.get("port") or 587
    username = data.get("username") or ""
    password = data.get("password") or ""
    from_email = data.get("from_email") or username
    use_tls = data.get("use_tls", True)

    ok, message = test_smtp_credentials(host, port, username, password, use_tls)
    if not ok:
        return jsonify({"error": message}), 400

    funnel.set_smtp_credentials(host, port, username, password, from_email, use_tls)
    funnel.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "SMTP connected — receipts will now send from your own account.", "funnel": _serialize_funnel(funnel)})


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/test-smtp", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_test_smtp(funnel_id):
    """Re-check an already-connected SMTP account without re-entering the
    password (mirrors test-whatsapp's 'confirm it's still good' use)."""
    from app.models.platform import UserFunnel
    from app.utils.email import test_smtp_credentials
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    creds = funnel.get_smtp_credentials()
    if not creds:
        return jsonify({"error": "No SMTP account connected yet."}), 400
    ok, message = test_smtp_credentials(creds.get("host"), creds.get("port"), creds.get("username"), creds.get("password"), creds.get("use_tls", True))
    return jsonify({"ok": ok, "message": message}), (200 if ok else 400)


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/disconnect-smtp", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_disconnect_smtp(funnel_id):
    from app.models.platform import UserFunnel
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    funnel.smtp_credentials_encrypted = None
    funnel.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "SMTP disconnected — receipts will use the platform's shared account again.", "funnel": _serialize_funnel(funnel)})


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/unpublish", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_unpublish(funnel_id):
    """Take a funnel offline without deleting it or losing its subdomain."""
    from app.models.platform import UserFunnel
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    funnel.published = False
    funnel.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Funnel unpublished.", "funnel": _serialize_funnel(funnel)})


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/analytics")
@require_premium("funnel-builder")
def funnel_builder_analytics(funnel_id):
    """A real, dedicated Analytics page for one funnel — revenue, orders,
    traffic sources, devices, browsers, and per-page performance. This
    used to be squeezed into the Settings modal as a bare summary; it's
    now its own page with real depth, derived from actual order rows and
    the real pageview capture in _record_funnel_pageview()."""
    from app.models.platform import UserFunnel, FunnelOrder, FunnelLead
    from decimal import Decimal
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    pages = funnel.ordered_pages()
    orders = FunnelOrder.query.filter_by(funnel_id=funnel.id).order_by(FunnelOrder.created_at.desc()).all()
    paid_orders = [o for o in orders if o.status == "paid"]
    revenue = sum(Decimal(str(o.amount or 0)) for o in paid_orders)
    settings = funnel.settings or {}
    analytics = settings.get("analytics") or {}
    unique_visitors = analytics.get("unique_visitors") or 0
    conv_rate = round((len(paid_orders) / funnel.view_count * 100), 2) if funnel.view_count else 0

    page_rows = []
    for p in pages:
        a = (p.settings or {}).get("analytics") or {}
        page_rows.append({"title": p.title, "views": a.get("views", 0), "conversions": a.get("conversions", 0)})
    top_pages = sorted(page_rows, key=lambda r: r["views"], reverse=True)

    def _sorted_breakdown(d):
        items = list((d or {}).items())
        items.sort(key=lambda kv: kv[1], reverse=True)
        total = sum(v for _, v in items) or 1
        return [{"label": k, "count": v, "pct": round(v / total * 100, 1)} for k, v in items]

    return render_template(
        "dashboard/funnel_analytics.html", funnel=funnel,
        revenue=revenue, orders=orders, paid_orders_count=len(paid_orders),
        failed_orders_count=len([o for o in orders if o.status == "failed"]),
        average_order_value=(revenue / len(paid_orders)) if paid_orders else Decimal("0"),
        unique_visitors=unique_visitors, conv_rate=conv_rate,
        top_pages=top_pages,
        traffic_sources=_sorted_breakdown(analytics.get("traffic_sources")),
        devices=_sorted_breakdown(analytics.get("devices")),
        browsers=_sorted_breakdown(analytics.get("browsers")),
        leads=FunnelLead.query.filter_by(funnel_id=funnel.id).order_by(FunnelLead.created_at.desc()).limit(200).all(),
        lead_count=FunnelLead.query.filter_by(funnel_id=funnel.id).count(),
    )


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/leads.csv")
@require_premium("funnel-builder")
def funnel_builder_leads_csv(funnel_id):
    """Export every captured lead for this funnel as a real CSV — this
    is what actually closes the loop on "how do I collect information
    from the sales funnel": Form blocks could already save submissions
    (FunnelLead), but there was no way to ever see or use them anywhere
    in the UI. Column set is derived from whatever fields each lead
    actually has (forms can differ per page), so this works whether a
    funnel has one lead-capture page or several with different fields."""
    from app.models.platform import UserFunnel, FunnelLead
    import csv, io
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    leads = FunnelLead.query.filter_by(funnel_id=funnel.id).order_by(FunnelLead.created_at.asc()).all()

    field_keys = []
    for lead in leads:
        for k in (lead.data or {}).keys():
            if k not in field_keys:
                field_keys.append(k)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Page"] + field_keys)
    page_titles = {p.id: p.title for p in funnel.ordered_pages()}
    for lead in leads:
        row = [lead.created_at.strftime("%Y-%m-%d %H:%M") if lead.created_at else "", page_titles.get(lead.page_id, "")]
        row += [(lead.data or {}).get(k, "") for k in field_keys]
        writer.writerow(row)

    resp = make_response(buf.getvalue())
    resp.headers["Content-Type"] = "text/csv"
    resp.headers["Content-Disposition"] = f"attachment; filename={funnel.slug or 'funnel'}-leads.csv"
    return resp


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/orders")
@require_premium("funnel-builder")
def funnel_builder_orders(funnel_id):
    """Order history for a funnel's Checkout page(s)."""
    from app.models.platform import UserFunnel, FunnelOrder
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    orders = FunnelOrder.query.filter_by(funnel_id=funnel.id).order_by(FunnelOrder.created_at.desc()).limit(200).all()
    return jsonify({"orders": [{
        "id": o.id, "customer_name": o.customer_name, "customer_email": o.customer_email,
        "product_name": o.product_name, "amount": str(o.amount), "currency": o.currency,
        "gateway": o.gateway, "status": o.status,
        "created_at": o.created_at.strftime("%b %d, %Y %H:%M") if o.created_at else "",
    } for o in orders]})


# ══════════════════════════════════════════════════════════════════════
#  INVOICE GENERATOR
# ══════════════════════════════════════════════════════════════════════

# Real ISO currency list (code -> symbol/label). The old dropdown only
# had 3 hardcoded options (USD/EUR/GBP) and stored the SYMBOL itself
# ("$") as the invoice's currency value instead of a proper ISO code —
# that value flows straight into UserPaymentLink.currency and then into
# the gateway calls, so a "$" was being saved where "USD" belongs.
INVOICE_CURRENCIES = [
    ("NGN", "₦", "Nigerian Naira"), ("USD", "$", "US Dollar"), ("EUR", "€", "Euro"),
    ("GBP", "£", "British Pound"), ("CAD", "$", "Canadian Dollar"), ("AUD", "$", "Australian Dollar"),
    ("ZAR", "R", "South African Rand"), ("KES", "KSh", "Kenyan Shilling"), ("GHS", "GH₵", "Ghanaian Cedi"),
    ("XOF", "CFA", "West African CFA Franc"), ("EGP", "E£", "Egyptian Pound"), ("INR", "₹", "Indian Rupee"),
    ("AED", "د.إ", "UAE Dirham"), ("JPY", "¥", "Japanese Yen"), ("CNY", "¥", "Chinese Yuan"),
    ("CHF", "CHF", "Swiss Franc"), ("SEK", "kr", "Swedish Krona"),
]


@dashboard_bp.route("/invoice-generator")
@require_premium("invoice-generator")
def invoice_generator():
    """Invoice Generator workspace."""
    from app.models.platform import UserInvoice, UserPaymentLink
    invoices = UserInvoice.query.filter_by(
        user_id=current_user.id
    ).order_by(UserInvoice.created_at.desc()).all()
    # Full data for the JS "Edit" flow — editInvoice() used to be a stub
    # that just showed an alert and did nothing; it now looks the
    # invoice up here instead of needing a separate fetch endpoint.
    link_slugs = {}
    link_ids = [i.payment_link_id for i in invoices if i.payment_link_id]
    if link_ids:
        for link in UserPaymentLink.query.filter(UserPaymentLink.id.in_(link_ids)).all():
            link_slugs[link.id] = link.slug
    invoices_json = [{
        "id": i.id, "invoice_number": i.invoice_number,
        "client_name": i.client_name, "client_email": i.client_email,
        "client_address": i.client_address,
        "business_name": i.business_name, "business_email": i.business_email,
        "business_address": i.business_address, "logo_url": i.logo_url,
        "items": i.items or [], "tax_rate": i.tax_rate or 0,
        "discount": float(i.discount or 0), "currency": i.currency,
        "due_date": i.due_date.isoformat() if i.due_date else "",
        "notes": i.notes, "terms": i.terms,
        "pay_url": url_for("dashboard.pay_link_view", slug=link_slugs[i.payment_link_id], _external=True) if i.payment_link_id in link_slugs else None,
        "status": i.status, "total": float(i.total or 0),
    } for i in invoices]
    return render_template("dashboard/invoice_generator.html", invoices=invoices, invoices_json=invoices_json,
                            currencies=INVOICE_CURRENCIES)


@dashboard_bp.route("/invoice-generator/create", methods=["POST"])
@require_premium("invoice-generator")
def invoice_generator_create():
    """Create or update a user invoice."""
    from app.models.platform import UserInvoice
    from decimal import Decimal
    data = request.get_json(silent=True) or {}
    invoice_id = data.get("id")

    items = data.get("items", [])
    # Line items come from the form as {description, quantity, rate} — the
    # backend used to look for `amount` directly, which the form never
    # sends, so every invoice silently saved with a $0.00 subtotal/total
    # while the downloaded PDF (which recomputes qty*rate independently)
    # showed different numbers. Compute the same way here.
    def _item_amount(item):
        if item.get("amount") not in (None, ""):
            return Decimal(str(item.get("amount", 0)))
        qty = Decimal(str(item.get("quantity", item.get("qty", 0)) or 0))
        rate = Decimal(str(item.get("rate", item.get("price", 0)) or 0))
        return qty * rate
    subtotal = sum(_item_amount(item) for item in items)
    tax_rate = float(data.get("tax_rate", 0))
    tax_amount = subtotal * Decimal(str(tax_rate / 100))
    discount = Decimal(str(data.get("discount", 0)))
    total = subtotal + tax_amount - discount

    if invoice_id:
        inv = UserInvoice.query.filter_by(id=invoice_id, user_id=current_user.id).first()
        if not inv:
            return jsonify({"error": "Invoice not found."}), 404
    else:
        # Generate invoice number
        count = UserInvoice.query.filter_by(user_id=current_user.id).count()
        inv_num = f"INV-{current_user.id:04d}-{count + 1:04d}"
        inv = UserInvoice(user_id=current_user.id, invoice_number=inv_num)
        db.session.add(inv)

    inv.client_name = data.get("client_name", "")
    inv.client_email = data.get("client_email", "")
    inv.client_address = data.get("client_address", "")
    inv.client_phone = data.get("client_phone", "")
    inv.items = items
    inv.subtotal = subtotal
    inv.tax_rate = tax_rate
    inv.tax_amount = tax_amount
    inv.discount = discount
    inv.total = total
    inv.currency = data.get("currency", "USD")
    inv.status = data.get("status", "draft")
    inv.notes = data.get("notes", "")
    inv.terms = data.get("terms", "")
    inv.logo_url = data.get("logo_url", "")
    inv.business_name = data.get("business_name", "")
    inv.business_email = data.get("business_email", "")
    inv.business_address = data.get("business_address", "")
    inv.business_phone = data.get("business_phone", "")
    if data.get("due_date"):
        try:
            inv.due_date = datetime.strptime(data["due_date"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass
    inv.updated_at = datetime.utcnow()

    # Give every invoice a real "Pay Invoice" link by reusing the Payment
    # Links infrastructure — same per-user gateway checkout, same order
    # tracking, same thank-you page — instead of building a second,
    # separate payment system just for invoices.
    from app.models.platform import UserPaymentLink
    if total > 0:
        if inv.payment_link_id:
            link = UserPaymentLink.query.get(inv.payment_link_id)
        else:
            link = None
        if not link:
            link = UserPaymentLink(user_id=current_user.id, active=True)
            db.session.add(link)
        link.title = f"Invoice {inv.invoice_number}"
        link.amount = total
        link.currency = inv.currency
        link.description = f"Payment for invoice {inv.invoice_number}" + (f" — {inv.client_name}" if inv.client_name else "")
        if not link.slug:
            import re as _re, secrets as _secrets
            base = _re.sub(r"[^a-z0-9]+", "-", inv.invoice_number.lower()).strip("-")
            link.slug = f"{base}-{_secrets.token_hex(3)}"
        settings = dict(link.settings or {})
        settings["seller_bio"] = inv.business_name or None
        settings["collect_payer_info"] = False  # we already have the client's details from the invoice
        link.settings = settings
        db.session.flush()  # get link.id now that all NOT NULL fields are set
        inv.payment_link_id = link.id

    db.session.commit()

    pay_url = url_for("dashboard.pay_link_view", slug=link.slug) if total > 0 and link else None
    return jsonify({"id": inv.id, "invoice_number": inv.invoice_number, "message": "Invoice saved.", "pay_url": pay_url})


@dashboard_bp.route("/invoice-generator/upload-logo", methods=["POST"])
@require_premium("invoice-generator")
def invoice_generator_upload_logo():
    """Upload a business/company logo for use as the invoice header.
    The editor previously had no way to attach a logo at all — the PDF
    generator already rendered `logo_url` in the header, but nothing in
    the UI ever set it."""
    from app.utils.media_storage import save_upload
    file = request.files.get("logo")
    if not file or not file.filename:
        return jsonify({"error": "No file selected."}), 400
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in {"png", "jpg", "jpeg", "gif", "webp", "svg"}:
        return jsonify({"error": "Please upload an image file (PNG, JPG, WEBP, SVG)."}), 400
    try:
        url, filename, size = save_upload(file, "invoice-logos", current_app)
    except Exception as e:
        return jsonify({"error": f"Upload failed: {e}"}), 500
    return jsonify({"url": url})


@dashboard_bp.route("/invoice-generator/<int:invoice_id>/ensure-pay-link", methods=["POST"])
@require_premium("invoice-generator")
def invoice_generator_ensure_pay_link(invoice_id):
    """Make sure a saved invoice with a real total has a working pay
    link, and return it. Invoices saved before the auto-link logic
    existed (or saved while the total was still $0) can end up with
    payment_link_id = None even though they now have a real total —
    this repairs that on demand instead of just telling the user
    'no payable amount' with no way to fix it."""
    from app.models.platform import UserInvoice, UserPaymentLink
    inv = UserInvoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    if not inv.total or inv.total <= 0:
        return jsonify({"error": "This invoice has no items with an amount yet — add items and save it first."}), 400

    link = UserPaymentLink.query.get(inv.payment_link_id) if inv.payment_link_id else None
    if not link:
        import re as _re, secrets as _secrets
        link = UserPaymentLink(user_id=current_user.id, active=True)
        db.session.add(link)
        base = _re.sub(r"[^a-z0-9]+", "-", inv.invoice_number.lower()).strip("-")
        link.slug = f"{base}-{_secrets.token_hex(3)}"
        settings = dict(link.settings or {})
        settings["seller_bio"] = inv.business_name or None
        settings["collect_payer_info"] = False
        link.settings = settings

    link.title = f"Invoice {inv.invoice_number}"
    link.amount = inv.total
    link.currency = inv.currency
    link.description = f"Payment for invoice {inv.invoice_number}" + (f" — {inv.client_name}" if inv.client_name else "")
    db.session.flush()
    inv.payment_link_id = link.id
    db.session.commit()

    pay_url = url_for("dashboard.pay_link_view", slug=link.slug, _external=True)
    return jsonify({"pay_url": pay_url})


@dashboard_bp.route("/invoice-generator/<int:invoice_id>/pdf")
@require_premium("invoice-generator")
def invoice_generator_pdf(invoice_id):
    """Generate and download invoice PDF."""
    from app.models.platform import UserInvoice
    from app.utils.user_invoice_pdf import generate_user_invoice_pdf
    from flask import send_file
    import io

    inv = UserInvoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    pdf_bytes = generate_user_invoice_pdf(inv)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{inv.invoice_number}.pdf",
    )


@dashboard_bp.route("/invoice-generator/<int:invoice_id>/send", methods=["POST"])
@require_premium("invoice-generator")
def invoice_generator_send(invoice_id):
    """Send invoice to client via email."""
    from app.models.platform import UserInvoice
    from app.utils.email import send_email
    inv = UserInvoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    if not inv.client_email:
        return jsonify({"error": "No client email set."}), 400

    biz_name = inv.business_name or current_user.name or "Your provider"
    send_email(
        to=inv.client_email,
        subject=f"Invoice {inv.invoice_number} from {biz_name}",
        body_html=f"""<p>Hi {inv.client_name or 'there'},</p>
        <p>Please find your invoice <strong>{inv.invoice_number}</strong> for <strong>{inv.currency} {inv.total}</strong>.</p>
        <p>Due date: {inv.due_date or 'Upon receipt'}</p>
        <p>{inv.notes or ''}</p>
        <p>Thanks,<br>{biz_name}</p>""",
    )
    inv.status = "sent"
    inv.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": "Invoice sent to client."})


@dashboard_bp.route("/invoice-generator/<int:invoice_id>/delete", methods=["POST"])
@require_premium("invoice-generator")
def invoice_generator_delete(invoice_id):
    """Delete a user invoice."""
    from app.models.platform import UserInvoice
    inv = UserInvoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    db.session.delete(inv)
    db.session.commit()
    return jsonify({"message": "Invoice deleted."})


# ══════════════════════════════════════════════════════════════════════
#  PAYMENT LINK GENERATOR
# ══════════════════════════════════════════════════════════════════════

@dashboard_bp.route("/payment-links")
@require_premium("payment-link-generator")
def payment_links():
    """Payment Link Generator workspace."""
    from app.models.platform import UserPaymentLink, UserPaymentGateway
    show_archived = request.args.get("archived") == "1"
    all_links = UserPaymentLink.query.filter_by(
        user_id=current_user.id
    ).order_by(UserPaymentLink.created_at.desc()).all()
    archived_count = sum(1 for l in all_links if (l.settings or {}).get("archived"))
    links = [l for l in all_links if bool((l.settings or {}).get("archived")) == show_archived]
    connected_gateways = [g.gateway for g in UserPaymentGateway.query.filter_by(user_id=current_user.id, active=True).all()]
    return render_template("dashboard/payment_links.html", links=links, show_archived=show_archived,
                            archived_count=archived_count, connected_gateways=connected_gateways)


@dashboard_bp.route("/payment-links/create", methods=["POST"])
@require_premium("payment-link-generator")
def payment_links_create():
    """Create or update a payment link."""
    from app.models.platform import UserPaymentLink
    from decimal import Decimal
    import re, secrets
    data = request.get_json(silent=True) or {}
    link_id = data.get("id")

    if link_id:
        link = UserPaymentLink.query.filter_by(id=link_id, user_id=current_user.id).first()
        if not link:
            return jsonify({"error": "Payment link not found."}), 404
    else:
        title = data.get("title", "Payment").strip()
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "pay"
        slug = f"u-{slug}-{secrets.token_hex(3)}"
        link = UserPaymentLink(
            user_id=current_user.id,
            title=title,
            slug=slug,
            amount=Decimal(str(data.get("amount", 0))),
            currency=data.get("currency", "USD"),
        )
        db.session.add(link)

    link.title = data.get("title", link.title)
    link.amount = Decimal(str(data.get("amount", link.amount)))
    link.currency = data.get("currency", link.currency)
    link.description = data.get("description", "")
    link.active = data.get("active", True)
    # The create form sends redirect_url as a flat field (not nested under
    # "settings"), so it was silently discarded before — folded into
    # settings here instead, alongside anything already stored there.
    settings = dict(link.settings or {})
    if "redirect_url" in data:
        settings["redirect_url"] = data.get("redirect_url", "")
    if "settings" in data and isinstance(data["settings"], dict):
        settings.update(data["settings"])
    link.settings = settings
    link.updated_at = datetime.utcnow()
    db.session.commit()

    pay_url = url_for("dashboard.pay_link_view", slug=link.slug, _external=True)
    return jsonify({
        "id": link.id,
        "slug": link.slug,
        "url": pay_url,
        "message": "Payment link saved.",
    })


@dashboard_bp.route("/payment-links/<int:link_id>/delete", methods=["POST"])
@require_premium("payment-link-generator")
def payment_links_delete(link_id):
    """Delete a payment link."""
    from app.models.platform import UserPaymentLink
    link = UserPaymentLink.query.filter_by(id=link_id, user_id=current_user.id).first_or_404()
    db.session.delete(link)
    db.session.commit()
    return jsonify({"message": "Payment link deleted."})


@dashboard_bp.route("/payment-links/<int:link_id>/duplicate", methods=["POST"])
@require_premium("payment-link-generator")
def payment_links_duplicate(link_id):
    """Duplicate a payment link — new slug, same settings, starts at
    zero views/payments (its own real history, not the original's)."""
    from app.models.platform import UserPaymentLink
    import re, secrets
    original = UserPaymentLink.query.filter_by(id=link_id, user_id=current_user.id).first_or_404()
    base_slug = re.sub(r"[^a-z0-9]+", "-", (original.title + "-copy").lower()).strip("-") or "pay"
    copy = UserPaymentLink(
        user_id=current_user.id,
        title=f"{original.title} (Copy)",
        slug=f"u-{base_slug}-{secrets.token_hex(3)}",
        amount=original.amount,
        currency=original.currency,
        description=original.description,
        active=True,
        settings=dict(original.settings or {}),
    )
    db.session.add(copy)
    db.session.commit()
    return jsonify({"id": copy.id, "message": "Payment link duplicated."})


@dashboard_bp.route("/payment-links/<int:link_id>/archive", methods=["POST"])
@require_premium("payment-link-generator")
def payment_links_archive(link_id):
    """Archive (hide from the public + main list) without deleting —
    keeps all order/customer history intact, unlike Delete."""
    from app.models.platform import UserPaymentLink
    link = UserPaymentLink.query.filter_by(id=link_id, user_id=current_user.id).first_or_404()
    settings = dict(link.settings or {})
    settings["archived"] = True
    link.settings = settings
    db.session.commit()
    return jsonify({"message": "Payment link archived."})


@dashboard_bp.route("/payment-links/<int:link_id>/unarchive", methods=["POST"])
@require_premium("payment-link-generator")
def payment_links_unarchive(link_id):
    from app.models.platform import UserPaymentLink
    link = UserPaymentLink.query.filter_by(id=link_id, user_id=current_user.id).first_or_404()
    settings = dict(link.settings or {})
    settings.pop("archived", None)
    link.settings = settings
    db.session.commit()
    return jsonify({"message": "Payment link restored."})


@dashboard_bp.route("/payment-links/<int:link_id>/orders")
@require_premium("payment-link-generator")
def payment_links_orders(link_id):
    """Real per-transaction orders for one link — Order Management."""
    from app.models.platform import UserPaymentLink, UserPaymentLinkOrder
    link = UserPaymentLink.query.filter_by(id=link_id, user_id=current_user.id).first_or_404()
    orders = UserPaymentLinkOrder.query.filter_by(payment_link_id=link.id).order_by(UserPaymentLinkOrder.created_at.desc()).limit(200).all()
    return jsonify({"orders": [o.to_dict() for o in orders]})


@dashboard_bp.route("/payment-links/customers")
@require_premium("payment-link-generator")
def payment_links_customers():
    """Real Customer Management — every distinct buyer across ALL of this
    user's payment links, with their totals, derived from actual paid
    orders (not a separate hand-maintained customer list)."""
    from app.models.platform import UserPaymentLinkOrder
    from sqlalchemy import func
    rows = (
        db.session.query(
            UserPaymentLinkOrder.buyer_email,
            func.max(UserPaymentLinkOrder.buyer_name).label("buyer_name"),
            func.count(UserPaymentLinkOrder.id).label("orders"),
            func.sum(UserPaymentLinkOrder.amount).label("total_spent"),
            func.max(UserPaymentLinkOrder.created_at).label("last_order"),
        )
        .filter(UserPaymentLinkOrder.user_id == current_user.id, UserPaymentLinkOrder.status == "paid")
        .group_by(UserPaymentLinkOrder.buyer_email)
        .order_by(func.max(UserPaymentLinkOrder.created_at).desc())
        .limit(500)
        .all()
    )
    return jsonify({"customers": [{
        "email": r.buyer_email, "name": r.buyer_name, "orders": r.orders,
        "total_spent": float(r.total_spent or 0),
        "last_order": r.last_order.strftime("%Y-%m-%d %H:%M") if r.last_order else None,
    } for r in rows]})


@dashboard_bp.route("/payment-links/<int:link_id>/analytics")
@require_premium("payment-link-generator")
def payment_links_analytics(link_id):
    """Revenue / conversion analytics for one link, derived from real
    order rows rather than only the two aggregate counters on the link."""
    from app.models.platform import UserPaymentLink, UserPaymentLinkOrder
    link = UserPaymentLink.query.filter_by(id=link_id, user_id=current_user.id).first_or_404()
    orders = UserPaymentLinkOrder.query.filter_by(payment_link_id=link.id).all()
    paid = [o for o in orders if o.status == "paid"]
    failed = [o for o in orders if o.status == "failed"]
    revenue = sum(float(o.amount or 0) for o in paid)
    conv_rate = (len(paid) / link.view_count * 100) if link.view_count else 0
    return jsonify({
        "views": link.view_count or 0,
        "orders": len(paid),
        "failed_orders": len(failed),
        "revenue": revenue,
        "average_order_value": (revenue / len(paid)) if paid else 0,
        "conversion_rate": round(conv_rate, 2),
    })


@dashboard_bp.route("/payment-links/<int:link_id>/qr.png")
@require_premium("payment-link-generator")
def payment_links_qr(link_id):
    """QR code for a payment link's public checkout URL — scan to open
    the exact same page a buyer would land on."""
    from app.models.platform import UserPaymentLink
    import qrcode, io
    from flask import send_file
    link = UserPaymentLink.query.filter_by(id=link_id, user_id=current_user.id).first_or_404()
    pay_url = url_for("dashboard.pay_link_view", slug=link.slug, _external=True)
    img = qrcode.make(pay_url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", as_attachment=False, download_name=f"{link.slug}-qr.png")


@dashboard_bp.route("/payment-links/<int:link_id>/analytics-page")
@require_premium("payment-link-generator")
def payment_links_analytics_page(link_id):
    """A real, dedicated Analytics page for one payment link (not just a
    JSON endpoint) — views, clicks-to-checkout, conversion rate, revenue,
    a real 14-day revenue trend chart, gateway breakdown, and the actual
    order list. All derived from real UserPaymentLinkOrder rows."""
    from app.models.platform import UserPaymentLink, UserPaymentLinkOrder
    from collections import defaultdict, OrderedDict
    from datetime import timedelta
    link = UserPaymentLink.query.filter_by(id=link_id, user_id=current_user.id).first_or_404()
    orders = UserPaymentLinkOrder.query.filter_by(payment_link_id=link.id).order_by(UserPaymentLinkOrder.created_at.desc()).all()
    paid = [o for o in orders if o.status == "paid"]
    failed = [o for o in orders if o.status == "failed"]
    pending = [o for o in orders if o.status == "pending"]
    revenue = sum(float(o.amount or 0) for o in paid)
    conv_rate = round((len(paid) / link.view_count * 100), 2) if link.view_count else 0
    checkout_rate = round((len(orders) / link.view_count * 100), 2) if link.view_count else 0

    # Real 14-day revenue trend from actual paid_at timestamps
    today = datetime.utcnow().date()
    days = OrderedDict((today - timedelta(days=i), 0.0) for i in range(13, -1, -1))
    for o in paid:
        d = (o.paid_at or o.created_at)
        if d and d.date() in days:
            days[d.date()] += float(o.amount or 0)
    max_day = max(days.values()) or 1
    trend = [{"label": d.strftime("%b %d"), "value": v, "pct": round(v / max_day * 100, 1)} for d, v in days.items()]

    gateway_counts = defaultdict(int)
    for o in paid:
        gateway_counts[o.gateway or "unknown"] += 1
    total_gw = sum(gateway_counts.values()) or 1
    gateway_breakdown = [{"label": k, "count": v, "pct": round(v / total_gw * 100, 1)} for k, v in sorted(gateway_counts.items(), key=lambda x: -x[1])]

    return render_template(
        "dashboard/payment_link_analytics.html", link=link,
        revenue=revenue, paid_count=len(paid), failed_count=len(failed), pending_count=len(pending),
        conv_rate=conv_rate, checkout_rate=checkout_rate,
        average_order_value=(revenue / len(paid)) if paid else 0,
        trend=trend, gateway_breakdown=gateway_breakdown, orders=orders,
    )


# ══════════════════════════════════════════════════════════════════════
#  VOICE STUDIO
# ══════════════════════════════════════════════════════════════════════
@dashboard_bp.route("/settings")
def settings():
    """User account settings — profile, security, preferences. Billing
    now lives on its own page (see dashboard.billing) instead of being a
    section here; this route still computes unlocked_count for the small
    summary card that links there."""
    from app.dashboard.premium import get_user_products
    products = get_user_products(current_user) if current_user.is_authenticated else []
    unlocked_count = sum(1 for p in products if p["unlocked"])
    return render_template("dashboard/settings_user.html", unlocked_count=unlocked_count)


@dashboard_bp.route("/settings/preferences", methods=["POST"])
def update_preferences():
    data = request.get_json(silent=True) or {}
    if "email_notifications" in data:
        current_user.email_notifications = bool(data["email_notifications"])
    if "timezone" in data:
        current_user.timezone = (data.get("timezone") or "UTC").strip()
    db.session.commit()
    return jsonify({"success": True})


@dashboard_bp.route("/billing")
def billing():
    """Billing — AI credits summary, credit purchase history, and every
    premium product/subscription the user has bought (including the
    Sales Funnel Builder plan), with real activation/expiration/renewal
    status. Separate page from Settings — the old sidebar link just
    pointed at Settings with a #billing anchor to a 3-stat summary,
    which is why it looked like 'the same page'."""
    from app.models.platform import CreditPurchase, CreditTransaction
    from app.models.commerce import Order, Product
    from app.dashboard.premium import get_user_products, PREMIUM_PRODUCTS
    from app.utils.credits import get_credit_status
    from app.utils.payments import currency_symbol

    credit_status = get_credit_status(current_user.id)
    credit_purchases = CreditPurchase.query.filter_by(user_id=current_user.id).order_by(CreditPurchase.created_at.desc()).limit(10).all()

    # Every product the user has EVER unlocked (active or expired) — not
    # just currently-active ones, so an expired subscription still shows
    # up with a Renew action instead of silently disappearing.
    from app.models.platform import UserProductAccess
    access_rows = {a.product_slug: a for a in UserProductAccess.query.filter_by(user_id=current_user.id).all()}
    products = get_user_products(current_user)
    subscriptions = []
    for p in products:
        access = access_rows.get(p["slug"])
        if not access and not p["unlocked"]:
            continue  # never purchased — not part of billing history
        mp_product = Product.query.filter_by(slug=p["slug"], status="active").first()
        expired = bool(access and access.expires_at and access.expires_at < datetime.utcnow())
        subscriptions.append({
            "name": p["name"], "slug": p["slug"], "icon": p["icon"], "color": p["color"],
            "billing_period": mp_product.billing_period if mp_product else "one_time",
            "price": float(mp_product.effective_price) if mp_product else None,
            "currency": mp_product.currency if mp_product else None,
            "activated_at": access.activated_at if access else None,
            "expires_at": access.expires_at if access else None,
            "active": bool(access and access.active and not expired),
            "expired": expired,
        })

    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(20).all()

    return render_template(
        "dashboard/billing.html",
        credit_status=credit_status, credit_purchases=credit_purchases,
        subscriptions=subscriptions, orders=orders, currency_symbol=currency_symbol(),
    )


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC SERVING — Published websites & funnels
# ══════════════════════════════════════════════════════════════════════

@dashboard_bp.route("/sites/<subdomain>")
@dashboard_bp.route("/sites/<subdomain>/<path:page>")
def serve_website(subdomain, page=None):
    """Serve a published user website.

    Pages are stored as separate html/css/js (see UserWebsite.pages) and
    the generated HTML links to them as real external files
    (<link rel="stylesheet" href="style.css">, <script src="script.js">)
    — there's no static file route for those per-page paths, so they're
    inlined into the served document here instead. Without this, a
    published site loaded with no styling/behavior at all (the browser's
    404s on style.css/script.js just fail silently), which is very
    plausibly what "publish isn't working" was actually seeing."""
    from app.models.platform import UserWebsite
    website = UserWebsite.query.filter_by(subdomain=subdomain, published=True).first_or_404()
    website.view_count = (website.view_count or 0) + 1
    db.session.commit()

    pages = website.pages or []
    page_name = page or "Home"
    matched = None
    for p in pages:
        if p.get("name", "").lower() == page_name.lower() or (page is None and p.get("order", 99) == 0):
            matched = p
            break
    if not matched and pages:
        matched = pages[0]
    if not matched:
        abort(404)

    html = matched.get("html", "")
    css = matched.get("css", "")
    js = matched.get("js", "")
    if css and "</head>" in html:
        html = html.replace("</head>", f"<style>{css}</style></head>", 1)
    elif css:
        html = f"<style>{css}</style>" + html
    if js and "</body>" in html:
        html = html.replace("</body>", f"<script>{js}</script></body>", 1)
    elif js:
        html = html + f"<script>{js}</script>"
    return html, 200, {"Content-Type": "text/html"}


@dashboard_bp.route("/pay-link/<slug>", methods=["GET", "POST"])
def pay_link_view(slug):
    """Public buyer page for a user-created Payment Link. Only shows
    payment methods the LINK OWNER has actually connected in their own
    Gateway Manager — never falls back to the site admin's gateways, so
    a buyer can't accidentally pay into the wrong account. Also enforces
    the link's advanced settings (expiry, purchase limit, password) and
    adapts to its type (fixed price vs donation/custom-amount)."""
    from app.models.platform import UserPaymentLink
    from flask import session as _session
    link = UserPaymentLink.query.filter_by(slug=slug, active=True).first_or_404()
    settings = link.settings or {}
    if settings.get("archived"):
        abort(404)

    expiry = settings.get("expiry")
    if expiry:
        try:
            if datetime.utcnow() > datetime.fromisoformat(expiry):
                return render_template("dashboard/pay_link_public.html", link=link, gateways=[], expired=True)
        except (ValueError, TypeError):
            pass
    purchase_limit = settings.get("purchase_limit")
    if purchase_limit and (link.payment_count or 0) >= int(purchase_limit):
        return render_template("dashboard/pay_link_public.html", link=link, gateways=[], sold_out=True)

    required_password = settings.get("password")
    unlock_key = f"paylink_pw_ok_{link.id}"
    if required_password:
        if request.method == "POST":
            if request.form.get("password") == required_password:
                _session[unlock_key] = True
                return redirect(request.path)
            return render_template("dashboard/pay_link_password_gate.html", link=link, error=True), 401
        if not _session.get(unlock_key):
            return render_template("dashboard/pay_link_password_gate.html", link=link, error=False)
    elif request.method == "POST":
        return redirect(request.path)

    link.view_count = (link.view_count or 0) + 1
    db.session.commit()

    from app.utils.payments import get_user_enabled_gateways
    gateways = get_user_enabled_gateways(link.user_id)
    enabled_subset = settings.get("enabled_gateways")
    if enabled_subset:
        gateways = [g for g in gateways if g in enabled_subset]

    from app.utils.qr import generate_qr_data_uri
    qr_data_uri = generate_qr_data_uri(url_for("dashboard.pay_link_view", slug=slug, _external=True))

    link_type = settings.get("link_type", "single")
    return render_template(
        "dashboard/pay_link_public.html", link=link, gateways=gateways,
        link_type=link_type, min_amount=settings.get("min_amount"), max_amount=settings.get("max_amount"),
        qr_data_uri=qr_data_uri,
        collect_payer_info=settings.get("collect_payer_info", True),
        seller_bio=settings.get("seller_bio"),
        order_bump=settings.get("order_bump"),
    )


@dashboard_bp.route("/pay-link/<slug>/checkout/<gateway>", methods=["POST"])
def pay_link_checkout(slug, gateway):
    from app.models.platform import UserPaymentLink, UserPaymentLinkOrder
    from flask import session as _session
    from decimal import Decimal, InvalidOperation
    from types import SimpleNamespace
    import secrets
    link = UserPaymentLink.query.filter_by(slug=slug, active=True).first_or_404()
    settings = link.settings or {}

    # Re-validate everything server-side — a buyer could hit this route
    # directly, bypassing whatever the view route already checked.
    if settings.get("archived"):
        abort(404)
    expiry = settings.get("expiry")
    if expiry:
        try:
            if datetime.utcnow() > datetime.fromisoformat(expiry):
                flash("This payment link has expired.", "danger")
                return redirect(url_for("dashboard.pay_link_view", slug=slug))
        except (ValueError, TypeError):
            pass
    purchase_limit = settings.get("purchase_limit")
    if purchase_limit and (link.payment_count or 0) >= int(purchase_limit):
        flash("This payment link has reached its purchase limit.", "danger")
        return redirect(url_for("dashboard.pay_link_view", slug=slug))
    if settings.get("password") and not _session.get(f"paylink_pw_ok_{link.id}"):
        return redirect(url_for("dashboard.pay_link_view", slug=slug))

    payer_email = (request.form.get("payer_email") or "").strip()
    payer_name = (request.form.get("payer_name") or "").strip()
    collect_info = settings.get("collect_payer_info", True)
    if collect_info and not payer_email:
        flash("Please enter your email so a receipt can be sent to you.", "danger")
        return redirect(url_for("dashboard.pay_link_view", slug=slug))
    if not payer_email:
        payer_email = f"guest-{secrets.token_hex(4)}@buyer.local"
        payer_name = payer_name or "Guest"

    # Determine the real amount — fixed price, or buyer-entered for a
    # donation / custom-amount link, clamped to the configured range and
    # NEVER trusted purely from the client.
    link_type = settings.get("link_type", "single")
    if link_type in ("donation", "custom_amount"):
        try:
            amount = Decimal(str(request.form.get("amount", "0")))
        except InvalidOperation:
            amount = Decimal("0")
        min_amt = Decimal(str(settings.get("min_amount") or "1"))
        max_amt = Decimal(str(settings.get("max_amount"))) if settings.get("max_amount") else None
        if amount < min_amt or (max_amt and amount > max_amt):
            flash(f"Please enter an amount of at least {min_amt}" + (f" and at most {max_amt}" if max_amt else "") + ".", "danger")
            return redirect(url_for("dashboard.pay_link_view", slug=slug))
    else:
        amount = Decimal(str(link.amount))

    # Order bump — an optional, buyer-opted-in add-on item.
    bump_cfg = settings.get("order_bump") or {}
    include_bump = request.form.get("include_bump") == "1"
    bump_amount = Decimal("0")
    if bump_cfg.get("enabled") and include_bump:
        try:
            bump_amount = Decimal(str(bump_cfg.get("price", "0")))
        except InvalidOperation:
            bump_amount = Decimal("0")
    amount += bump_amount

    # Coupon — validated and applied server-side, never trusted from the
    # discounted total the client might send.
    coupon_cfg = settings.get("coupon") or {}
    coupon_input = (request.form.get("coupon_code") or "").strip()
    discount_amount = Decimal("0")
    coupon_applied = False
    if coupon_cfg.get("code") and coupon_input.lower() == coupon_cfg["code"].strip().lower():
        expiry_c = coupon_cfg.get("expiry")
        expired_c = False
        if expiry_c:
            try:
                expired_c = datetime.utcnow() > datetime.fromisoformat(expiry_c)
            except (ValueError, TypeError):
                expired_c = False
        limit_c = coupon_cfg.get("usage_limit")
        uses_so_far = coupon_cfg.get("uses", 0) or 0
        if not expired_c and not (limit_c and uses_so_far >= int(limit_c)):
            if coupon_cfg.get("type") == "percent":
                discount_amount = amount * Decimal(str(coupon_cfg.get("value", 0))) / Decimal("100")
            else:
                discount_amount = Decimal(str(coupon_cfg.get("value", 0)))
            discount_amount = min(discount_amount, amount)
            coupon_applied = True
    amount -= discount_amount
    if amount < 0:
        amount = Decimal("0")
    if coupon_applied:
        # Counted at checkout-attempt time (not confirmed payment) — the
        # simplest honest tradeoff given payments can still fail after
        # this point; a failed/abandoned checkout still "used" the code.
        settings = dict(link.settings or {})
        cc = dict(settings.get("coupon") or {})
        cc["uses"] = (cc.get("uses", 0) or 0) + 1
        settings["coupon"] = cc
        link.settings = settings
        db.session.commit()

    fake_payer = SimpleNamespace(email=payer_email, name=payer_name or "Guest")

    from app.utils.payments import get_user_gateway_credentials
    credentials = get_user_gateway_credentials(link.user_id, gateway)
    if not credentials:
        flash("The seller hasn't finished connecting this payment method yet.", "danger")
        return redirect(url_for("dashboard.pay_link_view", slug=slug))

    order = UserPaymentLinkOrder(
        payment_link_id=link.id, user_id=link.user_id, buyer_name=payer_name or "Guest",
        buyer_email=payer_email, amount=amount, currency=link.currency, gateway=gateway, status="pending",
    )
    db.session.add(order)
    db.session.commit()

    try:
        if gateway == "paystack":
            from app.utils.payments import create_paystack_transaction
            data = create_paystack_transaction(link.title, float(amount), fake_payer,
                url_for("dashboard.pay_link_callback", slug=slug, gateway="paystack", order_id=order.id, _external=True),
                metadata={"user_payment_link_id": link.id, "order_id": order.id}, credentials=credentials)
            order.reference = data.get("reference")
            db.session.commit()
            return redirect(data["authorization_url"], code=303)
        if gateway == "flutterwave":
            from app.utils.payments import create_flutterwave_transaction
            tx_ref = f"upl-{link.id}-{order.id}-{int(datetime.utcnow().timestamp())}"
            order.reference = tx_ref
            db.session.commit()
            checkout_link = create_flutterwave_transaction(link.title, float(amount), fake_payer, tx_ref,
                url_for("dashboard.pay_link_callback", slug=slug, gateway="flutterwave", tx_ref=tx_ref, order_id=order.id, _external=True),
                credentials=credentials)
            return redirect(checkout_link, code=303)
        if gateway == "paypal":
            from app.utils.payments import create_paypal_order
            paypal_order_id, approval_url = create_paypal_order(link.title, float(amount),
                url_for("dashboard.pay_link_callback", slug=slug, gateway="paypal", order_id=order.id, _external=True),
                url_for("dashboard.pay_link_view", slug=slug, _external=True), credentials=credentials)
            order.reference = paypal_order_id
            db.session.commit()
            return redirect(approval_url, code=303)
        if gateway == "stripe":
            from app.utils.payments import create_stripe_session
            session_obj = create_stripe_session(link.title, float(amount), fake_payer,
                url_for("dashboard.pay_link_callback", slug=slug, gateway="stripe", order_id=order.id, _external=True),
                url_for("dashboard.pay_link_view", slug=slug, _external=True), credentials=credentials)
            order.reference = session_obj.id
            db.session.commit()
            return redirect(session_obj.url, code=303)
    except Exception as e:
        current_app.logger.error(f"Payment link checkout error ({gateway}): {e}")
        order.status = "failed"
        db.session.commit()
        flash(f"Payment could not be started: {e}", "danger")
        return redirect(url_for("dashboard.pay_link_view", slug=slug))

    order.status = "failed"
    db.session.commit()
    flash("That payment method isn't available.", "danger")
    return redirect(url_for("dashboard.pay_link_view", slug=slug))


@dashboard_bp.route("/pay-link/<slug>/callback/<gateway>")
def pay_link_callback(slug, gateway):
    from app.models.platform import UserPaymentLink, UserPaymentLinkOrder
    from decimal import Decimal
    link = UserPaymentLink.query.filter_by(slug=slug).first_or_404()
    from app.utils.payments import get_user_gateway_credentials
    credentials = get_user_gateway_credentials(link.user_id, gateway)

    order = None
    order_id = request.args.get("order_id")
    if order_id:
        order = UserPaymentLinkOrder.query.filter_by(id=order_id, payment_link_id=link.id).first()

    verified = False
    if gateway == "paystack":
        from app.utils.payments import verify_paystack_payment
        verified = bool(verify_paystack_payment(request.args.get("reference"), credentials=credentials))
    elif gateway == "flutterwave":
        from app.utils.payments import verify_flutterwave_payment
        transaction_id = request.args.get("transaction_id")
        verified = bool(verify_flutterwave_payment(transaction_id, credentials=credentials)) if transaction_id else False
    elif gateway == "paypal":
        from app.utils.payments import capture_paypal_order
        verified = bool(capture_paypal_order(request.args.get("token"), credentials=credentials))
    elif gateway == "stripe":
        verified = True  # see note on the equivalent admin flow: webhook is the real source of truth

    if verified:
        pay_amount = order.amount if order else link.amount
        if order:
            order.status = "paid"
            order.paid_at = datetime.utcnow()
        link.payment_count = (link.payment_count or 0) + 1
        link.total_collected = (link.total_collected or Decimal("0")) + Decimal(str(pay_amount))

        # If this payment link was auto-created for an invoice, the
        # invoice itself needs to flip to paid too — otherwise the
        # dashboard would show the payment landing while the invoice
        # list still says "unpaid" forever.
        from app.models.platform import UserInvoice
        inv = UserInvoice.query.filter_by(payment_link_id=link.id).first()
        if inv and inv.status != "paid":
            inv.status = "paid"
            inv.paid_at = datetime.utcnow()

        db.session.commit()

        _send_payment_link_emails(link, order)

        settings = link.settings or {}
        if settings.get("redirect_url"):
            return redirect(settings["redirect_url"])
        return render_template("dashboard/pay_link_thanks.html", link=link, order=order)

    if order:
        order.status = "failed"
        db.session.commit()
    flash("We couldn't verify that payment.", "danger")
    return redirect(url_for("dashboard.pay_link_view", slug=slug))


def _send_payment_link_emails(link, order):
    """Real buyer receipt + seller sale notification with template
    variables — Doc 3's 'Customer Emails' step. Never lets an email
    failure break the payment flow (best-effort, logged)."""
    from app.utils.email import send_email
    settings = link.settings or {}
    email_cfg = settings.get("emails") or {}
    seller = link.user
    amount_display = f"{order.amount} {order.currency}" if order else f"{link.amount} {link.currency}"
    buyer_name = (order.buyer_name if order else "there") or "there"
    buyer_email = order.buyer_email if order else None

    variables = {
        "{{customer_name}}": buyer_name,
        "{{product_name}}": link.title,
        "{{amount}}": str(order.amount if order else link.amount),
        "{{currency}}": (order.currency if order else link.currency) or "",
        "{{order_number}}": str(order.id) if order else "",
        "{{purchase_date}}": datetime.utcnow().strftime("%Y-%m-%d"),
        "{{seller_name}}": seller.name if seller else "",
        "{{support_email}}": email_cfg.get("support_email", ""),
    }

    def _fill(template, fallback):
        text = template or fallback
        for k, v in variables.items():
            text = text.replace(k, str(v))
        return text

    try:
        if buyer_email:
            subject = _fill(email_cfg.get("buyer_subject"), f"Payment received — {link.title}")
            body = _fill(email_cfg.get("buyer_body"),
                         f"<p>Hi {buyer_name},</p><p>We've received your payment of {amount_display} for <strong>{link.title}</strong>.</p><p>Thank you!</p>")
            send_email(buyer_email, subject, body)
    except Exception:
        current_app.logger.exception("Payment link buyer receipt email failed")

    try:
        if seller and seller.email:
            subject = f"💰 New payment — {link.title}"
            body = f"<p>You just received a payment of {amount_display} for <strong>{link.title}</strong> from {buyer_name} ({buyer_email or 'no email given'}).</p>"
            send_email(seller.email, subject, body)
    except Exception:
        current_app.logger.exception("Payment link seller notification email failed")

    try:
        from app.utils.notifications import notify_user
        if seller:
            notify_user(seller.id, type="payment_link_payment", title="💳 You received a payment",
                        body=f"{amount_display} for {link.title}", link=url_for("dashboard.payment_links"))
            db.session.commit()
    except Exception:
        current_app.logger.exception("Payment link in-app notification failed")


def _inject_page_extras(html, page, extra_script=""):
    """Apply a page's Page Settings (SEO title/description, custom
    header/footer scripts) plus any extra script (nav/tracking) to its
    rendered HTML. Works whether html came from html_content, the block
    renderer, or the checkout page renderer — they're all just strings
    with a <head>/<body> by this point."""
    settings = page.settings or {}
    seo = settings.get("seo") or {}
    scripts = settings.get("custom_scripts") or {}
    head_extra = ""
    if seo.get("title"):
        head_extra += f"<title>{_html_escape(seo['title'])}</title>"
    if seo.get("description"):
        head_extra += f"<meta name='description' content='{_html_escape(seo['description'])}'>"
    if scripts.get("header"):
        head_extra += scripts["header"]
    if head_extra:
        html = html.replace("<head>", "<head>" + head_extra, 1) if "<head>" in html else head_extra + html

    footer_extra = (scripts.get("footer") or "") + extra_script
    if footer_extra:
        html = html.replace("</body>", footer_extra + "</body>", 1) if "</body>" in html else html + footer_extra
    return html


def _html_escape(s):
    import html as _html
    return _html.escape(str(s or ""), quote=True)


_TRAFFIC_SOURCE_DOMAINS = {
    "google.": "Google", "bing.": "Bing", "duckduckgo.": "DuckDuckGo", "yahoo.": "Yahoo",
    "facebook.": "Facebook", "fb.": "Facebook", "instagram.": "Instagram", "l.instagram.": "Instagram",
    "twitter.": "Twitter/X", "t.co": "Twitter/X", "x.com": "Twitter/X",
    "tiktok.": "TikTok", "linkedin.": "LinkedIn", "youtube.": "YouTube",
    "reddit.": "Reddit", "pinterest.": "Pinterest", "whatsapp.": "WhatsApp",
}


def _classify_traffic_source(referrer, own_host):
    """Real, code-only traffic-source classification from the Referer
    header — no external API/GeoIP dependency. 'Direct' covers no
    referrer at all (typed URL, bookmark, or a stripped referrer);
    'Internal' covers navigating between a funnel's own pages."""
    if not referrer:
        return "Direct"
    try:
        from urllib.parse import urlparse
        host = (urlparse(referrer).netloc or "").lower()
    except Exception:
        return "Direct"
    if not host:
        return "Direct"
    if own_host and own_host in host:
        return "Internal"
    for needle, label in _TRAFFIC_SOURCE_DOMAINS.items():
        if needle in host:
            return label
    return "Other Websites"


def _classify_device(user_agent):
    """Real device-type classification from the User-Agent header —
    heuristic, not a full UA-parsing library, but code-only (no external
    service)."""
    ua = (user_agent or "").lower()
    if "ipad" in ua or ("tablet" in ua) or ("android" in ua and "mobile" not in ua):
        return "Tablet"
    if "mobi" in ua or "iphone" in ua or "android" in ua:
        return "Mobile"
    return "Desktop"


def _classify_browser(user_agent):
    ua = (user_agent or "").lower()
    if "edg/" in ua or "edga" in ua or "edgios" in ua:
        return "Edge"
    if "opr/" in ua or "opera" in ua:
        return "Opera"
    if "chrome" in ua and "chromium" not in ua:
        return "Chrome"
    if "crios" in ua:
        return "Chrome"
    if "fxios" in ua or "firefox" in ua:
        return "Firefox"
    if "safari" in ua and "chrome" not in ua:
        return "Safari"
    return "Other"


def _record_funnel_pageview(funnel, request_obj):
    """Bumps a funnel-level analytics summary: traffic source, device,
    browser, and a real (not sampled) unique-visitor count via a
    long-lived first-party cookie. Returns the visitor cookie value the
    caller should set on the response (None if the visitor already had
    one — nothing to set)."""
    import uuid
    settings = dict(funnel.settings or {})
    analytics = dict(settings.get("analytics") or {})
    sources = dict(analytics.get("traffic_sources") or {})
    devices = dict(analytics.get("devices") or {})
    browsers = dict(analytics.get("browsers") or {})

    own_host = (request_obj.host or "").lower()
    source = _classify_traffic_source(request_obj.referrer, own_host)
    device = _classify_device(request_obj.headers.get("User-Agent"))
    browser = _classify_browser(request_obj.headers.get("User-Agent"))
    sources[source] = sources.get(source, 0) + 1
    devices[device] = devices.get(device, 0) + 1
    browsers[browser] = browsers.get(browser, 0) + 1
    analytics["traffic_sources"] = sources
    analytics["devices"] = devices
    analytics["browsers"] = browsers

    new_visitor_cookie = None
    visitor_cookie = request_obj.cookies.get("bzn_visitor")
    if not visitor_cookie:
        new_visitor_cookie = str(uuid.uuid4())
        analytics["unique_visitors"] = (analytics.get("unique_visitors") or 0) + 1

    settings["analytics"] = analytics
    funnel.settings = settings
    return new_visitor_cookie


@dashboard_bp.route("/funnels/<subdomain>", methods=["GET", "POST"])
@dashboard_bp.route("/funnels/<subdomain>/<path:page_slug>", methods=["GET", "POST"])
def serve_funnel(subdomain, page_slug=None):
    """Serve a page from a published funnel. With no page_slug, serves
    the funnel's entry page. A small nav script is injected so any
    element in the generated HTML marked data-funnel-nav="next" /
    "accept" / "decline" follows this page's real connections instead
    of being a dead link. Also handles per-page password protection and
    applies Page Settings (SEO, custom scripts)."""
    import json as _json
    from flask import session as _session
    from app.models.platform import UserFunnel, FunnelPage
    funnel = UserFunnel.query.filter_by(subdomain=subdomain, published=True).first_or_404()
    pages = funnel.ordered_pages()
    if not pages:
        return "<h1>Coming Soon</h1>", 200, {"Content-Type": "text/html"}

    page = None
    if page_slug:
        page = next((p for p in pages if p.slug == page_slug), None)
        if page is None and page_slug.isdigit():
            # Backward-compat fallback for links published before this
            # rebuild, which used a numeric step index instead of a slug.
            idx = int(page_slug)
            page = pages[idx] if 0 <= idx < len(pages) else None
    else:
        page = funnel.entry_page or pages[0]
    if page is None:
        abort(404)

    # ── Password protection (per page) ──────────────────────────────
    page_settings = page.settings or {}
    required_password = page_settings.get("password")
    unlock_key = f"funnel_pw_ok_{page.id}"
    if required_password:
        if request.method == "POST":
            if request.form.get("password") == required_password:
                _session[unlock_key] = True
                return redirect(request.path)
            return render_template("dashboard/funnel_password_gate.html", funnel=funnel, page=page, error=True), 401
        if not _session.get(unlock_key):
            return render_template("dashboard/funnel_password_gate.html", funnel=funnel, page=page, error=False)
    elif request.method == "POST":
        # No password required on this page — nothing meaningful to POST to it.
        return redirect(request.path)

    funnel.view_count = (funnel.view_count or 0) + 1
    analytics = dict(page_settings.get("analytics") or {})
    analytics["views"] = (analytics.get("views") or 0) + 1
    page_settings = {**page_settings, "analytics": analytics}
    page.settings = page_settings
    new_visitor_cookie = _record_funnel_pageview(funnel, request)
    db.session.commit()

    nav_script = f"""
<script>
  window.FUNNEL_NEXT_URL = {_json.dumps(_funnel_page_url(funnel, page.next_page))};
  window.FUNNEL_ACCEPT_URL = {_json.dumps(_funnel_page_url(funnel, page.branch_yes))};
  window.FUNNEL_DECLINE_URL = {_json.dumps(_funnel_page_url(funnel, page.branch_no))};
  function funnelBeacon(ev) {{
    try {{
      var url = {_json.dumps(url_for('dashboard.funnel_track', subdomain=subdomain))};
      var payload = JSON.stringify({{page_id: {page.id}, event: ev}});
      if (navigator.sendBeacon) {{ navigator.sendBeacon(url, new Blob([payload], {{type:'application/json'}})); }}
      else {{ fetch(url, {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:payload, keepalive:true}}); }}
    }} catch (e) {{}}
  }}
  document.addEventListener('DOMContentLoaded', function () {{
    document.querySelectorAll('[data-funnel-nav]').forEach(function (el) {{
      var nav = el.getAttribute('data-funnel-nav');
      var url = nav === 'accept' ? window.FUNNEL_ACCEPT_URL
              : nav === 'decline' ? window.FUNNEL_DECLINE_URL
              : window.FUNNEL_NEXT_URL;
      if (url) el.addEventListener('click', function (e) {{ e.preventDefault(); funnelBeacon('convert'); window.location.href = url; }});
    }});
  }});
</script>"""

    checkout = page_settings.get("checkout")
    if page.page_type == "checkout" and checkout:
        from app.utils.funnel_checkout import render_checkout_page_html
        from app.utils.funnel_blocks import render_blocks_body_html
        from app.utils.payments import get_user_enabled_gateways
        from flask_wtf.csrf import generate_csrf
        gateways = get_user_enabled_gateways(funnel.user_id)
        action_base = url_for("dashboard.funnel_checkout_start", subdomain=subdomain, page_slug=page.slug, gateway="__G__")
        action_base = action_base.replace("__G__", "")
        blocks_html = render_blocks_body_html(page.blocks, page_id=page.id) if page.blocks else ""
        html = render_checkout_page_html(page, checkout, gateways, action_base, generate_csrf(), extra_content_html=blocks_html)
    else:
        html = page.html_content or "<h1>Coming Soon</h1>"

    html = _inject_page_extras(html, page, extra_script=nav_script)
    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html"
    if new_visitor_cookie:
        resp.set_cookie("bzn_visitor", new_visitor_cookie, max_age=60 * 60 * 24 * 365 * 2, httponly=True, samesite="Lax")
    return resp


@dashboard_bp.route("/funnels/<subdomain>/track", methods=["POST"])
def funnel_track(subdomain):
    """Public beacon endpoint — records a conversion for a page inside a
    published funnel (views are counted server-side in serve_funnel;
    this only handles the client-reported 'convert' event fired when a
    visitor actually clicks a funnel-nav element)."""
    from app.models.platform import UserFunnel, FunnelPage
    funnel = UserFunnel.query.filter_by(subdomain=subdomain, published=True).first()
    if not funnel:
        return jsonify({"ok": False}), 404
    data = request.get_json(silent=True) or {}
    try:
        page_id = int(data.get("page_id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False}), 400
    page = FunnelPage.query.filter_by(id=page_id, funnel_id=funnel.id).first()
    if not page:
        return jsonify({"ok": False}), 404
    if data.get("event") == "convert":
        settings = dict(page.settings or {})
        analytics = dict(settings.get("analytics") or {})
        analytics["conversions"] = (analytics.get("conversions") or 0) + 1
        settings["analytics"] = analytics
        page.settings = settings
        funnel.conversion_count = (funnel.conversion_count or 0) + 1
        db.session.commit()
    return jsonify({"ok": True})


@dashboard_bp.route("/funnels/leads/<int:page_id>/submit", methods=["POST"])
@limiter.limit("30 per minute")
def funnel_lead_submit(page_id):
    """The actual "how do I collect information from the sales funnel"
    mechanism — what a page's Form block(s) POST to (see the `form`
    block renderer in app/utils/funnel_blocks.py). Public and
    unauthenticated by necessity (an anonymous visitor is the caller).

    Validates against the SAME field config the block was built with
    (not just whatever the client sends) — required fields are enforced
    server-side too, and only keys the form was actually configured
    with get stored, so a manipulated request can't stuff arbitrary
    extra data into a lead row.
    """
    from app.models.platform import FunnelPage, UserFunnel, FunnelLead
    page = FunnelPage.query.get_or_404(page_id)
    funnel = UserFunnel.query.filter_by(id=page.funnel_id, published=True).first()
    if not funnel:
        return jsonify({"ok": False, "error": "This form is not currently active."}), 404

    payload = request.get_json(silent=True) or {}
    block_id = str(payload.get("block_id") or "")
    submitted = payload.get("data") or {}
    if not isinstance(submitted, dict):
        return jsonify({"ok": False, "error": "Invalid submission."}), 400

    form_block = next((b for b in (page.blocks or []) if b.get("type") == "form" and str(b.get("id")) == block_id), None)
    if not form_block:
        # Fall back to the page's first form block if block_id wasn't
        # sent/matched — keeps this working for pages with exactly one
        # form even if the id gets lost somewhere in a re-render.
        form_block = next((b for b in (page.blocks or []) if b.get("type") == "form"), None)
    if not form_block:
        return jsonify({"ok": False, "error": "This form is no longer available on this page."}), 404

    field_defs = (form_block.get("data") or {}).get("fields") or []
    clean = {}
    missing = []
    for fdef in field_defs:
        key = (fdef.get("key") or "").strip()
        if not key:
            continue
        value = str(submitted.get(key) or "").strip()
        required = str(fdef.get("required") or "").strip().lower() in ("yes", "true", "1")
        if required and not value:
            missing.append(fdef.get("label") or key)
        if value:
            clean[key] = value[:2000]
    if missing:
        return jsonify({"ok": False, "error": f"Please fill in: {', '.join(missing)}."}), 400
    if not clean:
        return jsonify({"ok": False, "error": "Please fill in the form before submitting."}), 400

    lead = FunnelLead(
        funnel_id=funnel.id, page_id=page.id, user_id=funnel.user_id,
        block_id=block_id or (form_block.get("id") or ""), data=clean,
        source_ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")[:64],
    )
    db.session.add(lead)
    db.session.commit()

    try:
        from app.utils.notifications import notify_user
        notify_user(funnel.user_id, type="funnel_lead", title="📋 New lead captured",
                    body=f"Someone submitted a form on \"{page.title}\" ({funnel.title}).")
    except Exception:
        current_app.logger.exception("Funnel lead notification failed")

    return jsonify({"ok": True})


@dashboard_bp.route("/funnels/<subdomain>/<page_slug>/checkout/<gateway>", methods=["POST"])
def funnel_checkout_start(subdomain, page_slug, gateway):
    """Start a real payment for a funnel Checkout page, using the funnel
    OWNER's connected gateway credentials (same app.utils.payments layer
    Payment Links already uses in production) — buyer money goes into
    the funnel owner's own account, never the site admin's."""
    from app.models.platform import UserFunnel, FunnelPage, FunnelOrder
    from types import SimpleNamespace
    from decimal import Decimal

    funnel = UserFunnel.query.filter_by(subdomain=subdomain, published=True).first_or_404()
    page = FunnelPage.query.filter_by(funnel_id=funnel.id, slug=page_slug).first_or_404()
    checkout = (page.settings or {}).get("checkout")
    if not checkout:
        abort(404)

    buyer_email = (request.form.get("buyer_email") or "").strip()
    buyer_name = (request.form.get("buyer_name") or "").strip()
    checkout_url = url_for("dashboard.serve_funnel", subdomain=subdomain, page_slug=page_slug)
    if not buyer_email:
        return redirect(checkout_url)
    fake_buyer = SimpleNamespace(email=buyer_email, name=buyer_name or "Guest")

    from app.utils.payments import get_user_gateway_credentials
    credentials = get_user_gateway_credentials(funnel.user_id, gateway)
    if not credentials:
        return redirect(checkout_url)

    amount = float(checkout.get("price") or 0)
    title = checkout.get("product_name") or page.title

    order = FunnelOrder(
        funnel_id=funnel.id, page_id=page.id, user_id=funnel.user_id,
        customer_name=buyer_name, customer_email=buyer_email,
        product_name=title, amount=Decimal(str(amount)), currency=checkout.get("currency", "USD"),
        gateway=gateway, status="pending",
    )
    db.session.add(order)
    db.session.commit()

    try:
        if gateway == "paystack":
            from app.utils.payments import create_paystack_transaction
            data = create_paystack_transaction(title, amount, fake_buyer,
                url_for("dashboard.funnel_checkout_callback", subdomain=subdomain, page_slug=page_slug, gateway="paystack", order_id=order.id, _external=True),
                metadata={"funnel_order_id": order.id}, credentials=credentials)
            order.gateway_reference = data.get("reference")
            db.session.commit()
            return redirect(data["authorization_url"], code=303)
        if gateway == "flutterwave":
            from app.utils.payments import create_flutterwave_transaction
            tx_ref = f"fnl-{order.id}-{int(datetime.utcnow().timestamp())}"
            order.gateway_reference = tx_ref
            db.session.commit()
            checkout_link = create_flutterwave_transaction(title, amount, fake_buyer, tx_ref,
                url_for("dashboard.funnel_checkout_callback", subdomain=subdomain, page_slug=page_slug, gateway="flutterwave", order_id=order.id, tx_ref=tx_ref, _external=True),
                credentials=credentials)
            return redirect(checkout_link, code=303)
        if gateway == "paypal":
            from app.utils.payments import create_paypal_order
            paypal_order_id, approval_url = create_paypal_order(title, amount,
                url_for("dashboard.funnel_checkout_callback", subdomain=subdomain, page_slug=page_slug, gateway="paypal", order_id=order.id, _external=True),
                checkout_url, credentials=credentials)
            order.gateway_reference = paypal_order_id
            db.session.commit()
            return redirect(approval_url, code=303)
        if gateway == "stripe":
            from app.utils.payments import create_stripe_session
            session_obj = create_stripe_session(title, amount, fake_buyer,
                url_for("dashboard.funnel_checkout_callback", subdomain=subdomain, page_slug=page_slug, gateway="stripe", order_id=order.id, _external=True),
                checkout_url, credentials=credentials)
            order.gateway_reference = session_obj.id
            db.session.commit()
            return redirect(session_obj.url, code=303)
    except Exception as e:
        current_app.logger.error(f"Funnel checkout error ({gateway}) for order {order.id}: {e}")
        order.status = "failed"
        db.session.commit()
        return redirect(checkout_url)

    return redirect(checkout_url)


@dashboard_bp.route("/funnels/<subdomain>/<page_slug>/callback/<gateway>")
def funnel_checkout_callback(subdomain, page_slug, gateway):
    """Verify a funnel checkout payment and route the buyer onward: the
    page's 'accept' branch if one is set, else its normal 'next' page,
    else a generic inline thank-you. Mirrors pay_link_callback's
    verification pattern exactly."""
    from app.models.platform import UserFunnel, FunnelPage, FunnelOrder
    from decimal import Decimal
    funnel = UserFunnel.query.filter_by(subdomain=subdomain).first_or_404()
    page = FunnelPage.query.filter_by(funnel_id=funnel.id, slug=page_slug).first_or_404()
    checkout_url = url_for("dashboard.serve_funnel", subdomain=subdomain, page_slug=page_slug)

    order_id = request.args.get("order_id")
    order = FunnelOrder.query.filter_by(id=order_id, funnel_id=funnel.id).first() if order_id else None
    if not order:
        return redirect(checkout_url)

    from app.utils.payments import get_user_gateway_credentials
    credentials = get_user_gateway_credentials(funnel.user_id, gateway)
    verified = False
    if gateway == "paystack":
        from app.utils.payments import verify_paystack_payment
        verified = bool(verify_paystack_payment(request.args.get("reference") or order.gateway_reference, credentials=credentials))
    elif gateway == "flutterwave":
        from app.utils.payments import verify_flutterwave_payment
        transaction_id = request.args.get("transaction_id")
        verified = bool(verify_flutterwave_payment(transaction_id, credentials=credentials)) if transaction_id else False
    elif gateway == "paypal":
        from app.utils.payments import capture_paypal_order
        verified = bool(capture_paypal_order(request.args.get("token") or order.gateway_reference, credentials=credentials))
    elif gateway == "stripe":
        verified = True  # webhook is the real source of truth, same caveat as the equivalent Payment Links flow

    if not verified:
        order.status = "failed"
        db.session.commit()
        return redirect(checkout_url)

    order.status = "paid"
    order.paid_at = datetime.utcnow()
    db.session.commit()

    checkout = (page.settings or {}).get("checkout") or {}
    _send_funnel_order_emails(funnel, page, order, checkout)

    if checkout.get("delivery_type") == "digital" and checkout.get("digital_file_url"):
        # "They pay, they just get a file, nothing else happens" — skip
        # the accept/next-page branch entirely and hand over the
        # download right here, matching what the builder's "After
        # Payment" setting promises rather than silently still routing
        # through the funnel's page connections.
        file_url = _html_escape(checkout["digital_file_url"])
        label = _html_escape(checkout.get("digital_file_label") or "Download your file")
        return (f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Thank you</title></head>"
                f"<body style='font-family:sans-serif;text-align:center;padding:80px 20px;background:#0a0a0a;color:#fff;'>"
                f"<h1>Thank you for your purchase!</h1>"
                f"<p style='color:#a3a3a3;margin:12px 0 28px;'>A receipt has been sent to {_html_escape(order.customer_email)}.</p>"
                f"<a href='{file_url}' style='display:inline-block;padding:14px 32px;background:#1DB954;color:#000;"
                f"border-radius:9999px;text-decoration:none;font-weight:700;'>{label}</a>"
                f"</body></html>"), 200, {"Content-Type": "text/html"}

    destination = page.branch_yes or page.next_page
    if destination:
        return redirect(_funnel_page_url(funnel, destination))
    return (f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Thank you</title></head>"
            f"<body style='font-family:sans-serif;text-align:center;padding:80px 20px;'>"
            f"<h1>Thank you for your purchase!</h1><p>A receipt has been sent to {order.customer_email}.</p>"
            f"</body></html>"), 200, {"Content-Type": "text/html"}


def _send_funnel_order_emails(funnel, page, order, checkout):
    """Buyer receipt + owner sale notification for a funnel Checkout
    order — same proven pattern as _send_payment_link_emails above,
    adapted for FunnelOrder. Previously nothing sent any email on a
    funnel purchase at all; the "thank you" pages have said "a receipt
    has been sent" for a while even though none ever was. Never lets an
    email failure break the payment flow (best-effort, logged)."""
    from app.utils.email import send_email
    seller = funnel.user
    amount_display = f"{order.amount} {order.currency}"
    buyer_name = order.customer_name or "there"
    settings = funnel.settings or {}
    email_cfg = settings.get("emails") or {}

    digital_line = ""
    if checkout.get("delivery_type") == "digital" and checkout.get("digital_file_url"):
        label = checkout.get("digital_file_label") or "Download your file"
        digital_line = f'<p style="margin-top:16px;"><a href="{_html_escape(checkout["digital_file_url"])}">{_html_escape(label)}</a></p>'

    try:
        if order.customer_email:
            default_subject = f"Payment received — {order.product_name}"
            default_body = (f"<p>Hi {_html_escape(buyer_name)},</p>"
                             f"<p>We've received your payment of {_html_escape(amount_display)} for "
                             f"<strong>{_html_escape(order.product_name)}</strong>.</p>{digital_line}<p>Thank you!</p>")
            subject = (email_cfg.get("buyer_subject") or default_subject)
            body = (email_cfg.get("buyer_body") or default_body)
            if email_cfg.get("buyer_subject"):
                subject = subject.replace("{{customer_name}}", buyer_name).replace("{{product_name}}", order.product_name or "")
            if email_cfg.get("buyer_body"):
                body = (body.replace("{{customer_name}}", buyer_name)
                             .replace("{{product_name}}", order.product_name or "")
                             .replace("{{amount}}", str(order.amount))
                             .replace("{{currency}}", order.currency or "")) + digital_line
            # The buyer needs to see THIS SELLER's identity, not the
            # platform's — the SMTP relay is necessarily shared (single
            # set of credentials for the whole app), but From-display-name
            # and Reply-To are per-send and were simply never being set
            # here. Without this, every funnel's receipts looked like they
            # came from the platform account, and hitting "Reply" on a
            # receipt would land in the platform's inbox, not the seller's.
            sender_name = email_cfg.get("sender_name") or funnel.title or (seller.name if seller else None) or "Bazillin Studio"
            reply_to = email_cfg.get("reply_to") or (seller.email if seller else None)
            send_email(order.customer_email, subject, body, from_name=sender_name, reply_to=reply_to)
    except Exception:
        current_app.logger.exception("Funnel order buyer receipt email failed")

    try:
        notify_email = email_cfg.get("notification_email") or (seller.email if seller else None)
        if notify_email:
            subject = f"💰 New sale — {order.product_name}"
            body = (f"<p>You just received a payment of {_html_escape(amount_display)} for "
                    f"<strong>{_html_escape(order.product_name)}</strong> from {_html_escape(buyer_name)} "
                    f"({_html_escape(order.customer_email or 'no email given')}) on \"{_html_escape(funnel.title)}\".</p>")
            send_email(notify_email, subject, body)
    except Exception:
        current_app.logger.exception("Funnel order notification email failed")

    try:
        from app.utils.notifications import notify_user
        if seller:
            notify_user(seller.id, type="funnel_order_payment", title="💳 You received a payment",
                        body=f"{amount_display} for {order.product_name} on {funnel.title}.")
    except Exception:
        current_app.logger.exception("Funnel order in-app notification failed")


# ══════════════════════════════════════════════════════════════════════
#  PAYMENT GATEWAY MANAGER (per-user — each customer connects their OWN
#  gateway credentials so Payment Links pay into THEIR account)
# ══════════════════════════════════════════════════════════════════════

GATEWAY_FIELDS = {
    "stripe":      {"name": "Stripe",      "fields": [("secret_key", "Secret Key", "sk_live_...")]},
    "paystack":    {"name": "Paystack",    "fields": [("secret_key", "Secret Key", "sk_live_...")]},
    "flutterwave": {"name": "Flutterwave", "fields": [("secret_key", "Secret Key", "FLWSECK_...")]},
    "paypal":      {"name": "PayPal",      "fields": [("client_id", "Client ID", ""), ("client_secret", "Client Secret", "")]},
}


@dashboard_bp.route("/payment-gateways")
@require_any_premium("payment-link-generator", "funnel-builder")
def payment_gateways():
    """Gateway Manager — where a user connects their own Stripe /
    Paystack / Flutterwave / PayPal so their Payment Links charge into
    their own account instead of the site admin's."""
    from app.models.platform import UserPaymentGateway
    connected = {g.gateway: g for g in UserPaymentGateway.query.filter_by(user_id=current_user.id).all()}
    return render_template("dashboard/payment_gateways.html", connected=connected, gateway_fields=GATEWAY_FIELDS)


@dashboard_bp.route("/payment-gateways/<gateway>/connect", methods=["POST"])
@require_any_premium("payment-link-generator", "funnel-builder")
def payment_gateways_connect(gateway):
    from app.models.platform import UserPaymentGateway
    from app.utils.crypto import encrypt_json, mask_secret
    if gateway not in GATEWAY_FIELDS:
        flash("Unknown payment gateway.", "danger")
        return redirect(url_for("dashboard.payment_gateways"))

    creds = {}
    for field_key, _label, _placeholder in GATEWAY_FIELDS[gateway]["fields"]:
        val = (request.form.get(field_key) or "").strip()
        if val:
            creds[field_key] = val
    if not creds:
        flash("Please enter your credentials.", "danger")
        return redirect(url_for("dashboard.payment_gateways"))

    row = UserPaymentGateway.query.filter_by(user_id=current_user.id, gateway=gateway).first()
    if not row:
        row = UserPaymentGateway(user_id=current_user.id, gateway=gateway)
        db.session.add(row)
    row.mode = request.form.get("mode", "live")
    row.credentials_encrypted = encrypt_json(creds)
    primary_secret = creds.get("secret_key") or creds.get("client_secret") or ""
    row.last4 = mask_secret(primary_secret)[-8:] if primary_secret else None
    row.active = True
    row.updated_at = datetime.utcnow()
    db.session.commit()
    flash(f"{GATEWAY_FIELDS[gateway]['name']} connected.", "success")
    return redirect(url_for("dashboard.payment_gateways"))


@dashboard_bp.route("/payment-gateways/<gateway>/disconnect", methods=["POST"])
@require_any_premium("payment-link-generator", "funnel-builder")
def payment_gateways_disconnect(gateway):
    from app.models.platform import UserPaymentGateway
    row = UserPaymentGateway.query.filter_by(user_id=current_user.id, gateway=gateway).first()
    if row:
        db.session.delete(row)
        db.session.commit()
        flash(f"{GATEWAY_FIELDS.get(gateway, {}).get('name', gateway)} disconnected.", "success")
    return redirect(url_for("dashboard.payment_gateways"))


@dashboard_bp.route("/payment-gateways/<gateway>/toggle", methods=["POST"])
@require_any_premium("payment-link-generator", "funnel-builder")
def payment_gateways_toggle(gateway):
    from app.models.platform import UserPaymentGateway
    row = UserPaymentGateway.query.filter_by(user_id=current_user.id, gateway=gateway).first()
    if row:
        row.active = not row.active
        db.session.commit()
    return redirect(url_for("dashboard.payment_gateways"))


def _serialize_gateway_status():
    from app.models.platform import UserPaymentGateway
    connected = {g.gateway: g for g in UserPaymentGateway.query.filter_by(user_id=current_user.id).all()}
    return [
        {"key": key, "name": info["name"], "fields": [{"key": k, "label": l, "placeholder": p} for k, l, p in info["fields"]],
         "connected": key in connected, "active": connected[key].active if key in connected else False,
         "last4": connected[key].last4 if key in connected else None}
        for key, info in GATEWAY_FIELDS.items()
    ]


@dashboard_bp.route("/payment-gateways/status")
@require_any_premium("payment-link-generator", "funnel-builder")
def payment_gateways_status():
    """JSON status for embedding a gateway connector inline somewhere
    other than the full /payment-gateways page — used by the Funnel
    Builder's own Settings modal so a funnel-only customer configures
    payments without leaving the funnel builder at all."""
    return jsonify({"gateways": _serialize_gateway_status()})


@dashboard_bp.route("/payment-gateways/<gateway>/connect-json", methods=["POST"])
@require_any_premium("payment-link-generator", "funnel-builder")
def payment_gateways_connect_json(gateway):
    """Same save logic as payment_gateways_connect() above, JSON in/out
    instead of form-POST + redirect, so a caller like the Funnel
    Builder's inline gateway connector doesn't have to navigate the
    user away to a different page just to save a key."""
    from app.models.platform import UserPaymentGateway
    from app.utils.crypto import encrypt_json, mask_secret
    if gateway not in GATEWAY_FIELDS:
        return jsonify({"error": "Unknown payment gateway."}), 404

    data = request.get_json(silent=True) or {}
    creds = {}
    for field_key, _label, _placeholder in GATEWAY_FIELDS[gateway]["fields"]:
        val = (data.get(field_key) or "").strip()
        if val:
            creds[field_key] = val
    if not creds:
        return jsonify({"error": "Please enter your credentials."}), 400

    row = UserPaymentGateway.query.filter_by(user_id=current_user.id, gateway=gateway).first()
    if not row:
        row = UserPaymentGateway(user_id=current_user.id, gateway=gateway)
        db.session.add(row)
    row.mode = data.get("mode", "live")
    row.credentials_encrypted = encrypt_json(creds)
    primary_secret = creds.get("secret_key") or creds.get("client_secret") or ""
    row.last4 = mask_secret(primary_secret)[-8:] if primary_secret else None
    row.active = True
    row.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": f"{GATEWAY_FIELDS[gateway]['name']} connected.", "gateways": _serialize_gateway_status()})


@dashboard_bp.route("/payment-gateways/<gateway>/disconnect-json", methods=["POST"])
@require_any_premium("payment-link-generator", "funnel-builder")
def payment_gateways_disconnect_json(gateway):
    from app.models.platform import UserPaymentGateway
    row = UserPaymentGateway.query.filter_by(user_id=current_user.id, gateway=gateway).first()
    if row:
        db.session.delete(row)
        db.session.commit()
    return jsonify({"message": f"{GATEWAY_FIELDS.get(gateway, {}).get('name', gateway)} disconnected.", "gateways": _serialize_gateway_status()})



# ── Public Website Form Submissions ────────────────────────────────────

@dashboard_bp.route("/sites/submit-form/<subdomain>", methods=["POST"])
def site_submit_form(subdomain):
    from app.models.platform import UserWebsite
    # CSRF exemption registered at app-setup time in app/__init__.py —
    # see the comment there for why calling csrf.exempt() from inside
    # the view itself (as this used to) doesn't actually work.
    website = UserWebsite.query.filter_by(subdomain=subdomain).first_or_404()
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()
        
    if not data:
        return jsonify({"error": "No data submitted"}), 400
        
    settings = dict(website.settings or {})
    submissions = settings.get("submissions", [])
    data["submitted_at"] = datetime.utcnow().isoformat()
    submissions.append(data)
    settings["submissions"] = submissions
    website.settings = settings
    db.session.commit()
    return jsonify({"success": True, "message": "Submission recorded!"})


@dashboard_bp.route("/sites/submit-form-by-slug/<slug>", methods=["POST"])
def site_submit_form_by_slug(slug):
    """Same as site_submit_form() above, but keyed by `slug` (assigned the
    moment a site is first generated) instead of `subdomain` (only
    assigned on Publish). The Website Builder's auto-injected form-capture
    script (see _form_capture_snippet() in app/admin/routes.py) posts
    here, so submissions get captured while you're still previewing/
    editing a draft — not only after it's published. CSRF-exempted the
    same way as site_submit_form(), see app/__init__.py."""
    from app.models.platform import UserWebsite
    website = UserWebsite.query.filter_by(slug=slug).first_or_404()
    data = request.get_json(silent=True) or {}
    fields = data.get("fields")
    if not isinstance(fields, dict) or not fields:
        # Also accept a flat body for anything that doesn't wrap fields.
        fields = {k: v for k, v in data.items() if k not in ("page",)}
    if not fields:
        return jsonify({"error": "No data submitted"}), 400

    settings = dict(website.settings or {})
    submissions = list(settings.get("submissions") or [])
    entry = {str(k)[:80]: str(v)[:2000] for k, v in list(fields.items())[:30]}
    entry["submitted_at"] = datetime.utcnow().isoformat()
    if data.get("page"):
        entry["page"] = str(data.get("page"))[:100]
    submissions.insert(0, entry)
    submissions = submissions[:200]  # cap so a spammed form can't grow this unbounded
    settings["submissions"] = submissions
    website.settings = settings
    db.session.commit()
    return jsonify({"success": True, "message": "Submission recorded!"})


# ── Generic JSON collections ("mini backend") for generated sites ──────
# Only used when a site's own generated JS actually calls these — an
# AI-generated marketing/portfolio page never touches this, it's for
# sites that were actually asked to behave like an app: e-commerce
# (products/cart/orders), bookings, listings, etc. Each site gets its own
# isolated set of named collections (website.data_store), keyed by slug
# so it works pre-publish the same way form capture does.
#
# Deliberately public/no-login, same trust model as form-submit above:
# a static generated page's own JS is the only thing that can call these,
# and it has no session to authenticate with. That means these are NOT a
# secure real backend — anyone who finds the URL pattern could read or
# write a site's collections. Fine for prototyping a working cart/orders
# flow; not fine for anything actually sensitive. Capped hard (collection
# count, item count, item size) so it can't be used to store arbitrary
# large amounts of data or spammed into the ground.

_MAX_COLLECTIONS_PER_SITE = 20
_MAX_ITEMS_PER_COLLECTION = 500
_MAX_ITEM_BYTES = 20_000


def _get_website_by_slug_or_404(slug):
    from app.models.platform import UserWebsite
    return UserWebsite.query.filter_by(slug=slug).first_or_404()


def _item_size_ok(item):
    import json as _json
    try:
        return len(_json.dumps(item)) <= _MAX_ITEM_BYTES
    except (TypeError, ValueError):
        return False


@dashboard_bp.route("/sites/<slug>/data/<collection>", methods=["GET"])
def site_data_list(slug, collection):
    website = _get_website_by_slug_or_404(slug)
    store = website.data_store or {}
    items = store.get(collection, [])
    return jsonify({"items": items, "count": len(items)})


@dashboard_bp.route("/sites/<slug>/data/<collection>", methods=["POST"])
def site_data_create(slug, collection):
    import secrets as _secrets
    website = _get_website_by_slug_or_404(slug)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    if not _item_size_ok(body):
        return jsonify({"error": f"Item too large (max {_MAX_ITEM_BYTES} bytes)."}), 400

    store = dict(website.data_store or {})
    if collection not in store and len(store) >= _MAX_COLLECTIONS_PER_SITE:
        return jsonify({"error": f"This site already has the max of {_MAX_COLLECTIONS_PER_SITE} collections."}), 400
    items = list(store.get(collection, []))
    if len(items) >= _MAX_ITEMS_PER_COLLECTION:
        return jsonify({"error": f"'{collection}' is at its {_MAX_ITEMS_PER_COLLECTION}-item limit."}), 400

    item = dict(body)
    item["id"] = _secrets.token_hex(8)
    item["created_at"] = datetime.utcnow().isoformat()
    items.append(item)
    store[collection] = items
    website.data_store = store
    db.session.commit()
    return jsonify({"item": item}), 201


@dashboard_bp.route("/sites/<slug>/data/<collection>/<item_id>", methods=["GET"])
def site_data_get(slug, collection, item_id):
    website = _get_website_by_slug_or_404(slug)
    items = (website.data_store or {}).get(collection, [])
    item = next((i for i in items if i.get("id") == item_id), None)
    if not item:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"item": item})


@dashboard_bp.route("/sites/<slug>/data/<collection>/<item_id>", methods=["PUT", "PATCH"])
def site_data_update(slug, collection, item_id):
    website = _get_website_by_slug_or_404(slug)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    store = dict(website.data_store or {})
    items = list(store.get(collection, []))
    idx = next((i for i, it in enumerate(items) if it.get("id") == item_id), None)
    if idx is None:
        return jsonify({"error": "Not found"}), 404

    updated = dict(items[idx])
    updated.update({k: v for k, v in body.items() if k not in ("id", "created_at")})
    if not _item_size_ok(updated):
        return jsonify({"error": f"Item too large (max {_MAX_ITEM_BYTES} bytes)."}), 400
    updated["updated_at"] = datetime.utcnow().isoformat()
    items[idx] = updated
    store[collection] = items
    website.data_store = store
    db.session.commit()
    return jsonify({"item": updated})


@dashboard_bp.route("/sites/<slug>/data/<collection>/<item_id>", methods=["DELETE"])
def site_data_delete(slug, collection, item_id):
    website = _get_website_by_slug_or_404(slug)
    store = dict(website.data_store or {})
    items = list(store.get(collection, []))
    remaining = [i for i in items if i.get("id") != item_id]
    if len(remaining) == len(items):
        return jsonify({"error": "Not found"}), 404
    store[collection] = remaining
    website.data_store = store
    db.session.commit()
    return jsonify({"success": True})


# ── ZIP Downloader Endpoints ───────────────────────────────────────────
@dashboard_bp.route("/funnel-builder/<int:funnel_id>/download")
@login_required
@require_premium("funnel-builder")
def funnel_builder_download(funnel_id):
    """Static HTML export.

    Previously this zipped each page's raw `html_content` with nothing
    else — no Page Settings (SEO/custom scripts) applied, and crucially
    no nav script, so every `data-funnel-nav="next/accept/decline"`
    button in the download was a dead click (the live site only wires
    those up in serve_funnel() via _inject_page_extras). Opening the
    exported ZIP meant a funnel that looked complete but couldn't
    actually be clicked through. Now each page gets the same
    _inject_page_extras() treatment as the live site, with a nav script
    that points to the other pages' *local filenames* in this ZIP
    instead of live platform URLs — so the download is genuinely
    standalone and clickable start to finish, offline, no server needed
    (checkout pages still note they need to be hosted here for payment).
    """
    from app.models.platform import UserFunnel
    import io, zipfile, json as _json
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    pages = funnel.ordered_pages()

    filenames = {p.id: f"{i+1:02d}_{p.slug or p.page_type}.html" for i, p in enumerate(pages)}

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for p in pages:
            checkout = (p.settings or {}).get("checkout") if p.page_type == "checkout" else None
            if checkout:
                # Checkout pages are rendered dynamically (not stored as
                # static HTML) since they need live gateway wiring — the
                # ZIP gets a real preview of what buyers see, with a note
                # that the actual Pay buttons only work when hosted here.
                from app.utils.funnel_checkout import render_checkout_page_html
                from app.utils.funnel_blocks import render_blocks_body_html
                blocks_html = render_blocks_body_html(p.blocks, page_id=p.id) if p.blocks else ""
                html = render_checkout_page_html(p, checkout, [], "#not-functional-outside-bazillin-studio/", "", extra_content_html=blocks_html)
                html = html.replace(
                    "</body>",
                    "<p style='text-align:center;color:#a3a3a3;font-size:12px;margin-top:16px;'>"
                    "Note: this checkout's Pay buttons only work when hosted on Bazillin Studio, "
                    "where they use your connected payment gateway.</p></body>"
                )
            else:
                html = p.html_content or ""

            local_next = filenames.get(p.next_page_id)
            local_accept = filenames.get(p.branch_yes_id)
            local_decline = filenames.get(p.branch_no_id)
            nav_script = f"""
<script>
  window.FUNNEL_NEXT_URL = {_json.dumps(local_next)};
  window.FUNNEL_ACCEPT_URL = {_json.dumps(local_accept)};
  window.FUNNEL_DECLINE_URL = {_json.dumps(local_decline)};
  document.addEventListener('DOMContentLoaded', function () {{
    document.querySelectorAll('[data-funnel-nav]').forEach(function (el) {{
      var nav = el.getAttribute('data-funnel-nav');
      var url = nav === 'accept' ? window.FUNNEL_ACCEPT_URL
              : nav === 'decline' ? window.FUNNEL_DECLINE_URL
              : window.FUNNEL_NEXT_URL;
      if (url) el.addEventListener('click', function (e) {{ e.preventDefault(); window.location.href = url; }});
    }});
  }});
</script>"""
            html = _inject_page_extras(html, p, extra_script=nav_script)
            zipf.writestr(filenames[p.id], html)

        readme = (
            f"{funnel.title} — exported from Bazillin Studio\n\n"
            "Open the first numbered file in a browser to preview the funnel.\n"
            "Buttons between pages now link to the matching local file in this ZIP.\n\n"
            "Checkout page Pay buttons are preview-only in this export — payments require\n"
            "your connected gateway, which only runs when the funnel is hosted on Bazillin Studio\n"
            "or through the WordPress plugin export (Funnel Builder > Publish > WordPress Plugin).\n"
        )
        zipf.writestr("README.txt", readme)

    memory_file.seek(0)
    from flask import send_file
    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{funnel.slug or 'funnel'}_package.zip"
    )


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/wordpress-plugin.zip")
@login_required
@require_premium("funnel-builder")
def funnel_builder_wordpress_plugin(funnel_id):
    """A real, installable WordPress plugin for this funnel — same
    live-sync pattern already proven by the WhatsApp Widget plugin
    (see whatsapp_widget_plugin above): rather than baking a static
    snapshot in, activation creates one real WP page per funnel page,
    each holding a `[bazillin_funnel_page]` shortcode that fetches the
    current HTML from this platform on every request via
    funnel_page_embed() below. Edit the funnel here and the WordPress
    site reflects it immediately — no re-export needed.

    Licensing: a real FunnelLicenseKey row is minted on every download
    (so a re-downloaded/replaced install doesn't inherit an old key),
    embedded in the plugin, and sent as a query param on every embed
    request. funnel_page_embed() validates it and binds it to the
    requesting domain on first activation — a key issued for siteA.com
    is rejected on siteB.com even while the owner's account subscription
    is perfectly current. This is real per-install licensing, not just
    the account-level subscription check that used to be the only gate.
    """
    from app.models.platform import UserFunnel, FunnelLicenseKey
    import io, zipfile, re, secrets
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    pages = funnel.ordered_pages()
    if not pages:
        abort(400)

    license_key = FunnelLicenseKey(
        funnel_id=funnel.id, user_id=current_user.id,
        key=f"BZN-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}",
    )
    db.session.add(license_key)
    db.session.commit()

    plugin_slug = re.sub(r"[^a-z0-9]+", "-", (funnel.slug or funnel.title or "bazillin-funnel").lower()).strip("-") or "bazillin-funnel"
    embed_base = url_for("dashboard.funnel_page_embed", page_id=0, _external=True).rsplit("/0", 1)[0]

    pages_php_array = ",\n".join(
        "        array('id' => %d, 'title' => %s, 'slug' => %s, 'order' => %d)" % (
            p.id, _php_str(p.title or p.page_type), _php_str(p.slug or f"page-{p.id}"), i
        )
        for i, p in enumerate(pages)
    )

    php = f"""<?php
/**
 * Plugin Name: {funnel.title} — Bazillin Funnel
 * Description: Imports the "{funnel.title}" sales funnel as real WordPress pages, live-synced with your Bazillin Studio dashboard. Edit content, blocks, or design in Bazillin Studio and this site updates automatically — no re-export needed.
 * Version: 1.0.0
 */
if (!defined('ABSPATH')) exit;

define('BZN_FUNNEL_EMBED_BASE', '{embed_base}/');
define('BZN_FUNNEL_ID', {funnel.id});
define('BZN_LICENSE_KEY', {_php_str(license_key.key)});

$bzn_funnel_pages = array(
{pages_php_array}
);

// ── Activation: create one real, editable-title WP page per funnel page ──
function bzn_funnel_activate() {{
    global $bzn_funnel_pages;
    $created = get_option('bzn_funnel_page_map_{funnel.id}', array());
    foreach ($bzn_funnel_pages as $fp) {{
        if (isset($created[$fp['id']])) {{
            $existing = get_post($created[$fp['id']]);
            if ($existing && $existing->post_status !== 'trash') continue;
        }}
        $post_id = wp_insert_post(array(
            'post_title'   => $fp['title'],
            'post_name'    => $fp['slug'],
            'post_content' => '[bazillin_funnel_page id="' . intval($fp['id']) . '"]',
            'post_status'  => 'publish',
            'post_type'    => 'page',
            'menu_order'   => $fp['order'],
        ));
        if ($post_id && !is_wp_error($post_id)) {{
            $created[$fp['id']] = $post_id;
        }}
    }}
    update_option('bzn_funnel_page_map_{funnel.id}', $created);
}}
register_activation_hook(__FILE__, 'bzn_funnel_activate');

// ── Shortcode: live-fetches this page's current HTML, license-checked
// and domain-bound, from Bazillin Studio on every request ──
function bzn_funnel_page_shortcode($atts) {{
    $atts = shortcode_atts(array('id' => 0), $atts);
    $page_id = intval($atts['id']);
    if (!$page_id) return '';
    $url = add_query_arg(array(
        'key' => BZN_LICENSE_KEY,
        'domain' => parse_url(home_url(), PHP_URL_HOST),
    ), BZN_FUNNEL_EMBED_BASE . $page_id);
    $response = wp_remote_get($url, array('timeout' => 8));
    if (is_wp_error($response) || wp_remote_retrieve_response_code($response) !== 200) {{
        return '<p style="text-align:center;color:#999;padding:40px;">This page is temporarily unavailable. It will resync automatically.</p>';
    }}
    return wp_remote_retrieve_body($response);
}}
add_shortcode('bazillin_funnel_page', 'bzn_funnel_page_shortcode');

// The shortcode returns a full standalone HTML fragment (already styled) —
// tell WP not to run it through wpautop, which would mangle the markup.
remove_filter('the_content', 'wpautop');
"""

    readme = f"""=== {funnel.title} — Bazillin Funnel ===
Generated by Bazillin Studio.
License Key: {license_key.key}

INSTALLATION
1. Upload this folder to /wp-content/plugins/
2. Activate it under Plugins in your WordPress admin.
3. Real WordPress pages are created automatically for every page in this
   funnel: {", ".join(p.title or p.page_type for p in pages)}

LIVE SYNC
This plugin does not contain a snapshot of your funnel — each page fetches
its current content from your Bazillin Studio dashboard on every request.
Edit copy, blocks, design, or add/remove pages in the Funnel Builder and
your WordPress site updates automatically. No re-download or reinstall.

APPEARANCE
Pages render using the exact same HTML/CSS as the Funnel Builder preview
(Tailwind utility classes, same block renderer) — what you see in the
builder is what ships to WordPress, not an approximation. The one thing
that can differ visually is your WordPress theme itself: if your theme
injects its own global CSS resets or its own header/footer chrome around
page content, that can interact with the funnel content. wp_autop (which
would otherwise mangle the markup by wrapping every line in stray <p>
tags) is explicitly disabled for these pages.

LICENSING
This install's license key is bound to the first domain that activates
it. Moving the funnel to a different domain requires downloading a fresh
plugin ZIP (Funnel Builder > Publish > WordPress Plugin) — this prevents
one export being reused across unrelated sites. See and revoke active
license keys for this funnel from the Publish tab in the builder.

SUBSCRIPTION
This funnel stays live on your WordPress site as long as your Sales Funnel
Builder subscription on Bazillin Studio is active. If it lapses, pages keep
working but show a small renewal notice until you renew — your site is
never taken down.
"""

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{plugin_slug}/{plugin_slug}.php", php)
        zf.writestr(f"{plugin_slug}/readme.txt", readme)
    buf.seek(0)
    from flask import send_file
    return send_file(buf, mimetype="application/zip", as_attachment=True, download_name=f"{plugin_slug}.zip")


def _php_str(value):
    """Render a Python string as a single-quoted PHP string literal."""
    return "'" + str(value or "").replace("\\", "\\\\").replace("'", "\\'") + "'"


@dashboard_bp.route("/funnel-builder/<int:funnel_id>/license-keys")
@require_premium("funnel-builder")
def funnel_builder_license_keys(funnel_id):
    """List license keys issued for this funnel's WordPress exports, so
    an owner can see which domains are actually running it and revoke
    one without having to touch WordPress itself."""
    from app.models.platform import UserFunnel, FunnelLicenseKey
    funnel = UserFunnel.query.filter_by(id=funnel_id, user_id=current_user.id).first_or_404()
    keys = FunnelLicenseKey.query.filter_by(funnel_id=funnel.id).order_by(FunnelLicenseKey.created_at.desc()).all()
    return jsonify([{
        "id": k.id, "key": k.key, "domain": k.domain, "status": k.status,
        "created_at": k.created_at.isoformat() if k.created_at else None,
        "activated_at": k.activated_at.isoformat() if k.activated_at else None,
        "last_checked_at": k.last_checked_at.isoformat() if k.last_checked_at else None,
        "check_count": k.check_count,
    } for k in keys])


@dashboard_bp.route("/funnel-builder/license-keys/<int:key_id>/revoke", methods=["POST"])
@require_premium("funnel-builder")
def funnel_builder_revoke_license_key(key_id):
    from app.models.platform import FunnelLicenseKey
    key = FunnelLicenseKey.query.filter_by(id=key_id, user_id=current_user.id).first_or_404()
    key.status = "revoked"
    db.session.commit()
    return jsonify({"ok": True})


@dashboard_bp.route("/funnel-builder/embed/page/<int:page_id>")
def funnel_page_embed(page_id):
    """Public, unauthenticated endpoint the WordPress plugin's shortcode
    fetches on every page load (see funnel_builder_wordpress_plugin
    above) — this is what makes the exported plugin "live-synced"
    instead of a static snapshot, same pattern as the WhatsApp Widget's
    embed.js. Explicitly no-cached.

    Two independent checks gate the live content, in order:
    1. License key: must exist, belong to this funnel, not be revoked,
       and be bound to (or activating on) the requesting domain — a
       key activated on siteA.com is rejected on siteB.com even if the
       key itself is valid. Requests with no key (e.g. someone hitting
       this URL directly, or a plugin built before this feature) fall
       back to account-level access below rather than being hard-
       rejected, so this stays backward compatible.
    2. Subscription state via has_product_access() — if the owner's
       Sales Funnel Builder access has lapsed, the WordPress site keeps
       rendering, never breaks, but gets a renewal notice instead of
       the live page content.
    """
    from app.models.platform import UserFunnel, FunnelPage, FunnelLicenseKey
    from app.dashboard.premium import has_product_access
    page = FunnelPage.query.get_or_404(page_id)
    funnel = UserFunnel.query.get_or_404(page.funnel_id)

    key_value = request.args.get("key")
    domain = (request.args.get("domain") or "").lower().strip()
    if key_value:
        license_key = FunnelLicenseKey.query.filter_by(key=key_value, funnel_id=funnel.id).first()
        if not license_key or license_key.status == "revoked":
            resp = make_response(_funnel_license_notice("This license key is no longer valid.", None))
            resp.headers["Content-Type"] = "text/html"
            resp.headers["Cache-Control"] = "no-store"
            return resp
        if not license_key.domain and domain:
            license_key.domain = domain
            license_key.activated_at = datetime.utcnow()
        elif license_key.domain and domain and license_key.domain != domain:
            resp = make_response(_funnel_license_notice("This license key is already active on a different domain.", None))
            resp.headers["Content-Type"] = "text/html"
            resp.headers["Cache-Control"] = "no-store"
            return resp
        license_key.last_checked_at = datetime.utcnow()
        license_key.check_count = (license_key.check_count or 0) + 1
        db.session.commit()

    if not has_product_access(funnel.user, "funnel-builder"):
        renewal_url = url_for("marketplace.product_detail", slug="funnel-builder", _external=True)
        resp = make_response(_funnel_license_notice(
            "The Sales Funnel Builder subscription behind this page has expired.", renewal_url))
        resp.headers["Content-Type"] = "text/html"
        resp.headers["Cache-Control"] = "no-store"
        return resp

    checkout = (page.settings or {}).get("checkout") if page.page_type == "checkout" else None
    if checkout:
        from app.utils.funnel_checkout import render_checkout_page_html
        from app.utils.funnel_blocks import render_blocks_body_html
        blocks_html = render_blocks_body_html(page.blocks, page_id=page.id) if page.blocks else ""
        html = render_checkout_page_html(page, checkout, [], "#not-functional-outside-bazillin-studio/", "", extra_content_html=blocks_html)
    else:
        html = page.html_content or ""

    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html"
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _funnel_license_notice(message, renewal_url):
    button = (
        f'<a href="{_html_escape(renewal_url)}" style="display:inline-block;padding:12px 28px;background:#111;'
        f'color:#fff;border-radius:9999px;text-decoration:none;font-weight:700;">Renew Subscription</a>'
    ) if renewal_url else ""
    return f"""<div style="max-width:640px;margin:60px auto;padding:32px;text-align:center;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
        border:1px solid #eee;border-radius:16px;">
        <p style="font-weight:700;font-size:18px;margin-bottom:8px;">This page is paused</p>
        <p style="color:#666;margin-bottom:20px;">{_html_escape(message)}</p>
        {button}
    </div>"""




# ── Page Listing endpoints ─────────────────────────────────────────────



@dashboard_bp.route("/chatbot-builder")
@require_premium("whatsapp-bot")
def chatbot_builder():
    """WhatsApp Bot / Chatbot Builder workspace. Deliberately excludes
    platform == "ai-agent" — AI Chatbot's agent is created and managed
    on its own separate page (dashboard.ai_chatbot). Before this filter,
    a user's AI Chatbot agent showed up as a selectable "bot" in THIS
    tool's list too (and its conversation history right along with it),
    which is exactly the cross-contamination the two tools were meant
    to never have."""
    from app.models.platform import UserChatbot
    bots = UserChatbot.query.filter(
        UserChatbot.user_id == current_user.id,
        UserChatbot.platform != "ai-agent",
    ).order_by(UserChatbot.created_at.desc()).all()
    webhook_urls = {b.id: url_for("telephony.twilio_whatsapp_webhook_per_bot", bot_id=b.id, _external=True) for b in bots}
    return render_template("dashboard/chatbot_builder.html", bots=bots, webhook_urls=webhook_urls)



@dashboard_bp.route("/chatbot-builder/save", methods=["POST"])
@require_premium("whatsapp-bot")
def chatbot_builder_save():
    """Save a chatbot configuration."""
    from app.models.platform import UserChatbot
    data = request.get_json(silent=True) or {}
    bot_id = data.get("id")

    if bot_id:
        bot = UserChatbot.query.filter_by(id=bot_id, user_id=current_user.id).first()
        if not bot:
            return jsonify({"error": "Bot not found."}), 404
    else:
        bot = UserChatbot(user_id=current_user.id, name=data.get("name", "My Bot"))
        db.session.add(bot)

    bot.name = data.get("name", bot.name)
    bot.platform = data.get("platform", "whatsapp")
    bot.greeting = data.get("greeting", "")
    bot.flows = data.get("flows", [])
    bot.keywords = data.get("keywords", [])
    bot.auto_replies = data.get("auto_replies", [])
    bot.ai_enabled = data.get("ai_enabled", False)
    bot.ai_instructions = data.get("ai_instructions", "")
    bot.faqs = data.get("faqs", [])
    bot.knowledge_text = data.get("knowledge_text", "")
    bot.unknown_reply = data.get("unknown_reply", "")
    bot.display_phone = (data.get("phone") or "").strip() or None
    bot.active = data.get("active", True)
    bot.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"id": bot.id, "message": "Bot saved."})



@dashboard_bp.route("/chatbot-builder/<int:bot_id>/delete", methods=["POST"])
@require_premium("whatsapp-bot")
def chatbot_builder_delete(bot_id):
    """Delete a chatbot."""
    from app.models.platform import UserChatbot
    bot = UserChatbot.query.filter_by(id=bot_id, user_id=current_user.id).first_or_404()
    db.session.delete(bot)
    db.session.commit()
    return jsonify({"message": "Bot deleted."})


@dashboard_bp.route("/chatbot-builder/<int:bot_id>/connect-whatsapp", methods=["POST"])
@require_premium("whatsapp-bot")
def chatbot_builder_connect_whatsapp(bot_id):
    """Connect THIS bot to the customer's own Twilio WhatsApp sender —
    separate from the site-wide Admin -> Settings -> Twilio config, which
    only ever answers with the platform owner's single agent. Credentials
    are stored Fernet-encrypted (see UserChatbot.set_whatsapp_credentials)
    and never echoed back in plaintext. Verifies the credentials against
    Twilio's own API before saving, so a mistyped SID/token is caught
    immediately (Doc 13's 'Test Connection' requirement) instead of only
    surfacing on the first missed real customer message."""
    from app.models.platform import UserChatbot
    from app.utils.twilio_integration import test_twilio_credentials
    bot = UserChatbot.query.filter_by(id=bot_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    account_sid = (data.get("account_sid") or "").strip()
    auth_token = (data.get("auth_token") or "").strip()
    whatsapp_number = (data.get("whatsapp_number") or "").strip()
    if not account_sid or not auth_token or not whatsapp_number:
        return jsonify({"error": "Account SID, Auth Token, and WhatsApp number are all required."}), 400

    ok, message = test_twilio_credentials(account_sid, auth_token)
    if not ok:
        return jsonify({"error": message}), 400

    bot.set_whatsapp_credentials(account_sid, auth_token, whatsapp_number)
    bot.updated_at = datetime.utcnow()
    db.session.commit()
    webhook_url = url_for("telephony.twilio_whatsapp_webhook_per_bot", bot_id=bot.id, _external=True)
    return jsonify({"success": True, "webhook_url": webhook_url})


@dashboard_bp.route("/chatbot-builder/<int:bot_id>/test-whatsapp", methods=["POST"])
@require_premium("whatsapp-bot")
def chatbot_builder_test_whatsapp(bot_id):
    """Re-verify the currently-connected Twilio credentials against
    Twilio's own API — for checking a connection still works after, say,
    rotating an Auth Token in the Twilio Console."""
    from app.models.platform import UserChatbot
    from app.utils.twilio_integration import test_twilio_credentials
    bot = UserChatbot.query.filter_by(id=bot_id, user_id=current_user.id).first_or_404()
    if not bot.whatsapp_connected:
        return jsonify({"error": "WhatsApp isn't connected yet."}), 400
    creds = bot.get_whatsapp_credentials()
    ok, message = test_twilio_credentials(creds.get("account_sid"), creds.get("auth_token"))
    if not ok:
        return jsonify({"error": message, "connected": False}), 400
    return jsonify({"success": True, "connected": True, "message": message})


@dashboard_bp.route("/chatbot-builder/<int:bot_id>/disconnect-whatsapp", methods=["POST"])
@require_premium("whatsapp-bot")
def chatbot_builder_disconnect_whatsapp(bot_id):
    from app.models.platform import UserChatbot
    bot = UserChatbot.query.filter_by(id=bot_id, user_id=current_user.id).first_or_404()
    bot.whatsapp_credentials_encrypted = None
    db.session.commit()
    return jsonify({"success": True})


# ── Knowledge Sources: website pages + uploaded documents ─────────────
# Shared by BOTH the WhatsApp Bot builder and the AI Chatbot page — one
# canonical set of endpoints, gated only by "you own this UserChatbot
# row" rather than a specific product slug, since a bot's platform
# already tells you which product unlocked it. Doc 9 §5's "Website" and
# "Documents" knowledge sources, previously entirely unbuilt — only
# manual FAQ/business-info text existed (batch 71).

def _owned_bot_or_404(bot_id):
    from app.models.platform import UserChatbot
    return UserChatbot.query.filter_by(id=bot_id, user_id=current_user.id).first_or_404()


@dashboard_bp.route("/chatbot-knowledge/<int:bot_id>/add-url", methods=["POST"])
def chatbot_knowledge_add_url(bot_id):
    bot = _owned_bot_or_404(bot_id)
    from app.utils.knowledge import fetch_url_text
    import uuid, datetime as _dt
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Enter a URL."}), 400

    title, text, err = fetch_url_text(url)
    if err:
        return jsonify({"error": err}), 400

    sources = list(bot.knowledge_sources or [])
    sources.append({
        "id": uuid.uuid4().hex[:12], "type": "url", "title": title, "source": url,
        "text": text, "added_at": _dt.datetime.utcnow().isoformat(),
    })
    bot.knowledge_sources = sources
    db.session.commit()
    return jsonify({"sources": [{k: v for k, v in s.items() if k != "text"} for s in sources]})


@dashboard_bp.route("/chatbot-knowledge/<int:bot_id>/add-file", methods=["POST"])
def chatbot_knowledge_add_file(bot_id):
    bot = _owned_bot_or_404(bot_id)
    from app.utils.knowledge import extract_text_from_upload
    import uuid, datetime as _dt
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file selected."}), 400

    text, err = extract_text_from_upload(file)
    if err:
        return jsonify({"error": err}), 400

    sources = list(bot.knowledge_sources or [])
    sources.append({
        "id": uuid.uuid4().hex[:12], "type": "file", "title": file.filename, "source": file.filename,
        "text": text, "added_at": _dt.datetime.utcnow().isoformat(),
    })
    bot.knowledge_sources = sources
    db.session.commit()
    return jsonify({"sources": [{k: v for k, v in s.items() if k != "text"} for s in sources]})


@dashboard_bp.route("/chatbot-knowledge/<int:bot_id>/remove/<source_id>", methods=["POST"])
def chatbot_knowledge_remove_source(bot_id, source_id):
    bot = _owned_bot_or_404(bot_id)
    sources = [s for s in (bot.knowledge_sources or []) if s.get("id") != source_id]
    bot.knowledge_sources = sources
    db.session.commit()
    return jsonify({"sources": [{k: v for k, v in s.items() if k != "text"} for s in sources]})


@dashboard_bp.route("/chatbot-knowledge/<int:bot_id>/sources", methods=["GET"])
def chatbot_knowledge_list_sources(bot_id):
    bot = _owned_bot_or_404(bot_id)
    sources = bot.knowledge_sources or []
    return jsonify({"sources": [{k: v for k, v in s.items() if k != "text"} for s in sources]})


# ── Widget appearance: logo, position, color, icon, animation, labels —
# shared by WhatsApp Bot's Web Widget deployment AND AI Chatbot, since
# both render through the exact same bubble (app.utils.chat_widget) and
# both are just UserChatbot rows. One set of endpoints, gated only by
# ownership (same pattern as the knowledge-source endpoints above). ──

@dashboard_bp.route("/chatbot/<int:bot_id>/upload-logo", methods=["POST"])
def chatbot_upload_logo(bot_id):
    bot = _owned_bot_or_404(bot_id)
    from app.utils.media_storage import save_upload
    file = request.files.get("logo")
    if not file or not file.filename:
        return jsonify({"error": "No file selected."}), 400
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in {"png", "jpg", "jpeg", "gif", "webp", "svg"}:
        return jsonify({"error": "Please upload an image file (PNG, JPG, WEBP, SVG)."}), 400
    try:
        url, filename, size = save_upload(file, "chatbot-logos", current_app)
    except Exception as e:
        return jsonify({"error": f"Upload failed: {e}"}), 500
    bot.logo_url = url
    db.session.commit()
    return jsonify({"url": url})


@dashboard_bp.route("/chatbot/<int:bot_id>/widget-settings", methods=["GET", "POST"])
def chatbot_widget_settings(bot_id):
    bot = _owned_bot_or_404(bot_id)
    if request.method == "GET":
        from app.utils.chat_widget import widget_config
        return jsonify(widget_config(bot))

    data = request.get_json(silent=True) or {}
    allowed = {"position", "button_color", "icon", "animation", "show_label",
               "button_text", "desktop_visible", "mobile_visible", "show_branding",
               "ai_reply_limit"}
    settings = dict(bot.widget_settings or {})
    for key in allowed:
        if key in data:
            settings[key] = data[key]
    bot.widget_settings = settings
    db.session.commit()
    from app.utils.chat_widget import widget_config
    return jsonify(widget_config(bot))


# ── Conversation history — shared table (UserChatbotMessage), but each
# endpoint only ever queries the CURRENT user's own bots, so WhatsApp
# Bot's history page and AI Chatbot's history page are naturally
# distinct even though they're powered by the same underlying log. ──

@dashboard_bp.route("/chatbot/<int:bot_id>/conversations")
def chatbot_conversation_list(bot_id):
    """One row per distinct visitor session for this bot — most
    recently active first — with a preview of the last message."""
    bot = _owned_bot_or_404(bot_id)
    from app.models.platform import UserChatbotMessage
    from sqlalchemy import func

    rows = (
        db.session.query(
            UserChatbotMessage.session_id,
            func.max(UserChatbotMessage.created_at).label("last_at"),
            func.count(UserChatbotMessage.id).label("message_count"),
        )
        .filter(UserChatbotMessage.bot_id == bot.id)
        .group_by(UserChatbotMessage.session_id)
        .order_by(func.max(UserChatbotMessage.created_at).desc())
        .limit(100)
        .all()
    )
    conversations = []
    for session_id, last_at, message_count in rows:
        last_msg = (UserChatbotMessage.query
                    .filter_by(bot_id=bot.id, session_id=session_id)
                    .order_by(UserChatbotMessage.created_at.desc()).first())
        conversations.append({
            "session_id": session_id,
            "last_at": last_at.isoformat() if last_at else None,
            "message_count": message_count,
            "last_message": (last_msg.text[:120] if last_msg else ""),
            "last_sender": last_msg.sender if last_msg else None,
        })
    return jsonify({"conversations": conversations})


@dashboard_bp.route("/chatbot/<int:bot_id>/conversations/<session_id>")
def chatbot_conversation_detail(bot_id, session_id):
    """Full transcript for one visitor session."""
    bot = _owned_bot_or_404(bot_id)
    from app.models.platform import UserChatbotMessage
    msgs = (UserChatbotMessage.query
            .filter_by(bot_id=bot.id, session_id=session_id)
            .order_by(UserChatbotMessage.created_at.asc()).all())
    return jsonify({"messages": [
        {"sender": m.sender, "text": m.text, "source": m.source,
         "created_at": m.created_at.isoformat() if m.created_at else None}
        for m in msgs
    ]})


@dashboard_bp.route("/chatbot/<int:bot_id>/analytics")
def chatbot_analytics(bot_id):
    """Real analytics computed from UserChatbotMessage — same server-
    rendered-bar-chart convention already used by Payment Link/Funnel
    Analytics elsewhere in this app (no new charting library), so this
    fits the existing visual language instead of introducing a one-off
    pattern. Shared by WhatsApp Bot and AI Chatbot; each only ever
    queries its own bot's messages, same as the History endpoints."""
    bot = _owned_bot_or_404(bot_id)
    from app.models.platform import UserChatbotMessage
    from sqlalchemy import func
    import datetime as _dt

    total_messages = UserChatbotMessage.query.filter_by(bot_id=bot.id).count()
    total_conversations = (db.session.query(func.count(func.distinct(UserChatbotMessage.session_id)))
                            .filter(UserChatbotMessage.bot_id == bot.id).scalar()) or 0

    source_rows = (db.session.query(UserChatbotMessage.source, func.count(UserChatbotMessage.id))
                   .filter(UserChatbotMessage.bot_id == bot.id, UserChatbotMessage.sender == "bot")
                   .group_by(UserChatbotMessage.source).all())
    source_counts = {src or "other": cnt for src, cnt in source_rows}
    total_bot_replies = sum(source_counts.values())
    source_breakdown = [
        {"label": label, "count": source_counts.get(key, 0),
         "pct": round((source_counts.get(key, 0) / total_bot_replies) * 100, 1) if total_bot_replies else 0}
        for key, label in [("keyword", "Keyword Rules"), ("ai", "AI"), ("handoff", "WhatsApp Handoff"), ("fallback", "Fallback")]
        if source_counts.get(key, 0) > 0
    ]

    today = _dt.date.today()
    days = [today - _dt.timedelta(days=i) for i in range(13, -1, -1)]
    daily_rows = (db.session.query(func.date(UserChatbotMessage.created_at), func.count(UserChatbotMessage.id))
                  .filter(UserChatbotMessage.bot_id == bot.id,
                          UserChatbotMessage.created_at >= _dt.datetime.combine(days[0], _dt.time.min))
                  .group_by(func.date(UserChatbotMessage.created_at)).all())
    daily_map = {}
    for d, cnt in daily_rows:
        key = d.isoformat() if hasattr(d, "isoformat") else str(d)[:10]
        daily_map[key] = cnt
    trend = [{"label": d.strftime("%m/%d"), "value": daily_map.get(d.isoformat(), 0)} for d in days]
    max_val = max((t["value"] for t in trend), default=0)
    for t in trend:
        t["pct"] = round((t["value"] / max_val) * 100, 1) if max_val else 0

    return jsonify({
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "source_breakdown": source_breakdown,
        "trend": trend,
    })


@dashboard_bp.route("/chatbot/<int:bot_id>/plugin.zip")
def chatbot_wordpress_plugin(bot_id):
    """A real, live-synced WordPress plugin — same pattern as the
    WhatsApp Widget's plugin (whatsapp_widget_plugin below): it enqueues
    the SAME live embed script every other surface already uses
    (admin.chatbot_widget_js, which reads the bot's config fresh on
    every request), so editing appearance/knowledge/instructions in the
    dashboard shows up on the WordPress site automatically — no
    re-download or reinstall needed. Works identically for WhatsApp
    Bot's Web Widget deployment and AI Chatbot, since both are the same
    embeddable bubble under the hood."""
    bot = _owned_bot_or_404(bot_id)
    import io, zipfile, re
    slug = re.sub(r"[^a-z0-9]+", "-", (bot.name or "chatbot").lower()).strip("-") or "chatbot"
    embed_url = url_for("admin.chatbot_widget_js", bot_id=bot.id, _external=True)
    product_label = "AI Chatbot" if bot.platform == "ai-agent" else "WhatsApp Bot"
    php = f"""<?php
/**
 * Plugin Name: {bot.name} — {product_label}
 * Description: Adds your {product_label} chat widget to every page, live-synced with your Bazillin Studio dashboard — edit the bot there and it updates here automatically, no re-download needed.
 * Version: 1.0.0
 */
if (!defined('ABSPATH')) exit;

function bzn_chatbot_{bot.id}_enqueue() {{
    wp_enqueue_script('bzn-chatbot-{bot.id}', '{embed_url}', array(), '1.0.0', true);
}}
add_action('wp_enqueue_scripts', 'bzn_chatbot_{bot.id}_enqueue');
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}/{slug}.php", php)
        zf.writestr(f"{slug}/readme.txt",
            f"=== {bot.name} — {product_label} ===\nGenerated by Bazillin Studio.\n\n"
            "Installation:\n1. Upload this folder to /wp-content/plugins/\n"
            "2. Activate it under Plugins in your WordPress admin.\n"
            "3. The chat widget appears automatically on every page.\n\n"
            "This plugin stays LIVE-SYNCED with your dashboard — change the "
            "appearance, knowledge base, or anything else in your Bazillin Studio "
            "dashboard and it updates on your WordPress site automatically, no "
            "re-download or reinstall needed.\n")
    buf.seek(0)
    from flask import send_file
    return send_file(buf, mimetype="application/zip", as_attachment=True, download_name=f"{slug}.zip")


@dashboard_bp.route("/chatbot-builder/test", methods=["POST"])
@require_premium("whatsapp-bot")
def chatbot_builder_test():
    """Test chatbot AI reply. Uses the exact same grounded-reply path as
    the live public endpoint (app.utils.knowledge.generate_bot_reply), so
    what you see in the test panel — including Knowledge Base answers —
    matches what a real customer gets. Accepts faqs/knowledge_text
    in-line from the current (possibly unsaved) editor state, so you can
    test changes before saving. Ingested website/document sources are
    pulled from the saved bot itself (id, if the bot has been saved) —
    those require a real fetch/upload so they can't be "unsaved".
    """
    from app.utils.knowledge import generate_bot_reply
    from app.models.platform import UserChatbot
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    instructions = data.get("instructions", "You are a helpful business chatbot.")
    faqs = data.get("faqs", [])
    knowledge_text = data.get("knowledge_text", "")
    unknown_reply = data.get("unknown_reply", "")
    if not message:
        return jsonify({"error": "Enter a test message."}), 400

    sources = []
    bot_id = data.get("bot_id")
    if bot_id:
        bot = UserChatbot.query.filter_by(id=bot_id, user_id=current_user.id).first()
        if bot:
            sources = bot.knowledge_sources or []

    reply, err = generate_bot_reply(instructions, faqs, knowledge_text, message, unknown_reply=unknown_reply, sources=sources, charge_user_id=current_user.id)
    if err:
        return jsonify({"reply": f"Error: {err}"})
    return jsonify({"reply": reply or "Sorry, I couldn't generate a response."})


# ══════════════════════════════════════════════════════════════════════
#  AUTOMATION STUDIO (User-facing)
# ══════════════════════════════════════════════════════════════════════


@dashboard_bp.route("/chatbot/embed/<int:bot_id>")
def chatbot_embed(bot_id):
    """Serve a public standalone chatbot page — this doubles as "the
    standalone link" a business can share directly (not just embed),
    now branded with the bot's own configured logo/color instead of the
    fixed default look."""
    from app.models.platform import UserChatbot
    from app.utils.chat_widget import widget_config
    bot = UserChatbot.query.filter_by(id=bot_id, active=True).first_or_404()
    brand_color = widget_config(bot)["button_color"]
    return render_template("dashboard/chatbot_embed.html", bot=bot, brand_color=brand_color)


# ══════════════════════════════════════════════════════════════════════
#  AI CHATBOT (user-facing) — self-serve: the customer creates and owns
#  their own agent instantly, the same way WhatsApp Bot already works,
#  metered by AI Credits (Doc 9 §2/§20-22). Admin can still hand-build or
#  reconfigure an agent for a customer who wants white-glove setup (see
#  admin.ai_chatbot_agents_create) — that path is now an OPTION on top of
#  self-serve, not the only way to get an agent.
#  Distinct from WhatsApp Bot (dashboard.chatbot_builder) — the two must
#  never point at the same page/endpoint.
# ══════════════════════════════════════════════════════════════════════

AI_CHATBOT_PERSONALITIES = {
    "professional": "Be professional, precise, and businesslike in every reply.",
    "friendly": "Be warm, friendly, and conversational — like a helpful teammate.",
    "casual": "Be casual and relaxed in tone, like chatting with a friend.",
    "formal": "Be formal and courteous — measured language, no slang.",
    "sales": "Be an enthusiastic, persuasive sales assistant — highlight value and gently guide toward a purchase.",
    "support": "Be a calm, patient, solutions-focused customer support agent.",
}


@dashboard_bp.route("/ai-chatbot")
@require_premium("ai-chatbot")
def ai_chatbot():
    """AI Chatbot workspace. Purchasing unlocks this page immediately.
    If no agent exists yet, shows a real self-serve creation form
    instead of a 'we'll reach out' waiting state — the customer can
    build their own agent right now, same as WhatsApp Bot already
    works, metered by AI Credits."""
    from app.models.platform import UserChatbot
    from app.utils.credits import get_balance
    agent = (UserChatbot.query.filter_by(user_id=current_user.id, platform="ai-agent")
             .order_by(UserChatbot.created_at.desc()).first())
    credit_balance = get_balance(current_user.id)
    return render_template("dashboard/ai_chatbot.html", agent=agent, credit_balance=credit_balance,
                            personalities=AI_CHATBOT_PERSONALITIES)


@dashboard_bp.route("/ai-chatbot/create", methods=["POST"])
@require_premium("ai-chatbot")
def ai_chatbot_create():
    """Self-serve agent creation — the customer builds their own AI
    Agent instantly instead of waiting on an admin. Refuses to create a
    second agent for the same user (one agent per account today, same
    as WhatsApp Bot's per-bot model but simpler — matches what the
    dashboard page renders)."""
    from app.models.platform import UserChatbot
    existing = UserChatbot.query.filter_by(user_id=current_user.id, platform="ai-agent").first()
    if existing:
        return jsonify({"error": "You already have an AI Agent — edit it below instead of creating a new one."}), 400

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    business_name = (data.get("business_name") or "").strip()
    if not name:
        return jsonify({"error": "Give your agent a name."}), 400

    personality_key = data.get("personality") if data.get("personality") in AI_CHATBOT_PERSONALITIES else "friendly"
    personality_instruction = AI_CHATBOT_PERSONALITIES[personality_key]
    business_line = f" for {business_name}" if business_name else ""
    instructions = (
        f"You are the AI customer support assistant{business_line}. {personality_instruction} "
        "If you don't know something, say so clearly rather than guessing or inventing prices, "
        "products, or policies."
    )

    agent = UserChatbot(
        user_id=current_user.id, platform="ai-agent", name=name[:128],
        greeting=(data.get("greeting") or "Hi! How can I help you today?").strip(),
        ai_instructions=instructions, ai_enabled=True, active=True,
        unknown_reply="Sorry, I don't have that information. Please contact our support team.",
    )
    db.session.add(agent)
    db.session.commit()
    return jsonify({"message": "Your AI Agent is ready.", "id": agent.id})


@dashboard_bp.route("/ai-chatbot/save", methods=["POST"])
@require_premium("ai-chatbot")
def ai_chatbot_save():
    """Let the customer edit their agent's name, greeting, instructions,
    knowledge base (FAQs + manual business info), and active state once
    the admin has set it up. Does not create a new agent — creation is
    an admin action after the manual build/setup contact described at
    purchase time. Previously this had NO knowledge base at all — the
    agent could only be steered via a raw prompt, with no structured way
    to tell it about the business's own FAQs/policies/pricing (Doc 9's
    core ask), even though WhatsApp Bot's `generate_bot_reply` retrieval
    path already existed and just wasn't reachable from this form."""
    from app.models.platform import UserChatbot
    import json as _json
    agent = (UserChatbot.query.filter_by(user_id=current_user.id, platform="ai-agent")
             .order_by(UserChatbot.created_at.desc()).first())
    if not agent:
        flash("Your AI Agent hasn't been set up yet — we'll reach out once it's ready.", "info")
        return redirect(url_for("dashboard.ai_chatbot"))
    agent.name = request.form.get("name", agent.name)[:128]
    agent.greeting = request.form.get("greeting", agent.greeting)
    agent.ai_instructions = request.form.get("ai_instructions", agent.ai_instructions)
    agent.knowledge_text = request.form.get("knowledge_text", agent.knowledge_text)
    agent.unknown_reply = request.form.get("unknown_reply", agent.unknown_reply)
    try:
        agent.faqs = _json.loads(request.form.get("faqs_json") or "[]")
    except (ValueError, TypeError):
        pass  # leave existing FAQs untouched if the client sent malformed JSON
    agent.active = request.form.get("active") == "on"
    agent.updated_at = datetime.utcnow()
    db.session.commit()
    flash("AI Agent updated.", "success")
    return redirect(url_for("dashboard.ai_chatbot"))


@dashboard_bp.route("/ai-chatbot/test", methods=["POST"])
@require_premium("ai-chatbot")
def ai_chatbot_test():
    """Live test chat for the customer's own AI Agent — reuses the exact
    same grounded-reply path as the real public widget, using the
    agent's currently-saved instructions/knowledge base."""
    from app.models.platform import UserChatbot
    from app.utils.knowledge import generate_bot_reply
    agent = (UserChatbot.query.filter_by(user_id=current_user.id, platform="ai-agent")
             .order_by(UserChatbot.created_at.desc()).first())
    if not agent:
        return jsonify({"error": "Your AI Agent hasn't been set up yet."}), 404
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Enter a test message."}), 400
    reply, err = generate_bot_reply(
        agent.ai_instructions, agent.faqs, agent.knowledge_text, message,
        unknown_reply=agent.unknown_reply, sources=agent.knowledge_sources,
        charge_user_id=current_user.id,
    )
    if err:
        return jsonify({"reply": f"Error: {err}"})
    return jsonify({"reply": reply or "Sorry, I couldn't generate a response."})


# ══════════════════════════════════════════════════════════════════════
#  WHATSAPP CHAT WIDGET — simple click-to-chat button. NOT the WhatsApp
#  Business API bot (that's dashboard.chatbot_builder / whatsapp-bot).
#  No API keys, no Meta app, no webhooks — just a wa.me link wrapped in
#  a configurable floating button, deliberately its own product.
# ══════════════════════════════════════════════════════════════════════

def _valid_hex_color(value, default):
    """Accepts either the native <input type=color> picker or a manually
    typed hex code field — both post the same button_color string, so this
    just guards against a malformed/partial hex value reaching the CSS."""
    import re as _re_hex
    if value and _re_hex.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", value.strip()):
        return value.strip()
    return default


@dashboard_bp.route("/whatsapp-widget")
@require_premium("whatsapp-widget")
def whatsapp_widget():
    from app.models.platform import UserWhatsAppWidget
    widgets = UserWhatsAppWidget.query.filter_by(user_id=current_user.id).order_by(UserWhatsAppWidget.created_at.desc()).all()
    return render_template("dashboard/whatsapp_widget.html", widgets=[w.to_dict() for w in widgets])


@dashboard_bp.route("/whatsapp-widget/save", methods=["POST"])
@require_premium("whatsapp-widget")
def whatsapp_widget_save():
    from app.models.platform import UserWhatsAppWidget
    from app.utils.whatsapp_widget import sanitize_phone
    import re, secrets
    data = request.get_json(silent=True) or {}
    widget_id = data.get("id")
    phone = sanitize_phone(data.get("phone_number", ""))
    if not phone or len(phone) < 7:
        return jsonify({"error": "Please enter a valid WhatsApp number, including country code."}), 400

    if widget_id:
        widget = UserWhatsAppWidget.query.filter_by(id=widget_id, user_id=current_user.id).first()
        if not widget:
            return jsonify({"error": "Widget not found."}), 404
    else:
        name = data.get("name") or "My WhatsApp Widget"
        base_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "widget"
        slug = f"{base_slug}-{secrets.token_hex(3)}"
        widget = UserWhatsAppWidget(user_id=current_user.id, slug=slug)
        db.session.add(widget)

    widget.name = data.get("name", widget.name)[:128]
    widget.phone_number = phone
    widget.business_name = data.get("business_name")
    widget.welcome_message = data.get("welcome_message")
    widget.default_message = data.get("default_message")
    widget.profile_image = data.get("profile_image")
    widget.active = data.get("active", True)
    widget.settings = {
        "position": data.get("position", "bottom-right"),
        "button_color": _valid_hex_color(data.get("button_color"), "#25D366"),
        "animation": data.get("animation", "pulse"),
        "show_label": bool(data.get("show_label", True)),
        "button_text": data.get("button_text", "Chat with us"),
        "desktop_visible": bool(data.get("desktop_visible", True)),
        "mobile_visible": bool(data.get("mobile_visible", True)),
        "icon": data.get("icon", "whatsapp"),
    }
    widget.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True, "widget": widget.to_dict()})


@dashboard_bp.route("/whatsapp-widget/<int:widget_id>/delete", methods=["POST"])
@require_premium("whatsapp-widget")
def whatsapp_widget_delete(widget_id):
    from app.models.platform import UserWhatsAppWidget
    widget = UserWhatsAppWidget.query.filter_by(id=widget_id, user_id=current_user.id).first_or_404()
    db.session.delete(widget)
    db.session.commit()
    return jsonify({"success": True})


@dashboard_bp.route("/whatsapp-widget/<int:widget_id>/duplicate", methods=["POST"])
@require_premium("whatsapp-widget")
def whatsapp_widget_duplicate(widget_id):
    from app.models.platform import UserWhatsAppWidget
    import secrets
    original = UserWhatsAppWidget.query.filter_by(id=widget_id, user_id=current_user.id).first_or_404()
    copy = UserWhatsAppWidget(
        user_id=current_user.id, name=f"{original.name} (Copy)", slug=f"{original.slug}-{secrets.token_hex(3)}",
        phone_number=original.phone_number, business_name=original.business_name,
        welcome_message=original.welcome_message, default_message=original.default_message,
        profile_image=original.profile_image, active=True, settings=dict(original.settings or {}),
    )
    db.session.add(copy)
    db.session.commit()
    return jsonify({"success": True, "id": copy.id})


@dashboard_bp.route("/whatsapp-widget/<int:widget_id>/preview")
@require_premium("whatsapp-widget")
def whatsapp_widget_preview(widget_id):
    """Small iframe target for the live preview in the dashboard."""
    from app.models.platform import UserWhatsAppWidget
    from app.utils.whatsapp_widget import render_widget_html
    widget = UserWhatsAppWidget.query.filter_by(id=widget_id, user_id=current_user.id).first_or_404()
    html = render_widget_html(widget)
    return f"<!DOCTYPE html><html><body style='margin:0;background:#f5f5f5;height:100vh'>{html}</body></html>"


@dashboard_bp.route("/whatsapp-widget/preview-live", methods=["POST"])
@require_premium("whatsapp-widget")
def whatsapp_widget_preview_live():
    """Live preview from in-progress (unsaved) form values — so the user
    sees changes update immediately while configuring, per the spec's
    'live preview' requirement, without needing to save first."""
    from app.models.platform import UserWhatsAppWidget
    from app.utils.whatsapp_widget import render_widget_html
    data = request.get_json(silent=True) or {}
    fake = UserWhatsAppWidget(
        phone_number=data.get("phone_number", ""), business_name=data.get("business_name"),
        welcome_message=data.get("welcome_message"), default_message=data.get("default_message"),
        profile_image=data.get("profile_image"),
        settings={
            "position": data.get("position", "bottom-right"), "button_color": _valid_hex_color(data.get("button_color"), "#25D366"),
            "animation": data.get("animation", "pulse"), "show_label": bool(data.get("show_label", True)),
            "button_text": data.get("button_text", "Chat with us"),
            "desktop_visible": True, "mobile_visible": True,
            "icon": data.get("icon", "whatsapp"),
        },
    )
    html = render_widget_html(fake)
    return f"<!DOCTYPE html><html><body style='margin:0;background:#f5f5f5;height:100vh'>{html}</body></html>"


@dashboard_bp.route("/whatsapp-widget/upload-logo", methods=["POST"])
@require_premium("whatsapp-widget")
def whatsapp_widget_upload_logo():
    """Upload a business logo/avatar for the widget — used both as the
    bubble avatar and, when 'Logo' is picked as the button icon, as the
    floating button's icon itself. Same save_upload() pattern as the
    Invoice Generator's logo upload, so it respects whichever media
    storage backend (local/Cloudinary) the admin has configured."""
    from app.utils.media_storage import save_upload
    file = request.files.get("logo")
    if not file or not file.filename:
        return jsonify({"error": "No file selected."}), 400
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in {"png", "jpg", "jpeg", "gif", "webp", "svg"}:
        return jsonify({"error": "Please upload an image file (PNG, JPG, WEBP, SVG)."}), 400
    try:
        url, filename, size = save_upload(file, "whatsapp-widget-logos", current_app)
    except Exception as e:
        return jsonify({"error": f"Upload failed: {e}"}), 500
    return jsonify({"url": url})


@dashboard_bp.route("/whatsapp-widget/<int:widget_id>/plugin.zip")
@require_premium("whatsapp-widget")
def whatsapp_widget_plugin(widget_id):
    """A real WordPress plugin. Unlike the first version of this (which
    baked a static HTML snapshot into the plugin file — meaning editing
    the widget afterward never showed up on the live WP site), this
    plugin instead enqueues the SAME live embed.js script every other
    surface uses. Since embed.js queries the widget fresh on every
    request (see whatsapp_widget_embed_js below, now explicitly
    no-cached), editing your number/message/appearance/etc in the
    dashboard reflects on the WordPress site within a few seconds —
    without ever needing to re-download or re-install the plugin."""
    from app.models.platform import UserWhatsAppWidget
    import io, zipfile, re
    widget = UserWhatsAppWidget.query.filter_by(id=widget_id, user_id=current_user.id).first_or_404()
    slug = re.sub(r"[^a-z0-9]+", "-", widget.name.lower()).strip("-") or "whatsapp-widget"
    embed_url = url_for("dashboard.whatsapp_widget_embed_js", slug=widget.slug, _external=True)
    php = f"""<?php
/**
 * Plugin Name: {widget.name} — WhatsApp Chat Widget
 * Description: Adds a WhatsApp click-to-chat button to every page, live-synced with your Bazillin Studio dashboard — edit the widget there and it updates here automatically, no re-download needed.
 * Version: 2.0.0
 */
if (!defined('ABSPATH')) exit;

function bzn_wa_widget_enqueue() {{
    wp_enqueue_script('bzn-wa-widget', '{embed_url}', array(), '2.0.0', true);
}}
add_action('wp_enqueue_scripts', 'bzn_wa_widget_enqueue');
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}/{slug}.php", php)
        zf.writestr(f"{slug}/readme.txt", f"=== {widget.name} — WhatsApp Chat Widget ===\nGenerated by Bazillin Studio.\n\nInstallation:\n1. Upload this folder to /wp-content/plugins/\n2. Activate it under Plugins in your WordPress admin.\n3. The widget appears automatically on every page.\n\nThis plugin stays LIVE-SYNCED with your dashboard — change the number, message, colors, or anything else in your Bazillin Studio dashboard and it updates on your WordPress site automatically, no re-download or reinstall needed.\n")
    buf.seek(0)
    from flask import send_file
    return send_file(buf, mimetype="application/zip", as_attachment=True, download_name=f"{slug}.zip")


@dashboard_bp.route("/w/<slug>")
def whatsapp_widget_public(slug):
    """Standalone hosted widget page (Doc 8's 'Option 3') — a minimal
    full-page render of just the floating button, suitable for use in an
    iframe wherever the user wants it. Real, tracked view."""
    from app.models.platform import UserWhatsAppWidget
    from app.utils.whatsapp_widget import render_widget_html
    widget = UserWhatsAppWidget.query.filter_by(slug=slug, active=True).first_or_404()
    widget.view_count = (widget.view_count or 0) + 1
    db.session.commit()
    html_block = render_widget_html(widget, click_track_url=url_for("dashboard.whatsapp_widget_click", slug=slug))
    return f"<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'></head><body style='margin:0;background:transparent'>{html_block}</body></html>"


@dashboard_bp.route("/w/<slug>/embed.js")
def whatsapp_widget_embed_js(slug):
    """The copy-paste embeddable script — injects the widget into ANY
    external site the user pastes it on. Queries the widget config fresh
    on every request and is explicitly no-cached, so this is also what
    makes the WordPress plugin "sync" (see whatsapp_widget_plugin above):
    it enqueues THIS exact script instead of a static snapshot, so any
    edit in the dashboard shows up on the WordPress site on next page
    load — no re-download or reinstall needed."""
    from app.models.platform import UserWhatsAppWidget
    from app.utils.whatsapp_widget import render_widget_html
    widget = UserWhatsAppWidget.query.filter_by(slug=slug, active=True).first_or_404()
    html_block = render_widget_html(widget, click_track_url=url_for("dashboard.whatsapp_widget_click", slug=slug, _external=True)).replace("`", "\\`")
    js = f"""(function() {{
  var d = document.createElement('div');
  d.innerHTML = `{html_block}`;
  document.body.appendChild(d);
  fetch('{url_for("dashboard.whatsapp_widget_view", slug=slug, _external=True)}', {{method:'POST'}}).catch(function(){{}});
}})();"""
    return js, 200, {
        "Content-Type": "application/javascript",
        "Cache-Control": "no-cache, max-age=0, must-revalidate",
    }


@dashboard_bp.route("/w/<slug>/view", methods=["POST"])
def whatsapp_widget_view(slug):
    from app.models.platform import UserWhatsAppWidget, UserWhatsAppWidgetEvent
    widget = UserWhatsAppWidget.query.filter_by(slug=slug, active=True).first_or_404()
    widget.view_count = (widget.view_count or 0) + 1
    db.session.add(UserWhatsAppWidgetEvent(widget_id=widget.id, event_type="view"))
    db.session.commit()
    return jsonify({"ok": True})


@dashboard_bp.route("/w/<slug>/click", methods=["POST"])
def whatsapp_widget_click(slug):
    from app.models.platform import UserWhatsAppWidget, UserWhatsAppWidgetEvent
    widget = UserWhatsAppWidget.query.filter_by(slug=slug, active=True).first_or_404()
    widget.click_count = (widget.click_count or 0) + 1
    db.session.add(UserWhatsAppWidgetEvent(widget_id=widget.id, event_type="click"))
    db.session.commit()
    return jsonify({"ok": True})


@dashboard_bp.route("/whatsapp-widget/<int:widget_id>/analytics")
def whatsapp_widget_analytics_data(widget_id):
    """Real analytics from the per-event log — same server-rendered-
    bar-chart convention as WhatsApp Bot/AI Chatbot/Payment Link/Funnel
    analytics elsewhere in this app."""
    from app.models.platform import UserWhatsAppWidget, UserWhatsAppWidgetEvent
    from sqlalchemy import func
    import datetime as _dt

    widget = UserWhatsAppWidget.query.filter_by(id=widget_id, user_id=current_user.id).first_or_404()

    today = _dt.date.today()
    days = [today - _dt.timedelta(days=i) for i in range(13, -1, -1)]
    start = _dt.datetime.combine(days[0], _dt.time.min)

    rows = (db.session.query(func.date(UserWhatsAppWidgetEvent.created_at),
                              UserWhatsAppWidgetEvent.event_type,
                              func.count(UserWhatsAppWidgetEvent.id))
            .filter(UserWhatsAppWidgetEvent.widget_id == widget.id,
                    UserWhatsAppWidgetEvent.created_at >= start)
            .group_by(func.date(UserWhatsAppWidgetEvent.created_at), UserWhatsAppWidgetEvent.event_type)
            .all())
    daily = {}
    for d, etype, cnt in rows:
        key = d.isoformat() if hasattr(d, "isoformat") else str(d)[:10]
        daily.setdefault(key, {"view": 0, "click": 0})[etype] = cnt

    trend = []
    for d in days:
        key = d.isoformat()
        views = daily.get(key, {}).get("view", 0)
        clicks = daily.get(key, {}).get("click", 0)
        trend.append({"label": d.strftime("%m/%d"), "views": views, "clicks": clicks})
    max_val = max((max(t["views"], t["clicks"]) for t in trend), default=0)
    for t in trend:
        t["view_pct"] = round((t["views"] / max_val) * 100, 1) if max_val else 0
        t["click_pct"] = round((t["clicks"] / max_val) * 100, 1) if max_val else 0

    return jsonify({
        "view_count": widget.view_count or 0,
        "click_count": widget.click_count or 0,
        "click_rate": round((widget.click_count or 0) / widget.view_count * 100, 1) if widget.view_count else 0,
        "trend": trend,
    })


# ══════════════════════════════════════════════════════════════════════
#  AI CREDIT STORE — buy credit packages priced/managed by the admin
#  under Admin -> Credit Packages. Mirrors the marketplace checkout ->
#  gateway callback -> server-verify -> grant pattern in
#  app/payments/routes.py (_mark_order_paid) rather than inventing a new
#  one, and is guarded the same way: credits are only ever added after
#  server-side payment verification, and grant_purchased_credits() is
#  idempotent so a duplicate callback can't double-credit.
# ══════════════════════════════════════════════════════════════════════

CREDIT_GATEWAY_LABELS = {
    "stripe": "Credit / Debit Card (Stripe)",
    "paystack": "Paystack",
    "flutterwave": "Flutterwave",
    "paypal": "PayPal",
}


@dashboard_bp.route("/credits")
def credits_home():
    from app.models.platform import CreditPackage, CreditTransaction, CreditPurchase
    from app.utils.payments import currency_symbol
    from app.utils.credits import get_credit_status, get_credit_unit_pricing
    status = get_credit_status(current_user.id)  # runs the free-refill check before rendering
    packages = CreditPackage.query.filter_by(active=True).order_by(CreditPackage.sort_order, CreditPackage.price).all()
    recent_tx = CreditTransaction.query.filter_by(user_id=current_user.id).order_by(CreditTransaction.created_at.desc()).limit(20).all()
    purchases = CreditPurchase.query.filter_by(user_id=current_user.id).order_by(CreditPurchase.created_at.desc()).limit(20).all()
    return render_template(
        "dashboard/credits.html",
        balance=status["total"], credit_status=status,
        packages=[p.to_dict() for p in packages],
        transactions=[t.to_dict() for t in recent_tx],
        purchases=purchases,
        currency_symbol=currency_symbol(),
        unit_pricing=get_credit_unit_pricing() or {"unit_size": 100, "unit_price": 10.0, "max_units": 10000},
    )


@dashboard_bp.route("/credits/status")
def credits_status():
    """Lightweight JSON balance/refill-countdown poll for the AI Credits
    page — avoids a full page reload just to refresh the countdown or
    catch a refill landing while the tab is open."""
    from app.utils.credits import get_credit_status
    status = get_credit_status(current_user.id)
    if status is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(status)


@dashboard_bp.route("/credits/buy/<int:package_id>")
def credits_choose_gateway(package_id):
    from app.models.platform import CreditPackage
    from app.utils.payments import get_enabled_gateways, currency_symbol
    package = CreditPackage.query.filter_by(id=package_id, active=True).first_or_404()
    enabled = get_enabled_gateways()
    if not enabled:
        flash("No payment methods are configured yet on this site. Please contact us directly to arrange payment.", "danger")
        return redirect(url_for("dashboard.credits_home"))
    return render_template(
        "dashboard/credits_checkout.html", package=package,
        gateways=[(g, CREDIT_GATEWAY_LABELS.get(g, g.title())) for g in enabled],
        currency_symbol=currency_symbol(),
    )


@dashboard_bp.route("/credits/buy-custom/<int:units>")
def credits_choose_gateway_custom(units):
    from app.utils.payments import get_enabled_gateways, currency_symbol
    from app.utils.credits import compute_custom_credit_price
    try:
        credits, amount = compute_custom_credit_price(units)
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("dashboard.credits_home"))
    enabled = get_enabled_gateways()
    if not enabled:
        flash("No payment methods are configured yet on this site. Please contact us directly to arrange payment.", "danger")
        return redirect(url_for("dashboard.credits_home"))
    return render_template(
        "dashboard/credits_checkout.html", package=None,
        custom_units=units, custom_credits=credits, custom_amount=amount,
        gateways=[(g, CREDIT_GATEWAY_LABELS.get(g, g.title())) for g in enabled],
        currency_symbol=currency_symbol(),
    )


@dashboard_bp.route("/credits/buy/<int:package_id>/<gateway>")
def credits_checkout_with_gateway(package_id, gateway):
    from app.models.platform import CreditPackage, CreditPurchase
    package = CreditPackage.query.filter_by(id=package_id, active=True).first_or_404()

    purchase = CreditPurchase(
        user_id=current_user.id, package_id=package.id, credits=package.credits,
        amount=package.price, currency=package.currency, gateway=gateway, status="pending",
    )
    try:
        db.session.add(purchase)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Credit purchase row creation failed")
        flash(f"Couldn't start checkout: {e}", "danger")
        return redirect(url_for("dashboard.credits_home"))
    return _start_credit_checkout(purchase, gateway)


@dashboard_bp.route("/credits/buy-custom/<int:units>/<gateway>")
def credits_checkout_custom(units, gateway):
    """Checkout for the dashboard's quantity-stepper 'quick buy' widget —
    N units at the admin-set per-unit rate (see
    app.utils.credits.compute_custom_credit_price), rather than a fixed
    CreditPackage. Same checkout function underneath either way."""
    from app.models.platform import CreditPurchase
    from app.utils.credits import compute_custom_credit_price
    from app.utils.payments import get_site_currency
    try:
        credits, amount = compute_custom_credit_price(units)
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("dashboard.credits_home"))

    purchase = CreditPurchase(
        user_id=current_user.id, package_id=None, credits=credits,
        amount=amount, currency=get_site_currency(), gateway=gateway, status="pending",
    )
    try:
        db.session.add(purchase)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Custom credit purchase row creation failed")
        flash(f"Couldn't start checkout: {e}", "danger")
        return redirect(url_for("dashboard.credits_home"))
    return _start_credit_checkout(purchase, gateway)


def _start_credit_checkout(purchase, gateway):
    """Shared by both the fixed-package and quantity-stepper purchase
    flows — everything past this point only needs the purchase row
    itself (credits/amount/label), not which flow created it."""
    from flask import g
    from app.utils.payments import resolve_checkout_currency
    from app.utils.currency import convert
    # Same currency-safety fix as marketplace checkout (see
    # app/payments/routes.py): only charge in a currency the admin has
    # confirmed this gateway account is actually approved for, converting
    # the purchase's own currency into whatever we're really charging —
    # previously this always silently charged in the SITE'S base
    # currency using the purchase's raw (unconverted) amount, which is
    # wrong whenever a credit package's price was entered in a different
    # currency than the site base.
    preferred_currency = getattr(g, "currency", None) or purchase.currency
    charge_currency, matched_preference = resolve_checkout_currency(gateway, preferred_currency)
    charge_amount = round(convert(purchase.amount, purchase.currency, charge_currency), 2)
    purchase.currency = charge_currency
    purchase.amount = charge_amount
    title = f"{purchase.credits:,} AI Credits — {purchase.label}"
    try:
        if gateway == "stripe":
            from app.utils.payments import create_stripe_session
            session = create_stripe_session(
                title, charge_amount, current_user,
                url_for("dashboard.credits_success", purchase_id=purchase.id, _external=True),
                url_for("dashboard.credits_home", _external=True),
                metadata={"credit_purchase_id": purchase.id, "user_id": current_user.id},
                currency=charge_currency,
            )
            purchase.gateway_ref = session.id
            db.session.commit()
            return redirect(session.url, code=303)
        if gateway == "paystack":
            from app.utils.payments import create_paystack_transaction
            data = create_paystack_transaction(
                title, charge_amount, current_user,
                url_for("dashboard.credits_paystack_callback", purchase_id=purchase.id, _external=True),
                metadata={"credit_purchase_id": purchase.id, "user_id": current_user.id},
                currency=charge_currency,
            )
            purchase.gateway_ref = data["reference"]
            db.session.commit()
            return redirect(data["authorization_url"], code=303)
        if gateway == "flutterwave":
            from app.utils.payments import create_flutterwave_transaction
            tx_ref = f"credits-{purchase.id}-{int(datetime.utcnow().timestamp())}"
            link = create_flutterwave_transaction(
                title, charge_amount, current_user, tx_ref,
                url_for("dashboard.credits_flutterwave_callback", purchase_id=purchase.id, _external=True),
                currency=charge_currency,
            )
            purchase.gateway_ref = tx_ref
            db.session.commit()
            return redirect(link, code=303)
        if gateway == "paypal":
            from app.utils.payments import create_paypal_order
            paypal_order_id, approval_url = create_paypal_order(
                title, charge_amount,
                url_for("dashboard.credits_paypal_capture", purchase_id=purchase.id, _external=True),
                url_for("dashboard.credits_home", _external=True),
                currency=charge_currency,
            )
            purchase.gateway_ref = paypal_order_id
            db.session.commit()
            return redirect(approval_url, code=303)
        flash(f"{CREDIT_GATEWAY_LABELS.get(gateway, gateway)} isn't fully configured yet.", "danger")
        db.session.delete(purchase)
        db.session.commit()
    except Exception as e:
        # .exception() (not .error()) so the full traceback lands in the
        # server log — the flashed message alone was never enough to
        # actually diagnose "any gateway fails" from the outside.
        current_app.logger.exception(f"Credit checkout error (gateway={gateway}, purchase={purchase.id})")
        flash(f"Payment could not be initiated: {e}", "danger")
        db.session.delete(purchase)
        db.session.commit()
    return redirect(url_for("dashboard.credits_home"))


@dashboard_bp.route("/credits/paystack/callback/<int:purchase_id>")
def credits_paystack_callback(purchase_id):
    from app.models.platform import CreditPurchase
    from app.utils.payments import verify_paystack_payment, reconcile_charged_currency
    from app.utils.credits import grant_purchased_credits
    purchase = CreditPurchase.query.filter_by(id=purchase_id, user_id=current_user.id).first_or_404()
    try:
        result = verify_paystack_payment(purchase.gateway_ref)
        if result and result.get("status") == "success":
            reconcile_charged_currency(purchase, result.get("currency"), result.get("amount"), is_minor_unit=True)
            grant_purchased_credits(purchase)
        else:
            purchase.status = "failed"
            db.session.commit()
            flash("Payment could not be verified.", "danger")
    except Exception as e:
        current_app.logger.exception(f"Paystack credit verify error (purchase={purchase.id})")
        flash("We couldn't confirm this payment right now. If you were charged, contact support with your reference.", "danger")
    return redirect(url_for("dashboard.credits_success", purchase_id=purchase.id))


@dashboard_bp.route("/credits/flutterwave/callback/<int:purchase_id>")
def credits_flutterwave_callback(purchase_id):
    from app.models.platform import CreditPurchase
    from app.utils.payments import verify_flutterwave_payment, reconcile_charged_currency
    from app.utils.credits import grant_purchased_credits
    purchase = CreditPurchase.query.filter_by(id=purchase_id, user_id=current_user.id).first_or_404()
    transaction_id = request.args.get("transaction_id")
    try:
        result = verify_flutterwave_payment(transaction_id)
        if result and result.get("status") == "successful":
            reconcile_charged_currency(purchase, result.get("currency"), result.get("amount"), is_minor_unit=False)
            grant_purchased_credits(purchase)
        else:
            purchase.status = "failed"
            db.session.commit()
            flash("Payment could not be verified.", "danger")
    except Exception as e:
        current_app.logger.exception(f"Flutterwave credit verify error (purchase={purchase.id})")
        flash("We couldn't confirm this payment right now. If you were charged, contact support with your reference.", "danger")
    return redirect(url_for("dashboard.credits_success", purchase_id=purchase.id))


@dashboard_bp.route("/credits/paypal/capture/<int:purchase_id>")
def credits_paypal_capture(purchase_id):
    from app.models.platform import CreditPurchase
    from app.utils.payments import capture_paypal_order, reconcile_charged_currency
    from app.utils.credits import grant_purchased_credits
    purchase = CreditPurchase.query.filter_by(id=purchase_id, user_id=current_user.id).first_or_404()
    try:
        result = capture_paypal_order(purchase.gateway_ref)
        if result and result.get("status") == "COMPLETED":
            try:
                captured = result["purchase_units"][0]["payments"]["captures"][0]["amount"]
                reconcile_charged_currency(purchase, captured.get("currency_code"), captured.get("value"), is_minor_unit=False)
            except (KeyError, IndexError, TypeError):
                pass
            grant_purchased_credits(purchase)
        else:
            purchase.status = "failed"
            db.session.commit()
            flash("Payment could not be verified.", "danger")
    except Exception as e:
        current_app.logger.exception(f"PayPal credit capture error (purchase={purchase.id})")
        flash("We couldn't confirm this payment right now. If you were charged, contact support with your reference.", "danger")
    return redirect(url_for("dashboard.credits_success", purchase_id=purchase.id))


@dashboard_bp.route("/credits/success/<int:purchase_id>")
def credits_success(purchase_id):
    from app.models.platform import CreditPurchase
    from app.utils.credits import grant_purchased_credits
    from app.utils.payments import currency_symbol
    purchase = CreditPurchase.query.filter_by(id=purchase_id, user_id=current_user.id).first_or_404()
    # Stripe Checkout has no callback route (unlike Paystack/Flutterwave/
    # PayPal above) — it redirects straight here. Normally the real
    # signed webhook (credits_stripe_webhook) grants credits first, but
    # if that hasn't landed yet (webhook lag, or not configured), verify
    # directly against Stripe's own API here rather than trusting the
    # redirect itself — the browser reaching this URL is never treated
    # as proof of payment on its own.
    if purchase.gateway == "stripe" and purchase.status == "pending" and purchase.gateway_ref:
        try:
            import stripe
            stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
            session = stripe.checkout.Session.retrieve(purchase.gateway_ref)
            if session.get("payment_status") == "paid":
                grant_purchased_credits(purchase)
        except Exception as e:
            current_app.logger.error(f"Stripe credit success-page verify error: {e}")
    return render_template("dashboard/credits_success.html", purchase=purchase, balance=current_user.credits or 0, currency_symbol=currency_symbol())


@dashboard_bp.route("/credits/stripe/webhook", methods=["POST"])
def credits_stripe_webhook():
    """Real webhook path for Stripe, mirroring app/payments/routes.py's
    stripe_webhook() exactly (same signature verification, same
    gateway_ref lookup) — covers the case where the customer closes the
    tab before the success-URL redirect completes."""
    from app.models.platform import CreditPurchase
    from app.utils.credits import grant_purchased_credits
    import stripe
    payload = request.data
    sig = request.headers.get("Stripe-Signature", "")
    secret = current_app.config.get("STRIPE_WEBHOOK_SECRET", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
        if event["type"] == "checkout.session.completed":
            sess = event["data"]["object"]
            purchase = CreditPurchase.query.filter_by(gateway_ref=sess["id"], gateway="stripe").first()
            if purchase:
                grant_purchased_credits(purchase)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════
#  AI VOICE STUDIO (dashboard) — real persistent generations + real
#  audio recording, living in the dashboard rather than redirecting
#  the user to the public Developer Tools page.
#
#  Being upfront about voice selection: the free tier (gTTS) has real,
#  working voices but they are LANGUAGE/ACCENT variants of one synthetic
#  voice per language (e.g. "English (US)", "English (UK)", "French") —
#  gTTS does not provide distinct named man/woman/boy/girl character
#  voices, and this app never claims it does. Real distinct named voices
#  with gender/age (e.g. "Rachel — Woman, American", "Josh — Man,
#  American") come from ElevenLabs once ELEVENLABS_API_KEY is configured
#  server-side (app/utils/tts.py now pulls the real named voice list
#  from ElevenLabs' API rather than exposing one generic "ElevenLabs"
#  option) — that's a paid third-party service and needs its own API key,
#  which only the site admin can add via server environment variables.
# ══════════════════════════════════════════════════════════════════════

@dashboard_bp.route("/voice-studio")
@require_premium("voice-studio")
def voice_studio():
    from app.models.platform import VoiceGeneration
    from app.utils.tts import list_voices
    generations = (VoiceGeneration.query.filter_by(user_id=current_user.id)
                   .order_by(VoiceGeneration.created_at.desc()).limit(100).all())
    return render_template(
        "dashboard/voice_studio.html",
        voices=list_voices(), generations=[g.to_dict() for g in generations],
        credits=current_user.credits,
    )


@dashboard_bp.route("/voice-studio/generate", methods=["POST"])
@require_premium("voice-studio")
def voice_studio_generate():
    from app.models.platform import VoiceGeneration
    from app.utils.tts import generate_speech, list_voices
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice_id = data.get("voice_id", "en-us")
    speed = float(data.get("speed", 1.0))

    if not text:
        return jsonify({"error": "Please enter some text."}), 400
    from app.utils.credits import get_credit_status, deduct_credits
    status = get_credit_status(current_user.id)  # also runs the free-refill check before we look at the balance
    if status["total"] <= 0:
        return jsonify({"error": "You're out of AI credits.", "credits_left": 0, "seconds_until_refill": status["seconds_until_refill"]}), 402

    result, error = generate_speech(text, voice_id, speed=speed)
    if error:
        # Generation failed before anything was produced — don't charge for it.
        return jsonify({"error": error}), 500

    ok, balance_or_error = deduct_credits(current_user.id, 1, type="usage", reason="Voice generation")
    if not ok:
        # Lost a race with another request between the check above and here —
        # the audio was already generated, so don't throw it away over this.
        current_app.logger.warning(f"Voice generation credit deduction failed post-generation for user {current_user.id}: {balance_or_error}")

    audio_url = result["audio_url"]
    relative_path = audio_url.split("/static/", 1)[-1]
    voice_meta = next((v for v in list_voices() if v["id"] == voice_id), {"name": result.get("voice", voice_id)})

    gen = VoiceGeneration(
        user_id=current_user.id, text=text, voice_id=voice_id, voice_name=voice_meta.get("name"),
        file_path=relative_path, file_format="mp3", char_count=len(text), credits_used=1,
    )
    db.session.add(gen)
    db.session.commit()

    return jsonify({"generation": gen.to_dict(), "credits_left": current_user.credits})


@dashboard_bp.route("/voice-studio/record", methods=["POST"])
@require_premium("voice-studio")
def voice_studio_record():
    """Save a voice recording captured in-browser (MediaRecorder) — real
    microphone audio, not TTS. No network/provider dependency at all, so
    this always works regardless of any TTS provider's availability."""
    from app.models.platform import VoiceGeneration
    import os, uuid
    audio_file = request.files.get("audio")
    if not audio_file or not audio_file.filename:
        return jsonify({"error": "No recording received."}), 400

    audio_dir = os.path.join(current_app.root_path, "static", "generated_audio")
    os.makedirs(audio_dir, exist_ok=True)
    ext = "webm"
    if "." in audio_file.filename:
        candidate = audio_file.filename.rsplit(".", 1)[-1].lower()
        if candidate in ("webm", "ogg", "mp3", "wav", "m4a"):
            ext = candidate
    filename = f"recording_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(audio_dir, filename)
    audio_file.save(filepath)

    title = (request.form.get("title") or "My Recording").strip()[:256]
    gen = VoiceGeneration(
        user_id=current_user.id, text="[Recorded audio]", voice_id="recording", voice_name="My Voice (Recorded)",
        file_path=f"generated_audio/{filename}", file_format=ext, char_count=0, credits_used=0, title=title,
    )
    db.session.add(gen)
    db.session.commit()
    return jsonify({"generation": gen.to_dict()})


@dashboard_bp.route("/voice-studio/<int:gen_id>/favorite", methods=["POST"])
@require_premium("voice-studio")
def voice_studio_favorite(gen_id):
    from app.models.platform import VoiceGeneration
    gen = VoiceGeneration.query.filter_by(id=gen_id, user_id=current_user.id).first_or_404()
    gen.is_favorite = not gen.is_favorite
    db.session.commit()
    return jsonify({"is_favorite": gen.is_favorite})


@dashboard_bp.route("/voice-studio/<int:gen_id>/rename", methods=["POST"])
@require_premium("voice-studio")
def voice_studio_rename(gen_id):
    from app.models.platform import VoiceGeneration
    gen = VoiceGeneration.query.filter_by(id=gen_id, user_id=current_user.id).first_or_404()
    title = (request.get_json(silent=True) or {}).get("title", "").strip()
    gen.title = title[:256] or None
    db.session.commit()
    return jsonify({"title": gen.title})


@dashboard_bp.route("/voice-studio/<int:gen_id>/delete", methods=["POST"])
@require_premium("voice-studio")
def voice_studio_delete(gen_id):
    from app.models.platform import VoiceGeneration
    import os
    gen = VoiceGeneration.query.filter_by(id=gen_id, user_id=current_user.id).first_or_404()
    try:
        full_path = os.path.join(current_app.root_path, "static", gen.file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    except Exception:
        pass
    db.session.delete(gen)
    db.session.commit()
    return jsonify({"message": "Deleted."})



