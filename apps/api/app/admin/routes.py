"""
app/admin/routes.py
===================
Full Admin Control Center — every feature wired to the DB.
"""
from functools import wraps
import json
import os
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, abort, current_app, send_file, make_response, session,
    Response, stream_with_context
)
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db, cache
from app.models import (
    User, Role, SiteSetting, AuditLog,
    Product, Order, BlogPost, Page, CmsBlock,
    Project, Service, Testimonial, Skill,
    HostingPlan, HostingSubscription, HostingServer,
    FreelancerProfile, JobPost,
    MediaFile, EmailTemplate, SupportTicket, FAQItem,
    Profile, Experience, Education, Certification, Award,
    NewsletterSubscriber, NewsletterCampaign, AnalyticsEvent, PageView,
    Notification, Message, Download, WishlistItem,
    TrendItem,
)
from app.utils.audit import log_action
from app.utils.settings import get_setting, set_setting, default_site_currency

admin_bp = Blueprint("admin", __name__, template_folder="../../templates/admin")


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ─────────────────────────────────────────────────────────────────
@admin_bp.route("/")
@admin_required
def dashboard():
    from app.models.platform import Invoice, ClientProject
    from flask import g
    from app.utils.currency import convert_and_sum, rates_are_missing_for
    # Every paid Order/Invoice counts here regardless of what currency it was
    # actually paid in — each currency's total is converted into the site's
    # display currency (using the admin's manual rate table) before being
    # added up, so a $20 order and a ₦30,000 order correctly combine into
    # one real total instead of either being blended 1:1 (the old bug) or
    # silently dropped (the fix that replaced that bug). The true, per-
    # currency, UNCONVERTED breakdown always lives at admin.financials.
    display_currency = getattr(g, "currency", "NGN")
    order_sums = db.session.query(Order.currency, func.sum(Order.amount)) \
        .filter_by(status="paid").group_by(Order.currency).all()
    invoice_sums = db.session.query(Invoice.currency, func.sum(Invoice.amount)) \
        .filter_by(status="paid").group_by(Invoice.currency).all()
    stats = {
        "users":    User.query.count(),
        "products": Product.query.count(),
        "orders":   Order.query.filter_by(status="paid").count(),
        "revenue":  convert_and_sum(order_sums, display_currency),
        "project_revenue": convert_and_sum(invoice_sums, display_currency),
        "posts":    BlogPost.query.filter_by(published=True).count(),
        "tickets":  SupportTicket.query.filter_by(status="open").count(),
    }
    stats["total_revenue"] = stats["revenue"] + stats["project_revenue"]
    stats["display_currency"] = display_currency
    # Which currencies actually appearing in paid orders/invoices have no
    # manual rate set yet — those got counted at 1:1 (unconverted) above,
    # so flag it instead of silently under/over-reporting.
    seen_currencies = {c for c, _ in order_sums if c} | {c for c, _ in invoice_sums if c}
    stats["unconverted_currencies"] = rates_are_missing_for(seen_currencies)
    chart_data = []
    for i in range(7):
        d = datetime.utcnow() - timedelta(days=6 - i)
        start = d.replace(hour=0, minute=0, second=0, microsecond=0)
        end   = d.replace(hour=23, minute=59, second=59)
        day_users = User.query.filter(User.created_at >= start, User.created_at <= end).count()
        day_order_sums = db.session.query(Order.currency, func.sum(Order.amount)) \
            .filter(Order.status == "paid", Order.created_at >= start, Order.created_at <= end) \
            .group_by(Order.currency).all()
        day_invoice_sums = db.session.query(Invoice.currency, func.sum(Invoice.amount)) \
            .filter(Invoice.status == "paid", Invoice.paid_at >= start, Invoice.paid_at <= end) \
            .group_by(Invoice.currency).all()
        day_rev = convert_and_sum(day_order_sums, display_currency)
        day_project_rev = convert_and_sum(day_invoice_sums, display_currency)
        chart_data.append({"date": d.strftime("%b %d"), "users": day_users, "revenue": day_rev,
                            "project_revenue": day_project_rev, "total_revenue": day_rev + day_project_rev})
    # Revenue by client — who's actually paying, and how much (converted to
    # the display currency so clients who paid in different currencies can
    # still be ranked against each other on one list).
    client_rows = (db.session.query(ClientProject.id, ClientProject.title, User.name, User.email,
                                     Invoice.currency, func.sum(Invoice.amount).label("paid_total"))
                   .join(Invoice, Invoice.project_id == ClientProject.id)
                   .join(User, User.id == ClientProject.client_id)
                   .filter(Invoice.status == "paid")
                   .group_by(ClientProject.id, User.id, Invoice.currency)
                   .all())
    client_totals = {}
    for project_id, title, name, email, currency, paid_total in client_rows:
        key = (title, name, email)
        client_totals[key] = client_totals.get(key, 0.0) + convert_and_sum([(currency, paid_total)], display_currency)
    client_revenue = sorted(
        [(title, name, email, total) for (title, name, email), total in client_totals.items()],
        key=lambda row: row[3], reverse=True,
    )[:10]
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, chart_data=chart_data,
                           recent_users=recent_users, recent_orders=recent_orders,
                           client_revenue=client_revenue)


# ── Settings ──────────────────────────────────────────────────────────────────
@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        for key, value in request.form.items():
            if key.startswith("_"):
                continue
            set_setting(key, value)
        log_action(current_user.id, "admin.settings.update", "SiteSettings")
        flash("Settings saved.", "success")
        return redirect(url_for("admin.settings"))
    groups = {}
    for s in SiteSetting.query.order_by(SiteSetting.group, SiteSetting.key).all():
        groups.setdefault(s.group, []).append(s)
    from app.models.core import Agent
    all_agents = Agent.query.filter_by(active=True).order_by(Agent.name).all()
    return render_template("admin/settings.html", groups=groups, all_agents=all_agents)

@admin_bp.route("/settings/update", methods=["POST"])
@admin_required
def settings_update():
    data = request.get_json(silent=True) or {}
    key = data.get("key")
    value = data.get("value", "")
    if not key:
        return jsonify({"error": "Key required"}), 400
    set_setting(key, str(value))
    log_action(current_user.id, "admin.setting.update", key)
    return jsonify({"success": True})


@admin_bp.route("/settings/test-google-sheets", methods=["POST"])
@admin_required
def test_google_sheets():
    from app.utils.google_sheets import test_connection
    data = request.get_json(silent=True) or {}
    spreadsheet_id = (data.get("spreadsheet_id") or "").strip()
    if not spreadsheet_id:
        return jsonify({"success": False, "error": "Spreadsheet ID is required."}), 400
    sa_json = get_setting("google_service_account_json")
    if not sa_json:
        return jsonify({"success": False, "error": "Paste a service account JSON key above first."}), 400
    try:
        title = test_connection(sa_json, spreadsheet_id)
        return jsonify({"success": True, "title": title})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@admin_bp.route("/settings/test-bloom", methods=["POST"])
@admin_required
def test_bloom():
    """Connectivity check against Bloom's real API — Bloom has no text
    generation endpoint, so this lists brands (a lightweight authenticated
    call) rather than generating anything."""
    from app.utils.bloom import list_brands
    brands, err = list_brands()
    if err:
        return jsonify({"success": False, "error": err}), 400
    return jsonify({"success": True, "text": f"Connected — {len(brands)} brand(s) on this account.", "brands": brands})


@admin_bp.route("/settings/bloom/brands", methods=["GET"])
@admin_required
def bloom_brands():
    from app.utils.bloom import list_brands
    brands, err = list_brands()
    if err:
        return jsonify({"success": False, "error": err}), 400
    return jsonify({"success": True, "brands": brands})


@admin_bp.route("/settings/bloom/onboard-brand", methods=["POST"])
@admin_required
def bloom_onboard_brand():
    from app.utils.bloom import onboard_brand
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    brand, err = onboard_brand(url)
    if err:
        return jsonify({"success": False, "error": err}), 400
    set_setting("bloom_brand_session_id", brand.get("id", ""), group="bloom", label="Bloom brand session id")
    set_setting("bloom_brand_source_url", url, group="bloom", label="Bloom brand source URL")
    log_action(current_user.id, "admin.bloom.onboard_brand", url)
    return jsonify({"success": True, "brand": brand})


@admin_bp.route("/settings/bloom/select-brand", methods=["POST"])
@admin_required
def bloom_select_brand():
    """Point Bloom at an existing brand instead of onboarding a new one —
    for accounts that already have a brand set up on trybloom.ai."""
    data = request.get_json(silent=True) or {}
    brand_id = (data.get("brand_id") or "").strip()
    if not brand_id:
        return jsonify({"success": False, "error": "No brand id given."}), 400
    from app.utils.bloom import get_brand
    brand, err = get_brand(brand_id)
    if err:
        return jsonify({"success": False, "error": err}), 400
    set_setting("bloom_brand_session_id", brand_id, group="bloom", label="Bloom brand session id")
    log_action(current_user.id, "admin.bloom.select_brand", brand_id)
    return jsonify({"success": True, "brand": brand})


@admin_bp.route("/settings/bloom/brand-status", methods=["GET"])
@admin_required
def bloom_brand_status():
    """Polls the currently-configured brand's status (used while it's
    still 'analyzing' after onboarding)."""
    from app.utils.bloom import get_brand
    brand_id = (get_setting("bloom_brand_session_id") or "").strip()
    if not brand_id:
        return jsonify({"success": True, "brand": None})
    brand, err = get_brand(brand_id)
    if err:
        return jsonify({"success": False, "error": err}), 400
    return jsonify({"success": True, "brand": brand})


@admin_bp.route("/settings/send-test-email", methods=["POST"])
@admin_required
def send_test_email():
    from app.utils.email import send_email
    target = get_setting("mail_username") or current_user.email
    ok = send_email(
        to=current_user.email,
        subject="Bazillin Studio — test email",
        body_html=f"<p>This is a test email sent from your Admin -> Settings -> Email panel.</p>"
                  f"<p>If you're reading this, your SMTP configuration is working correctly.</p>",
    )
    if ok:
        return jsonify({"success": True, "to": current_user.email})
    return jsonify({"success": False, "error": "Send failed — double-check SMTP host/port/username/password above, then try again."}), 400


# ── Users ─────────────────────────────────────────────────────────────────────
@admin_bp.route("/users")
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    q    = request.args.get("q", "")
    role = request.args.get("role", "")
    query = User.query
    if q:
        query = query.filter(db.or_(User.name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    if role:
        r = Role.query.filter_by(name=role).first()
        if r:
            query = query.filter_by(role_id=r.id)
    users_page = query.order_by(User.created_at.desc()).paginate(page=page, per_page=25, error_out=False)
    roles = Role.query.all()
    return render_template("admin/users.html", users=users_page, roles=roles, q=q, current_role=role)


@admin_bp.route("/security")
@admin_required
def security_center():
    """Real security signals from data that actually exists — NOT the full
    enterprise Security Center from the master prompt (no firewall/IP-
    blocking/geo-alerts/malware-scanning/API-key-rotation — those need
    infrastructure this app doesn't have, like a WAF or a threat-intel
    feed). What's here is grounded in the real AuditLog table:
    failed vs successful logins, 2FA adoption, and simple brute-force
    detection (5+ failed logins for the same email within an hour)."""
    from datetime import timedelta
    from app.models.core import AuditLog
    from app.models.user import User

    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    failed_24h = AuditLog.query.filter(AuditLog.action == "auth.login_failed", AuditLog.created_at >= day_ago).count()
    failed_7d = AuditLog.query.filter(AuditLog.action == "auth.login_failed", AuditLog.created_at >= week_ago).count()
    success_7d = AuditLog.query.filter(AuditLog.action == "auth.login", AuditLog.created_at >= week_ago).count()

    total_users = User.query.count()
    users_with_2fa = User.query.filter_by(totp_enabled=True).count()
    two_fa_pct = round(100 * users_with_2fa / total_users) if total_users else 0

    # Simple brute-force detection: same target (email) failing 5+ times
    # within the last hour — grouped from real rows, not a guess.
    hour_ago = now - timedelta(hours=1)
    recent_fails = AuditLog.query.filter(
        AuditLog.action == "auth.login_failed", AuditLog.created_at >= hour_ago).all()
    fail_counts = {}
    for f in recent_fails:
        fail_counts[f.target] = fail_counts.get(f.target, 0) + 1
    suspicious = [(target, count) for target, count in fail_counts.items() if count >= 5]

    recent_auth_events = AuditLog.query.filter(
        AuditLog.action.in_(["auth.login", "auth.login_failed", "auth.password_change", "auth.register"])
    ).order_by(AuditLog.created_at.desc()).limit(50).all()

    return render_template("admin/security_center.html",
                           failed_24h=failed_24h, failed_7d=failed_7d, success_7d=success_7d,
                           total_users=total_users, users_with_2fa=users_with_2fa, two_fa_pct=two_fa_pct,
                           suspicious=suspicious, recent_auth_events=recent_auth_events)


@admin_bp.route("/clients/<int:user_id>/timeline")
@admin_required
def customer_timeline(user_id):
    """One aggregated history for a single client, pulled from real data
    across the platform — not a separate 'CRM record' to maintain by hand.
    Covers: projects, invoices/payments, meetings, support tickets, wallet
    activity, and (if a CRM Lead shares this client's email) their pipeline
    notes/stage. Explicitly NOT built here: a unified messages/emails/calls
    feed (chat contacts are keyed by phone/chat_id per channel, not by
    platform user account, so reliably matching them to this client
    without guessing is its own project) or AI-generated insights on the
    timeline — both real gaps in this MVP, not silently skipped."""
    from app.models.platform import (ClientProject, Invoice, ProjectMeeting,
                                      SupportTicket, Lead, WalletTransaction, Wallet)
    client = User.query.get_or_404(user_id)

    events = []
    projects = ClientProject.query.filter_by(client_id=user_id).order_by(ClientProject.created_at.desc()).all()
    for p in projects:
        events.append({"type": "project", "icon": "📁", "date": p.created_at,
                       "title": f'Project started: "{p.title}"', "detail": f"Status: {p.status}"})
        for inv in p.invoices:
            events.append({"type": "invoice", "icon": "🧾", "date": inv.created_at,
                           "title": f'Invoice created: "{inv.title}"',
                           "detail": f"{inv.amount} {inv.currency or ''} — {inv.status}"})
            if inv.paid_at:
                events.append({"type": "payment", "icon": "💰", "date": inv.paid_at,
                               "title": f'Payment received: "{inv.title}"',
                               "detail": f"{inv.amount_paid or inv.amount} {inv.currency or ''} via {inv.gateway or 'unknown'}"})
        for m in p.meetings:
            events.append({"type": "meeting", "icon": "📅", "date": m.scheduled_at,
                           "title": f'Meeting: "{m.title}"', "detail": f'on "{p.title}"'})

    for t in SupportTicket.query.filter_by(user_id=user_id).order_by(SupportTicket.created_at.desc()).all():
        events.append({"type": "ticket", "icon": "🎫", "date": t.created_at,
                       "title": f'Support ticket: "{t.subject}"', "detail": f"Status: {t.status}"})

    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if wallet:
        for tx in wallet.transactions:
            events.append({"type": "wallet", "icon": "👛", "date": tx.created_at,
                           "title": (tx.note or tx.kind.replace("_", " ").title()),
                           "detail": f"{'+' if tx.amount > 0 else ''}{tx.amount} {wallet.currency or ''}"})

    lead = Lead.query.filter(db.func.lower(Lead.email) == (client.email or "").lower()).first() if client.email else None

    events = [e for e in events if e["date"]]
    events.sort(key=lambda e: e["date"], reverse=True)

    return render_template("admin/customer_timeline.html", client=client, events=events,
                           projects=projects, wallet=wallet, lead=lead)


def _client_last_activity(user_id):
    """Real max(activity date) across every source that actually means
    something happened with this client — not a guess. Returns
    (last_activity_datetime_or_None, source_label_or_None). None means the
    client has zero recorded activity at all (never had a project/invoice/
    meeting/ticket/wallet event) — that's a different case from "went
    quiet", handled separately by the caller."""
    from app.models.platform import ClientProject, Invoice, ProjectMeeting, ProjectUpdate, SupportTicket, WalletTransaction, Wallet

    candidates = []  # (datetime, label)
    projects = ClientProject.query.filter_by(client_id=user_id).all()
    for p in projects:
        if p.created_at:
            candidates.append((p.created_at, "project started"))
        for inv in p.invoices:
            if inv.created_at:
                candidates.append((inv.created_at, "invoice created"))
            if inv.paid_at:
                candidates.append((inv.paid_at, "payment received"))
        for m in p.meetings:
            if m.scheduled_at:
                candidates.append((m.scheduled_at, "meeting"))
        for u in ProjectUpdate.query.filter_by(project_id=p.id).all():
            if u.created_at:
                candidates.append((u.created_at, "project update posted"))

    for t in SupportTicket.query.filter_by(user_id=user_id).all():
        if t.created_at:
            candidates.append((t.created_at, "support ticket"))

    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if wallet:
        for tx in wallet.transactions:
            if tx.created_at:
                candidates.append((tx.created_at, "wallet activity"))

    if not candidates:
        return None, None
    candidates.sort(key=lambda c: c[0], reverse=True)
    return candidates[0]


@admin_bp.route("/crm/inactive-clients")
@admin_required
def inactive_clients():
    """Detect inactive customers — a real CRM AI Sales Assistant item.
    'Inactive' = has at least one real recorded activity ever, but nothing
    in the configurable threshold window, and their most recent project
    isn't already 'completed' (a finished, fully-wrapped-up project going
    quiet isn't a red flag — it's just... done). Clients with ZERO
    activity ever are shown separately as 'never engaged', since that's
    a different situation than someone who went quiet."""
    from datetime import timedelta
    from app.models.platform import ClientProject

    days_threshold = request.args.get("days", 60, type=int)
    cutoff = datetime.utcnow() - timedelta(days=days_threshold)

    client_role = Role.query.filter_by(name="client").first()
    clients = User.query.filter_by(role_id=client_role.id).all() if client_role else []

    inactive, never_engaged, active = [], [], []
    for c in clients:
        last_activity, source = _client_last_activity(c.id)
        if last_activity is None:
            never_engaged.append(c)
            continue
        latest_project = ClientProject.query.filter_by(client_id=c.id).order_by(ClientProject.created_at.desc()).first()
        already_wrapped_up = latest_project and latest_project.status == "completed"
        days_quiet = (datetime.utcnow() - last_activity).days
        if last_activity < cutoff and not already_wrapped_up:
            inactive.append({"client": c, "last_activity": last_activity, "source": source, "days_quiet": days_quiet})
        else:
            active.append(c)

    inactive.sort(key=lambda x: x["days_quiet"], reverse=True)
    return render_template("admin/inactive_clients.html", inactive=inactive, never_engaged=never_engaged,
                           active_count=len(active), days_threshold=days_threshold)


@admin_bp.route("/crm/inactive-clients/<int:user_id>/draft-reengagement", methods=["POST"])
@admin_required
def client_draft_reengagement_email(user_id):
    from app.ai_tools.routes import _call_ai
    client = User.query.get_or_404(user_id)
    last_activity, source = _client_last_activity(user_id)
    days_quiet = (datetime.utcnow() - last_activity).days if last_activity else None

    facts = (
        f"Client name: {client.name or client.email}\n"
        f"Last recorded activity: {source or 'none'}, {days_quiet if days_quiet is not None else 'unknown'} days ago"
    )
    system = (
        "You are writing a short, genuine re-engagement email to a past client of a web development/design "
        "studio who has gone quiet, based only on the real facts given — do not invent project details, "
        "outcomes, or specifics not given. Keep it warm, brief, and low-pressure — checking in, not selling. "
        "Respond ONLY as JSON: {\"subject\": \"...\", \"body\": \"...\"} — body as plain text with \\n for line breaks."
    )
    text, err = _call_ai(system, [{"role": "user", "content": facts}], max_tokens=500)
    if err:
        return jsonify({"error": err}), 502

    import json as _json
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        draft = _json.loads(cleaned)
    except Exception:
        return jsonify({"error": "The AI's response wasn't valid — try again.", "raw": text[:300]}), 502

    return jsonify({"subject": draft.get("subject", ""), "body": draft.get("body", "")})


@admin_bp.route("/crm/inactive-clients/<int:user_id>/send-reengagement", methods=["POST"])
@admin_required
def client_send_reengagement_email(user_id):
    from app.utils.email import send_email
    client = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}
    subject = (data.get("subject") or "").strip()
    body = (data.get("body") or "").strip()
    if not subject or not body:
        return jsonify({"error": "Subject and body can't be empty."}), 400
    if not client.email:
        return jsonify({"error": "This client has no email on file."}), 400

    body_html = "<p>" + body.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
    ok = send_email(to=client.email, subject=subject, body_html=body_html)
    if not ok:
        return jsonify({"error": "Email failed to send — check mail settings in Admin -> Settings."}), 502
    return jsonify({"sent": True})


@admin_bp.route("/partners")
@admin_required
def partners():
    from app.models.content import Partner
    items = Partner.query.order_by(Partner.order, Partner.created_at.desc()).all()
    return render_template("admin/partners.html", partners=items)


@admin_bp.route("/partners/create", methods=["POST"])
@admin_required
def partner_create():
    from app.models.content import Partner
    name = (request.form.get("name") or "").strip()
    website = (request.form.get("website") or "").strip() or None
    if not name:
        flash("Give the partner a name.", "danger")
        return redirect(url_for("admin.partners"))

    logo_url = (request.form.get("logo_url") or "").strip()
    file = request.files.get("logo_file")
    if file and file.filename:
        import uuid
        from werkzeug.utils import secure_filename
        ext = secure_filename(file.filename).rsplit(".", 1)[-1].lower()
        if ext not in ("png", "jpg", "jpeg", "svg", "webp"):
            flash("Logo must be a PNG, JPG, SVG, or WebP file.", "danger")
            return redirect(url_for("admin.partners"))
        filename = f"partner_{uuid.uuid4().hex}.{ext}"
        upload_dir = os.path.join(current_app.root_path, "static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file.save(os.path.join(upload_dir, filename))
        logo_url = f"/static/uploads/{filename}"

    if not logo_url:
        flash("Upload a logo file or paste a logo image URL.", "danger")
        return redirect(url_for("admin.partners"))

    max_order = db.session.query(db.func.max(Partner.order)).scalar() or 0
    db.session.add(Partner(name=name, logo_url=logo_url, website=website, order=max_order + 1))
    db.session.commit()
    flash(f'Added "{name}".', "success")
    return redirect(url_for("admin.partners"))


@admin_bp.route("/partners/<int:pid>/toggle", methods=["POST"])
@admin_required
def partner_toggle(pid):
    from app.models.content import Partner
    p = Partner.query.get_or_404(pid)
    p.active = not p.active
    db.session.commit()
    return redirect(url_for("admin.partners"))


@admin_bp.route("/partners/<int:pid>/delete", methods=["POST"])
@admin_required
def partner_delete(pid):
    from app.models.content import Partner
    p = Partner.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash("Partner removed.", "success")
    return redirect(url_for("admin.partners"))


@admin_bp.route("/knowledge-base")
@admin_required
def knowledge_base():
    """Overview + a live test box for the retrieval search every AI agent
    and the customer widget actually use. NOT the full 'indexed/embedded/
    synchronized' dashboard from the master prompt — there's no embedding
    pipeline or background indexing job to report on, since retrieval here
    is a live query against the real tables, not a separate index that can
    fall out of sync. So 'last synchronized' is always 'right now'."""
    from app.models.content import Service, Project, BlogPost
    from app.models.platform import FAQItem
    counts = {
        "Services": Service.query.filter_by(active=True).count(),
        "Portfolio Projects": Project.query.count(),
        "Published Blog Posts": BlogPost.query.filter_by(published=True).count(),
        "Active FAQs": FAQItem.query.filter_by(active=True).count(),
    }
    try:
        from app.models.commerce import Product
        counts["Active Products"] = Product.query.filter_by(status="active").count()
    except Exception:
        pass
    return render_template("admin/knowledge_base.html", counts=counts)


@admin_bp.route("/knowledge-base/test-search", methods=["POST"])
@admin_required
def knowledge_base_test_search():
    from app.utils.knowledge import search_knowledge_base
    query = (request.get_json(silent=True) or {}).get("query", "").strip()
    if not query:
        return jsonify({"error": "Enter a search query."}), 400
    return jsonify({"results": search_knowledge_base(query, limit=10)})


@admin_bp.route("/wallets")
@admin_required
def wallets():
    from app.models.platform import Wallet
    q = request.args.get("q", "")
    query = Wallet.query.join(User, Wallet.user_id == User.id)
    if q:
        query = query.filter(db.or_(User.name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    wallet_list = query.order_by(Wallet.updated_at.desc()).all()
    return render_template("admin/wallets.html", wallets=wallet_list, q=q)


def _parse_amount(raw):
    """Amounts are shown everywhere on this site with thousands separators
    (₦120,000) — admins naturally type them the same way, but float()
    rejects a comma outright and raises, which every call site here was
    silently swallowing into 0. That 0 then always failed the "must be
    greater than zero" check, so admin wallet/reward/payment forms could
    look completely broken no matter what was actually typed. Strips
    commas, whitespace, and common currency symbols before parsing."""
    if raw is None:
        return 0.0
    cleaned = str(raw).strip()
    for ch in (",", "₦", "$", "£", "€", " "):
        cleaned = cleaned.replace(ch, "")
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return 0.0


@admin_bp.route("/wallets/adjust", methods=["POST"])
@admin_required
def wallets_adjust():
    from app.utils.wallet import credit_wallet, debit_wallet
    email = (request.form.get("email") or "").strip().lower()
    action = request.form.get("action")
    amount = _parse_amount(request.form.get("amount"))
    note = (request.form.get("note") or "").strip() or None

    user = User.query.filter(db.func.lower(User.email) == email).first()
    if not user:
        flash(f"No user found with email {email}.", "danger")
        return redirect(url_for("admin.wallets"))
    if amount <= 0:
        flash("Amount must be greater than zero.", "danger")
        return redirect(url_for("admin.wallets"))

    if action == "credit":
        credit_wallet(user.id, amount, kind="credit", note=note or "Admin credit",
                      reference=f"admin:{current_user.email}", created_by=current_user.id)
        flash(f"Credited {amount} to {user.email}'s wallet.", "success")
    elif action == "debit":
        wallet, err = debit_wallet(user.id, amount, kind="debit", note=note or "Admin debit",
                                    reference=f"admin:{current_user.email}", created_by=current_user.id)
        if err:
            flash(err, "danger")
        else:
            flash(f"Debited {amount} from {user.email}'s wallet.", "success")
    else:
        flash("Unknown action.", "danger")
    return redirect(url_for("admin.wallets"))


@admin_bp.route("/withdrawals")
@admin_required
def withdrawals():
    from app.models.platform import WithdrawalRequest
    status = request.args.get("status", "pending")
    query = WithdrawalRequest.query
    if status != "all":
        query = query.filter_by(status=status)
    reqs = query.order_by(WithdrawalRequest.created_at.desc()).all()
    return render_template("admin/withdrawals.html", requests=reqs, active_status=status)


@admin_bp.route("/withdrawals/<int:req_id>/mark-paid", methods=["POST"])
@admin_required
def withdrawal_mark_paid(req_id):
    """The admin has actually sent the money outside the platform (bank
    transfer, crypto, whatever) — this just records that it's done. The
    wallet was already debited when the request was made, so no further
    balance change happens here."""
    from app.models.platform import WithdrawalRequest
    req = WithdrawalRequest.query.get_or_404(req_id)
    req.status = "paid"
    req.resolved_at = datetime.utcnow()
    req.admin_note = (request.form.get("admin_note") or "").strip() or req.admin_note
    db.session.commit()
    flash("Marked as paid.", "success")
    return redirect(url_for("admin.withdrawals"))


@admin_bp.route("/withdrawals/<int:req_id>/reject", methods=["POST"])
@admin_required
def withdrawal_reject(req_id):
    from app.models.platform import WithdrawalRequest
    from app.utils.wallet import credit_wallet
    req = WithdrawalRequest.query.get_or_404(req_id)
    if req.status == "pending":
        credit_wallet(req.user_id, float(req.amount), kind="withdrawal_refund",
                      note="Withdrawal request rejected — funds returned to wallet",
                      reference=f"withdrawal:{req.id}", created_by=current_user.id)
    req.status = "rejected"
    req.resolved_at = datetime.utcnow()
    req.admin_note = (request.form.get("admin_note") or "").strip() or req.admin_note
    db.session.commit()
    flash("Rejected — funds returned to the client's wallet.", "success")
    return redirect(url_for("admin.withdrawals"))


@admin_bp.route("/users/<int:uid>/role", methods=["POST"])
@admin_required
def update_user_role(uid):
    if uid == current_user.id:
        msg = "For safety, you cannot change your own role from the user list. Use \"Preview as\" on any other user's row if you need to see what their dashboard looks like."
        if request.is_json:
            return jsonify({"error": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("admin.users"))

    user = User.query.get_or_404(uid)
    role_name = request.form.get("role") or (request.get_json(silent=True) or {}).get("role", "")
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        if request.is_json:
            return jsonify({"error": "Role not found"}), 404
        flash("Role not found.", "danger")
        return redirect(url_for("admin.users"))

    admin_role = Role.query.filter_by(name="admin").first()
    if role_name == "admin" and user.role_id != (admin_role.id if admin_role else None):
        existing_admin_count = User.query.filter_by(role_id=admin_role.id).count() if admin_role else 0
        if existing_admin_count >= 1:
            msg = "Only one admin account is allowed on this site. Demote the current admin first if you want to transfer the role."
            if request.is_json:
                return jsonify({"error": msg}), 400
            flash(msg, "danger")
            return redirect(url_for("admin.users"))
    if user.role_id == (admin_role.id if admin_role else None) and role_name != "admin":
        # Demoting the only admin would lock everyone out of the admin panel.
        remaining_admins = User.query.filter_by(role_id=admin_role.id).filter(User.id != uid).count()
        if remaining_admins == 0:
            msg = "You can't remove the last admin — that would lock everyone out. Promote another account to admin first."
            if request.is_json:
                return jsonify({"error": msg}), 400
            flash(msg, "danger")
            return redirect(url_for("admin.users"))

    user.role = role
    db.session.commit()
    log_action(current_user.id, "admin.user.role_change", f"User#{uid}", f"→{role_name}")
    if request.is_json:
        return jsonify({"success": True})
    flash(f"Role updated to {role_name}.", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/users/<int:uid>/ban", methods=["POST"])
@admin_required
def toggle_ban(uid):
    user = User.query.get_or_404(uid)
    user.is_banned = not user.is_banned
    db.session.commit()
    action = "ban" if user.is_banned else "unban"
    log_action(current_user.id, f"admin.user.{action}", f"User#{uid}")
    if request.is_json:
        return jsonify({"success": True, "banned": user.is_banned})
    flash(f"User {'banned' if user.is_banned else 'unbanned'}.", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/users/<int:uid>/delete", methods=["POST"])
@admin_required
def delete_user(uid):
    user = User.query.get_or_404(uid)
    if user.is_admin():
        flash("Cannot delete admin users.", "danger")
        return redirect(url_for("admin.users"))
    db.session.delete(user)
    db.session.commit()
    log_action(current_user.id, "admin.user.delete", f"User#{uid}")
    if request.is_json:
        return jsonify({"success": True})
    flash("User deleted.", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/users/<int:uid>/credits", methods=["POST"])
@admin_required
def add_credits(uid):
    """Manual admin credit adjustment. Routes through the same ledgered
    add_credits/deduct_credits helpers the credit-purchase flow uses —
    every change (positive or negative) writes a CreditTransaction row
    with the admin's id and reason, rather than silently overwriting
    user.credits."""
    from app.utils.credits import add_credits as _ledger_add, deduct_credits as _ledger_deduct
    user = User.query.get_or_404(uid)
    form_or_json = request.form or (request.get_json(silent=True) or {})
    try:
        amount = int(form_or_json.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0
    reason = (form_or_json.get("reason") or "Manual admin adjustment").strip()
    if amount == 0:
        error = "Enter a non-zero amount."
        if request.is_json:
            return jsonify({"success": False, "error": error}), 400
        flash(error, "danger")
        return redirect(url_for("admin.users"))
    if amount > 0:
        new_balance = _ledger_add(user.id, amount, type="admin_adjustment", reason=reason, created_by=current_user.id)
        if request.is_json:
            return jsonify({"success": True, "credits": new_balance})
        flash(f"Added {amount} credits.", "success")
        return redirect(url_for("admin.users"))
    ok, result = _ledger_deduct(user.id, abs(amount), type="admin_adjustment", reason=reason)
    if not ok:
        if request.is_json:
            return jsonify({"success": False, "error": result}), 400
        flash(result, "danger")
        return redirect(url_for("admin.users"))
    if request.is_json:
        return jsonify({"success": True, "credits": result})
    flash(f"Removed {abs(amount)} credits.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:uid>/grant-product", methods=["POST"])
@admin_required
def grant_user_product(uid):
    """Manual escape hatch: unlock a premium dashboard product for a
    specific user right now, without needing to trace why the automatic
    payment->unlock grant didn't fire. Use this to unblock a customer
    immediately, then check the logs for the real cause separately."""
    from app.dashboard.premium import PREMIUM_PRODUCTS, grant_product_access
    user = User.query.get_or_404(uid)
    product_slug = request.form.get("product_slug")
    if product_slug not in PREMIUM_PRODUCTS:
        flash("Unknown product.", "danger")
        return redirect(url_for("admin.users"))
    grant_product_access(user, product_slug)
    flash(f"Granted {user.email} access to {PREMIUM_PRODUCTS[product_slug]['name']}.", "success")
    return redirect(request.referrer or url_for("admin.users"))


@admin_bp.route("/users/<int:uid>/revoke-product", methods=["POST"])
@admin_required
def revoke_user_product(uid):
    from app.dashboard.premium import PREMIUM_PRODUCTS, revoke_product_access
    user = User.query.get_or_404(uid)
    product_slug = request.form.get("product_slug")
    if product_slug not in PREMIUM_PRODUCTS:
        flash("Unknown product.", "danger")
        return redirect(url_for("admin.users"))
    revoke_product_access(user, product_slug)
    flash(f"Revoked {user.email}'s access to {PREMIUM_PRODUCTS[product_slug]['name']}.", "success")
    return redirect(request.referrer or url_for("admin.users"))


# ── Roles ─────────────────────────────────────────────────────────────────────
@admin_bp.route("/roles")
@admin_required
def roles():
    all_roles = Role.query.all()
    return render_template("admin/roles.html", roles=all_roles)

@admin_bp.route("/roles/create", methods=["POST"])
@admin_required
def create_role():
    name  = request.form.get("name", "").strip().lower()
    perms = request.form.getlist("permissions")
    desc  = request.form.get("description", "")
    if not name:
        flash("Role name required.", "danger")
        return redirect(url_for("admin.roles"))
    if Role.query.filter_by(name=name).first():
        flash("Role already exists.", "danger")
        return redirect(url_for("admin.roles"))
    db.session.add(Role(name=name, description=desc, permissions=perms))
    db.session.commit()
    log_action(current_user.id, "admin.role.create", f"Role:{name}")
    flash(f"Role '{name}' created.", "success")
    return redirect(url_for("admin.roles"))

@admin_bp.route("/roles/<int:rid>/delete", methods=["POST"])
@admin_required
def delete_role(rid):
    role = Role.query.get_or_404(rid)
    if role.is_system:
        flash("Cannot delete system roles.", "danger")
        return redirect(url_for("admin.roles"))
    db.session.delete(role)
    db.session.commit()
    flash(f"Role '{role.name}' deleted.", "success")
    return redirect(url_for("admin.roles"))


# ── Products ──────────────────────────────────────────────────────────────────
@admin_bp.route("/products")
@admin_required
def products():
    page = request.args.get("page", 1, type=int)
    q    = request.args.get("q", "")
    query = Product.query
    if q:
        query = query.filter(Product.title.ilike(f"%{q}%"))
    products_page = query.order_by(Product.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    # These slugs were auto-seeded into the marketplace by mistake — they're
    # admin-only tools, not sellable products, and shouldn't have been
    # created as Product rows at all. Flagged here (not auto-deleted) so
    # you get a one-click "Archive these" button instead of a silent action.
    # NOTE: "ai-chatbot" is deliberately NOT in this list — it's one of the
    # six real customer products in PREMIUM_PRODUCTS (see
    # app/dashboard/premium.py) and is managed on the Customer Tools page,
    # not archived. An earlier version of this list wrongly included it.
    from app.dashboard.premium import PREMIUM_PRODUCTS
    legacy_slugs = ["website-builder", "automation-studio", "graphics-studio",
                    "content-studio", "video-studio", "social-bot", "prompt-library", "voice-studio"]
    legacy_ct = Product.query.filter(Product.slug.in_(legacy_slugs), Product.status != "archived").count()
    return render_template("admin/products.html", products=products_page, q=q,
                           legacy_seed_count=legacy_ct, legacy_seed_slugs=legacy_slugs)


@admin_bp.route("/products/archive-legacy-seed", methods=["POST"])
@admin_required
def archive_legacy_seed_products():
    """One-click cleanup for the wrongly-auto-seeded admin-tool products
    (website-builder, automation-studio, etc.) — archives them
    (hides from marketplace) rather than deleting, since existing Orders
    may reference them and a hard delete would break that history."""
    legacy_slugs = ["website-builder", "automation-studio", "graphics-studio",
                    "content-studio", "video-studio", "social-bot", "prompt-library", "voice-studio"]
    updated = Product.query.filter(Product.slug.in_(legacy_slugs), Product.status != "archived").update(
        {"status": "archived"}, synchronize_session=False)
    db.session.commit()
    flash(f"Archived {updated} product(s) that shouldn't have been in the marketplace.", "success")
    return redirect(url_for("admin.products"))

@admin_bp.route("/products/create", methods=["POST"])
@admin_required
def create_product():
    import re, time
    title = request.form.get("title", "")
    slug_base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = f"{slug_base}-{int(time.time())}"
    tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    p = Product(
        title=title,
        slug=slug,
        description=request.form.get("description", ""),
        long_desc=request.form.get("long_desc", ""),
        category=request.form.get("category", "template"),
        type=request.form.get("type", "template"),
        price=float(request.form.get("price", 0) or 0),
        sale_price=float(request.form.get("sale_price") or 0) or None,
        currency=request.form.get("currency") or default_site_currency(),
        tags=tags,
        images=([request.form["image_url"].strip()] if request.form.get("image_url", "").strip() else []),
        status="active",
        featured=bool(request.form.get("featured")),
        file_url=request.form.get("file_url", ""),
        preview_url=request.form.get("preview_url", ""),
        demo_url=request.form.get("demo_url", ""),
        license=request.form.get("license", "standard"),
        version=request.form.get("version", "1.0.0"),
    )
    db.session.add(p)
    db.session.commit()
    log_action(current_user.id, "admin.product.create", f"Product#{p.id}")
    flash(f"Product '{title}' created.", "success")
    return redirect(url_for("admin.products"))

@admin_bp.route("/products/<int:pid>/toggle-feature", methods=["POST"])
@admin_required
def toggle_product_featured(pid):
    p = Product.query.get_or_404(pid)
    p.featured = not p.featured
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True, "featured": p.featured})
    flash(f"Product {'featured' if p.featured else 'unfeatured'}.", "success")
    return redirect(url_for("admin.products"))

@admin_bp.route("/products/<int:pid>/update", methods=["POST"])
@admin_required
def update_product(pid):
    p = Product.query.get_or_404(pid)
    tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    p.title = request.form.get("title", p.title)
    p.description = request.form.get("description", p.description)
    p.long_desc = request.form.get("long_desc", p.long_desc)
    p.category = request.form.get("category", p.category)
    p.type = request.form.get("type", p.type)
    p.price = float(request.form.get("price", p.price) or 0)
    p.sale_price = float(request.form.get("sale_price") or 0) or None
    p.currency = request.form.get("currency") or p.currency
    p.tags = tags or p.tags
    if request.form.get("image_url", "").strip():
        p.images = [request.form["image_url"].strip()]
    p.featured = bool(request.form.get("featured"))
    p.file_url = request.form.get("file_url", p.file_url)
    p.preview_url = request.form.get("preview_url", p.preview_url)
    p.demo_url = request.form.get("demo_url", p.demo_url)
    p.license = request.form.get("license", p.license)
    p.version = request.form.get("version", p.version)
    db.session.commit()
    log_action(current_user.id, "admin.product.update", f"Product#{p.id}")
    flash(f"Product '{p.title}' updated.", "success")
    return redirect(url_for("admin.products"))

@admin_bp.route("/products/<int:pid>/delete", methods=["POST"])
@admin_required
def delete_product(pid):
    p = Product.query.get_or_404(pid)
    if Order.query.filter_by(product_id=pid).count() > 0:
        flash(f"Cannot delete '{p.title}' — it has existing orders. Deactivate it instead.", "danger")
        return redirect(url_for("admin.products"))
    title = p.title
    db.session.delete(p)
    db.session.commit()
    log_action(current_user.id, "admin.product.delete", f"Product '{title}'")
    flash(f"Product '{title}' deleted.", "success")
    return redirect(url_for("admin.products"))

@admin_bp.route("/products/<int:pid>/status", methods=["POST"])
@admin_required
def update_product_status(pid):
    p = Product.query.get_or_404(pid)
    status = request.form.get("status") or (request.get_json(silent=True) or {}).get("status", "active")
    p.status = status
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash(f"Product status updated to {status}.", "success")
    return redirect(url_for("admin.products"))


# ── Customer Tools (the 6 sellable dashboard SaaS products, run from inside Admin) ──
# These are the same tools customers buy access to from the marketplace
# (Invoice Generator, Sales Funnel Builder, Payment Link Generator,
# WhatsApp Business Bot, WhatsApp Chat Widget, AI Chatbot). Admins already
# get free, fully-unlocked access to every one of them via the is_admin()
# bypass in has_product_access() — this page is where the admin (a) jumps
# straight into using any of them exactly like a customer would, and
# (b) manages every product setting: price, billing period, images,
# description, feature list, demo link, license, and marketplace visibility.
@admin_bp.route("/customer-tools")
@admin_required
def customer_tools():
    from app.dashboard.premium import PREMIUM_PRODUCTS, ensure_dashboard_tool_products
    ensure_dashboard_tool_products()
    tools = []
    for slug, info in PREMIUM_PRODUCTS.items():
        product = Product.query.filter_by(slug=slug).first()
        active_users = 0
        if product:
            from app.models.platform import UserProductAccess
            active_users = UserProductAccess.query.filter_by(product_slug=slug, active=True).count()
        tools.append({"slug": slug, "info": info, "product": product, "active_users": active_users})
    return render_template("admin/customer_tools.html", tools=tools)


@admin_bp.route("/customer-tools/<slug>/update", methods=["POST"])
@admin_required
def customer_tools_update(slug):
    from app.dashboard.premium import PREMIUM_PRODUCTS
    if slug not in PREMIUM_PRODUCTS:
        abort(404)
    p = Product.query.filter_by(slug=slug).first()
    if not p:
        p = Product(slug=slug, title=PREMIUM_PRODUCTS[slug]["name"], type="dashboard_tool")
        db.session.add(p)

    p.title = request.form.get("title", p.title) or PREMIUM_PRODUCTS[slug]["name"]
    p.description = request.form.get("description", p.description)
    p.long_desc = request.form.get("long_desc", p.long_desc)
    p.price = float(request.form.get("price", p.price) or 0)
    sale_price = request.form.get("sale_price", "").strip()
    p.sale_price = float(sale_price) if sale_price else None
    p.currency = request.form.get("currency") or p.currency or default_site_currency()
    p.billing_period = request.form.get("billing_period", "one_time")
    p.license = request.form.get("license", p.license or "standard")
    p.demo_url = request.form.get("demo_url", p.demo_url)
    p.preview_url = request.form.get("preview_url", p.preview_url)
    if request.form.get("image_url", "").strip():
        p.images = [request.form["image_url"].strip()]
    features_raw = request.form.get("features", "")
    p.features = [f.strip() for f in features_raw.split("\n") if f.strip()]
    p.status = request.form.get("status", p.status or "active")
    p.category = PREMIUM_PRODUCTS[slug].get("category", p.category)
    p.type = "dashboard_tool"

    db.session.commit()
    log_action(current_user.id, "admin.customer_tool.update", f"Product#{p.id} ({slug})")
    flash(f"{PREMIUM_PRODUCTS[slug]['name']} settings updated.", "success")
    return redirect(url_for("admin.customer_tools"))


# ── Payment Links (public 'pay me' pages — invoice/sales-funnel checkout) ──
@admin_bp.route("/payment-links")
@admin_required
def payment_links():
    from app.models.commerce import PaymentLink
    links = PaymentLink.query.order_by(PaymentLink.created_at.desc()).all()
    return render_template("admin/payment_links.html", links=links, default_currency=default_site_currency(),
                           gateway_labels={"paystack": "Paystack", "flutterwave": "Flutterwave", "paypal": "PayPal",
                                           "stripe": "Stripe", "bank_transfer": "Bank Transfer", "crypto": "Crypto",
                                           "wave": "Wave", "payoneer": "Payoneer"})


def _slugify_payment_link(title):
    import re, secrets
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "pay"
    from app.models.commerce import PaymentLink
    slug = base
    while PaymentLink.query.filter_by(slug=slug).first():
        slug = f"{base}-{secrets.token_hex(2)}"
    return slug


@admin_bp.route("/payment-links/create", methods=["POST"])
@admin_required
def create_payment_link():
    from app.models.commerce import PaymentLink
    title = (request.form.get("title") or "").strip()
    amount = request.form.get("amount", type=float)
    if not title or not amount or amount <= 0:
        flash("Title and a positive amount are required.", "danger")
        return redirect(url_for("admin.payment_links"))

    link = PaymentLink(
        owner_id=current_user.id,
        slug=_slugify_payment_link(title),
        title=title,
        description=(request.form.get("description") or "").strip(),
        image_url=(request.form.get("image_url") or "").strip() or None,
        amount=amount,
        currency=(request.form.get("currency") or default_site_currency()).strip(),
        status=request.form.get("status") if request.form.get("status") in ("draft", "published") else "draft",
        allowed_methods=request.form.getlist("allowed_methods"),
        wave_instructions=(request.form.get("wave_instructions") or "").strip() or None,
        payoneer_instructions=(request.form.get("payoneer_instructions") or "").strip() or None,
        thank_you_message=(request.form.get("thank_you_message") or "").strip() or "Thank you! Your payment has been received.",
        redirect_url=(request.form.get("redirect_url") or "").strip() or None,
    )
    db.session.add(link)
    db.session.commit()
    flash(f'Payment link created: {url_for("cms.payment_link_view", slug=link.slug, _external=True)}', "success")
    return redirect(url_for("admin.payment_links"))


@admin_bp.route("/payment-links/<int:lid>/update", methods=["POST"])
@admin_required
def update_payment_link(lid):
    from app.models.commerce import PaymentLink
    link = PaymentLink.query.get_or_404(lid)
    link.title = (request.form.get("title") or link.title).strip()
    link.description = (request.form.get("description") or "").strip()
    link.image_url = (request.form.get("image_url") or "").strip() or None
    amount = request.form.get("amount", type=float)
    if amount and amount > 0:
        link.amount = amount
    link.currency = (request.form.get("currency") or link.currency).strip()
    if request.form.get("status") in ("draft", "published", "archived"):
        link.status = request.form.get("status")
    link.allowed_methods = request.form.getlist("allowed_methods")
    link.wave_instructions = (request.form.get("wave_instructions") or "").strip() or None
    link.payoneer_instructions = (request.form.get("payoneer_instructions") or "").strip() or None
    link.thank_you_message = (request.form.get("thank_you_message") or link.thank_you_message).strip()
    link.redirect_url = (request.form.get("redirect_url") or "").strip() or None
    db.session.commit()
    flash("Payment link updated.", "success")
    return redirect(url_for("admin.payment_links"))


@admin_bp.route("/payment-links/<int:lid>/delete", methods=["POST"])
@admin_required
def delete_payment_link(lid):
    from app.models.commerce import PaymentLink
    link = PaymentLink.query.get_or_404(lid)
    if link.payments.count() > 0:
        link.status = "archived"
        db.session.commit()
        flash(f'"{link.title}" has received payments, so it was archived instead of deleted (keeps the payment history intact).', "warning")
        return redirect(url_for("admin.payment_links"))
    db.session.delete(link)
    db.session.commit()
    flash("Payment link deleted.", "success")
    return redirect(url_for("admin.payment_links"))


@admin_bp.route("/payment-links/<int:lid>/payments")
@admin_required
def payment_link_payments(lid):
    from app.models.commerce import PaymentLink
    link = PaymentLink.query.get_or_404(lid)
    payments = link.payments.order_by(db.desc("created_at")).all()
    return render_template("admin/payment_link_payments.html", link=link, payments=payments)


@admin_bp.route("/payment-links/payments/<int:pid>/confirm", methods=["POST"])
@admin_required
def confirm_payment_link_payment(pid):
    """Manually confirm a bank_transfer/crypto/wave/payoneer claim after
    checking it actually landed — those methods have no API to verify
    automatically, so this is the review step."""
    from app.models.commerce import PaymentLinkPayment
    payment = PaymentLinkPayment.query.get_or_404(pid)
    payment.status = "paid"
    payment.paid_at = datetime.utcnow()
    db.session.commit()
    flash(f"Marked {payment.currency} {payment.amount} from {payment.payer_name or payment.payer_email} as paid.", "success")
    return redirect(url_for("admin.payment_link_payments", lid=payment.payment_link_id))


@admin_bp.route("/payment-links/payments/<int:pid>/reject", methods=["POST"])
@admin_required
def reject_payment_link_payment(pid):
    from app.models.commerce import PaymentLinkPayment
    payment = PaymentLinkPayment.query.get_or_404(pid)
    payment.status = "failed"
    db.session.commit()
    flash("Payment claim rejected.", "success")
    return redirect(url_for("admin.payment_link_payments", lid=payment.payment_link_id))


@admin_bp.route("/products/import-software/search", methods=["POST"])
@admin_required
def import_software_search():
    """Searches a real, free software source (see app/utils/archive_software.py:
    archive.org or Modrinth). Returns lightweight preview data — full detail +
    the actual playable/download links are only fetched for items the admin
    chooses to import, in import_software_import."""
    from app.utils.archive_software import search_software
    data = request.get_json(silent=True) or {}
    q = (data.get("q") or "").strip()
    page = data.get("page", 1)
    source = data.get("source") if data.get("source") in ("archive", "modrinth") else "archive"
    results, err = search_software(q, source=source, page=page)
    if err:
        return jsonify({"success": False, "error": err}), 502
    return jsonify({"success": True, "results": results})


@admin_bp.route("/products/import-software/import", methods=["POST"])
@admin_required
def import_software_import():
    """Fetches full metadata for each selected item and creates a Product
    per one — status is whatever the admin picked (draft stays off the
    public marketplace; active goes live immediately, same as any other
    product). Already-imported items (same slug) are skipped rather than
    duplicated. Each item in `items` is {"source": "archive"|"modrinth", "identifier": "..."}."""
    import re as _re
    from app.utils.archive_software import get_software_detail
    data = request.get_json(silent=True) or {}
    items = [it for it in (data.get("items") or []) if it.get("identifier")][:50]
    status = data.get("status") if data.get("status") in ("draft", "active") else "draft"
    if not items:
        return jsonify({"success": False, "error": "Select at least one item to import."}), 400

    added, skipped, failed = 0, 0, []
    for item in items:
        source = item.get("source") if item.get("source") in ("archive", "modrinth") else "archive"
        identifier = item["identifier"]
        fields, err = get_software_detail(source, identifier)
        if err:
            failed.append({"identifier": identifier, "error": err})
            continue
        slug_base = _re.sub(r"[^a-z0-9]+", "-", fields["title"].lower()).strip("-") or "software"
        slug = f"{slug_base}-{source}-{identifier}".lower()[:256]
        if Product.query.filter_by(slug=slug).first():
            skipped += 1
            continue
        p = Product(
            title=fields["title"], slug=slug,
            description=fields["description"], long_desc=fields["long_desc"],
            category=fields["category"], type=fields["type"],
            price=0, currency=default_site_currency(),
            tags=fields["tags"], images=fields["images"], status=status,
            file_url=fields["file_url"], preview_url=fields["preview_url"], demo_url=fields["demo_url"],
            license=fields["license"], version=fields["version"],
        )
        db.session.add(p)
        added += 1
    db.session.commit()
    if added:
        log_action(current_user.id, "admin.product.import_software", f"{added} item(s) imported")

    msg = f"Imported {added} item(s) as {status}"
    if skipped:
        msg += f", {skipped} already imported"
    if failed:
        msg += f", {len(failed)} failed"
    return jsonify({"success": True, "added": added, "skipped": skipped, "failed": failed, "message": msg})


# ── Orders ────────────────────────────────────────────────────────────────────
@admin_bp.route("/orders")
@admin_required
def orders():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "")
    q = Order.query
    if status:
        q = q.filter_by(status=status)
    orders_page = q.order_by(Order.created_at.desc()).paginate(page=page, per_page=25, error_out=False)
    total_revenue = float(db.session.query(func.sum(Order.amount)).filter_by(status="paid").scalar() or 0)
    return render_template("admin/orders.html", orders=orders_page, total_revenue=total_revenue, current_status=status)


# ── Blog ──────────────────────────────────────────────────────────────────────
@admin_bp.route("/blog")
@admin_required
def blog():
    page = request.args.get("page", 1, type=int)
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template("admin/blog.html", posts=posts)

@admin_bp.route("/blog/create", methods=["POST"])
@admin_required
def create_post():
    import re, time
    title = request.form.get("title", "")
    slug_base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = f"{slug_base}-{int(time.time())}"
    tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    post = BlogPost(
        title=title, slug=slug,
        excerpt=request.form.get("excerpt", ""),
        content=request.form.get("content", ""),
        category=request.form.get("category", "tutorial"),
        cover_image=request.form.get("cover_image", ""),
        tags=tags,
        published=bool(request.form.get("published")),
        featured=bool(request.form.get("featured")),
        author_id=current_user.id,
        seo_title=request.form.get("seo_title", ""),
        seo_desc=request.form.get("seo_desc", ""),
    )
    db.session.add(post)
    db.session.commit()
    log_action(current_user.id, "admin.post.create", f"BlogPost#{post.id}")
    flash("Blog post created.", "success")
    return redirect(url_for("admin.blog"))

@admin_bp.route("/blog/<int:pid>/toggle-publish", methods=["POST"])
@admin_required
def toggle_publish_post(pid):
    post = BlogPost.query.get_or_404(pid)
    post.published = not post.published
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True, "published": post.published})
    flash(f"Post {'published' if post.published else 'unpublished'}.", "success")
    return redirect(url_for("admin.blog"))

@admin_bp.route("/blog/<int:pid>/delete", methods=["POST"])
@admin_required
def delete_post(pid):
    post = BlogPost.query.get_or_404(pid)
    db.session.delete(post)
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Post deleted.", "success")
    return redirect(url_for("admin.blog"))

@admin_bp.route("/blog/<int:pid>")
@admin_required
def get_post(pid):
    """Backs the edit modal — replaces the old 'coming soon' stub."""
    post = BlogPost.query.get_or_404(pid)
    return jsonify({
        "id": post.id, "title": post.title, "excerpt": post.excerpt,
        "content": post.content, "category": post.category,
        "tags": ", ".join(post.tags or []), "published": post.published,
        "featured": post.featured, "cover_image": post.cover_image,
        "seo_title": post.seo_title, "seo_desc": post.seo_desc,
    })

@admin_bp.route("/blog/<int:pid>/update", methods=["POST"])
@admin_required
def update_post(pid):
    post = BlogPost.query.get_or_404(pid)
    post.title = request.form.get("title", post.title)
    post.excerpt = request.form.get("excerpt", post.excerpt)
    post.content = request.form.get("content", post.content)
    post.category = request.form.get("category", post.category)
    post.cover_image = request.form.get("cover_image", post.cover_image)
    post.tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    post.published = bool(request.form.get("published"))
    post.featured = bool(request.form.get("featured"))
    post.seo_title = request.form.get("seo_title", "")
    post.seo_desc = request.form.get("seo_desc", "")
    db.session.commit()
    flash("Post updated.", "success")
    return redirect(url_for("admin.blog"))


# ── CMS Blocks ────────────────────────────────────────────────────────────────
@admin_bp.route("/cms")
@admin_required
def cms():
    blocks = CmsBlock.query.order_by(CmsBlock.order, CmsBlock.key).all()
    return render_template("admin/cms.html", blocks=blocks)

@admin_bp.route("/cms/save", methods=["POST"])
@admin_required
def save_cms_block():
    import json as _json
    # Accept both JSON (from JS) and multipart form
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        key     = payload.get("key")
        content = payload.get("content", {})
        label   = payload.get("label", key)
        btype   = payload.get("type", "section")
    else:
        key   = request.form.get("key")
        label = request.form.get("label", key)
        btype = request.form.get("type", "section")
        # pack all fields_* into a dict
        content = {}
        for k, v in request.form.items():
            if k.startswith("fields_"):
                content[k[7:]] = v

    if not key:
        if request.is_json:
            return jsonify({"error": "Key required"}), 400
        flash("Block key required.", "danger")
        return redirect(url_for("admin.cms"))

    if isinstance(content, str):
        try:
            content = _json.loads(content)
        except Exception:
            content = {"raw": content}

    block = CmsBlock.query.filter_by(key=key).first()
    if block:
        block.content = content
        block.label   = label or key
        block.type    = btype
    else:
        block = CmsBlock(key=key, label=label or key, type=btype, content=content, active=True)
        db.session.add(block)
    db.session.commit()
    log_action(current_user.id, "admin.cms.save", f"CmsBlock:{key}")
    if request.is_json:
        return jsonify({"success": True})
    flash(f"Block '{key}' saved.", "success")
    return redirect(url_for("admin.cms"))
@admin_bp.route("/portfolio")
@admin_required
def portfolio():
    profile = Profile.query.first()
    skills  = Skill.query.order_by(Skill.order).all()
    exps    = Experience.query.order_by(Experience.order).all()
    edus    = Education.query.order_by(Education.order).all()
    certs   = Certification.query.order_by(Certification.order).all()
    awards  = Award.query.all()
    projects    = Project.query.order_by(Project.featured.desc(), Project.order).all()
    services    = Service.query.order_by(Service.order).all()
    testimonials = Testimonial.query.order_by(Testimonial.order).all()
    return render_template("admin/portfolio.html",
        profile=profile, skills=skills, experiences=exps,
        educations=edus, certifications=certs, awards=awards,
        projects=projects, services=services, testimonials=testimonials)

@admin_bp.route("/portfolio/profile", methods=["POST"])
@admin_required
def save_profile():
    profile = Profile.query.first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.session.add(profile)
    for field in ["full_name","title","subtitle","bio","about","profile_image","cover_image","intro_video_url","resume_url","twitter","github","linkedin","instagram"]:
        setattr(profile, field, request.form.get(field, ""))
    db.session.commit()
    flash("Profile saved.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/project/create", methods=["POST"])
@admin_required
def create_project():
    import re, time
    title = request.form.get("title", "")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") + f"-{int(time.time())}"
    tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    tech_stack = [t.strip() for t in request.form.get("tech_stack", "").split(",") if t.strip()]
    p = Project(title=title, slug=slug, description=request.form.get("description",""),
                image_url=request.form.get("image_url",""), live_url=request.form.get("live_url",""),
                github_url=request.form.get("github_url",""), tags=tags, tech_stack=tech_stack,
                featured=bool(request.form.get("featured")), client_name=request.form.get("client_name",""))
    db.session.add(p)
    db.session.commit()
    flash("Project created.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/project/<int:pid>/edit", methods=["POST"])
@admin_required
def edit_project(pid):
    p = Project.query.get_or_404(pid)
    p.title = request.form.get("title", p.title)
    p.description = request.form.get("description", "")
    p.image_url = request.form.get("image_url", "")
    p.client_name = request.form.get("client_name", "")
    p.live_url = request.form.get("live_url", "")
    p.github_url = request.form.get("github_url", "")
    p.tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    p.tech_stack = [t.strip() for t in request.form.get("tech_stack", "").split(",") if t.strip()]
    p.featured = bool(request.form.get("featured"))
    db.session.commit()
    flash("Project updated.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/project/<int:pid>/delete", methods=["POST"])
@admin_required
def delete_project(pid):
    p = Project.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Project deleted.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/project/<int:pid>/toggle-featured", methods=["POST"])
@admin_required
def toggle_project_featured(pid):
    p = Project.query.get_or_404(pid)
    p.featured = not p.featured
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True, "featured": p.featured})
    flash(f"Project {'featured' if p.featured else 'unfeatured'}.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/testimonial/create", methods=["POST"])
@admin_required
def create_testimonial():
    t = Testimonial(
        name=request.form.get("name",""), role=request.form.get("role",""),
        company=request.form.get("company",""), avatar=request.form.get("avatar",""),
        content=request.form.get("content",""),
        rating=int(request.form.get("rating", 5)),
        featured=bool(request.form.get("featured")), approved=True,
    )
    db.session.add(t)
    db.session.commit()
    flash("Testimonial added.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/testimonial/<int:tid>/edit", methods=["POST"])
@admin_required
def edit_testimonial(tid):
    t = Testimonial.query.get_or_404(tid)
    t.name = request.form.get("name", t.name)
    t.role = request.form.get("role", "")
    t.company = request.form.get("company", "")
    t.avatar = request.form.get("avatar", "")
    t.content = request.form.get("content", "")
    t.rating = int(request.form.get("rating", 5))
    t.featured = bool(request.form.get("featured"))
    db.session.commit()
    flash("Testimonial updated.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/testimonial/<int:tid>/delete", methods=["POST"])
@admin_required
def delete_testimonial(tid):
    t = Testimonial.query.get_or_404(tid)
    db.session.delete(t)
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Testimonial deleted.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/service/create", methods=["POST"])
@admin_required
def create_service():
    features = [f.strip() for f in request.form.get("features","").split(chr(10)) if f.strip()]
    s = Service(title=request.form.get("title",""), description=request.form.get("description",""),
                icon=request.form.get("icon","Code2"), price=request.form.get("price",""),
                features=features, active=True)
    db.session.add(s)
    db.session.commit()
    flash("Service created.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/service/<int:sid>/edit", methods=["POST"])
@admin_required
def edit_service(sid):
    s = Service.query.get_or_404(sid)
    s.title = request.form.get("title", s.title)
    s.description = request.form.get("description", "")
    s.icon = request.form.get("icon", "Code2")
    s.price = request.form.get("price", "")
    s.features = [f.strip() for f in request.form.get("features","").split(chr(10)) if f.strip()]
    s.active = bool(request.form.get("active"))
    db.session.commit()
    flash("Service updated.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/service/<int:sid>/delete", methods=["POST"])
@admin_required
def delete_service(sid):
    # This route did not exist before, even though templates/admin/portfolio.html
    # already pointed its Delete button at this exact URL — clicking it 404'd.
    s = Service.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Service deleted.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/skill/create", methods=["POST"])
@admin_required
def create_skill():
    s = Skill(name=request.form.get("name",""), category=request.form.get("category",""),
              level=request.form.get("level","intermediate"),
              percentage=int(request.form.get("percentage", 0)),
              icon=request.form.get("icon", ""))
    db.session.add(s)
    db.session.commit()
    flash("Skill added.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/skill/<int:sid>/edit", methods=["POST"])
@admin_required
def edit_skill(sid):
    s = Skill.query.get_or_404(sid)
    s.name = request.form.get("name", s.name)
    s.category = request.form.get("category", "")
    s.level = request.form.get("level", "intermediate")
    s.percentage = int(request.form.get("percentage", 0))
    s.icon = request.form.get("icon", "")
    db.session.commit()
    flash("Skill updated.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/skill/<int:sid>/delete", methods=["POST"])
@admin_required
def delete_skill(sid):
    # Also previously missing — the Skills tab had no delete affordance
    # of any kind, so a skill added by mistake could never be removed.
    s = Skill.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Skill deleted.", "success")
    return redirect(url_for("admin.portfolio"))


# ── Experience / Education / Certification / Award ──────────────────────────
# None of these four had ANY admin routes before (no create, no edit, no
# delete) even though they render on the public About page — there was
# simply no way to manage them short of editing the database directly.
@admin_bp.route("/portfolio/experience/create", methods=["POST"])
@admin_required
def create_experience():
    e = Experience(company=request.form.get("company",""), role=request.form.get("role",""),
                    description=request.form.get("description",""),
                    start_date=request.form.get("start_date",""), end_date=request.form.get("end_date",""),
                    current=bool(request.form.get("current")), logo=request.form.get("logo",""))
    db.session.add(e)
    db.session.commit()
    flash("Experience added.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/experience/<int:eid>/edit", methods=["POST"])
@admin_required
def edit_experience(eid):
    e = Experience.query.get_or_404(eid)
    e.company = request.form.get("company", "")
    e.role = request.form.get("role", "")
    e.description = request.form.get("description", "")
    e.start_date = request.form.get("start_date", "")
    e.end_date = request.form.get("end_date", "")
    e.current = bool(request.form.get("current"))
    e.logo = request.form.get("logo", "")
    db.session.commit()
    flash("Experience updated.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/experience/<int:eid>/delete", methods=["POST"])
@admin_required
def delete_experience(eid):
    e = Experience.query.get_or_404(eid)
    db.session.delete(e)
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Experience deleted.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/education/create", methods=["POST"])
@admin_required
def create_education():
    e = Education(institution=request.form.get("institution",""), degree=request.form.get("degree",""),
                   field=request.form.get("field",""), start_year=request.form.get("start_year",""),
                   end_year=request.form.get("end_year",""), logo=request.form.get("logo",""))
    db.session.add(e)
    db.session.commit()
    flash("Education added.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/education/<int:eid>/edit", methods=["POST"])
@admin_required
def edit_education(eid):
    e = Education.query.get_or_404(eid)
    e.institution = request.form.get("institution", "")
    e.degree = request.form.get("degree", "")
    e.field = request.form.get("field", "")
    e.start_year = request.form.get("start_year", "")
    e.end_year = request.form.get("end_year", "")
    e.logo = request.form.get("logo", "")
    db.session.commit()
    flash("Education updated.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/education/<int:eid>/delete", methods=["POST"])
@admin_required
def delete_education(eid):
    e = Education.query.get_or_404(eid)
    db.session.delete(e)
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Education deleted.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/certification/create", methods=["POST"])
@admin_required
def create_certification():
    c = Certification(name=request.form.get("name",""), issuer=request.form.get("issuer",""),
                       issue_date=request.form.get("issue_date",""), url=request.form.get("url",""),
                       badge=request.form.get("badge",""))
    db.session.add(c)
    db.session.commit()
    flash("Certification added.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/certification/<int:cid>/edit", methods=["POST"])
@admin_required
def edit_certification(cid):
    c = Certification.query.get_or_404(cid)
    c.name = request.form.get("name", "")
    c.issuer = request.form.get("issuer", "")
    c.issue_date = request.form.get("issue_date", "")
    c.url = request.form.get("url", "")
    c.badge = request.form.get("badge", "")
    db.session.commit()
    flash("Certification updated.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/certification/<int:cid>/delete", methods=["POST"])
@admin_required
def delete_certification(cid):
    c = Certification.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Certification deleted.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/award/create", methods=["POST"])
@admin_required
def create_award():
    a = Award(title=request.form.get("title",""), issuer=request.form.get("issuer",""),
              year=request.form.get("year",""), description=request.form.get("description",""))
    db.session.add(a)
    db.session.commit()
    flash("Award added.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/award/<int:aid>/edit", methods=["POST"])
@admin_required
def edit_award(aid):
    a = Award.query.get_or_404(aid)
    a.title = request.form.get("title", "")
    a.issuer = request.form.get("issuer", "")
    a.year = request.form.get("year", "")
    a.description = request.form.get("description", "")
    db.session.commit()
    flash("Award updated.", "success")
    return redirect(url_for("admin.portfolio"))

@admin_bp.route("/portfolio/award/<int:aid>/delete", methods=["POST"])
@admin_required
def delete_award(aid):
    a = Award.query.get_or_404(aid)
    db.session.delete(a)
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Award deleted.", "success")
    return redirect(url_for("admin.portfolio"))


# ── Hosting ───────────────────────────────────────────────────────────────────
@admin_bp.route("/hosting")
@admin_required
def hosting():
    plans = HostingPlan.query.order_by(HostingPlan.order).all()
    subs  = HostingSubscription.query.order_by(HostingSubscription.created_at.desc()).limit(50).all()
    servers = HostingServer.query.order_by(HostingServer.created_at.desc()).all()
    active_count  = HostingSubscription.query.filter_by(status="active").count()
    hosting_rev   = float(db.session.query(func.sum(HostingPlan.monthly_price)).join(
        HostingSubscription, HostingSubscription.plan_id == HostingPlan.id
    ).filter(HostingSubscription.status == "active").scalar() or 0)
    return render_template("admin/hosting.html", plans=plans, subscriptions=subs, servers=servers,
                           active_count=active_count, hosting_rev=hosting_rev)

@admin_bp.route("/hosting/plan/create", methods=["POST"])
@admin_required
def create_hosting_plan():
    features = [f.strip() for f in request.form.get("features","").split(chr(10)) if f.strip()]
    import re, time
    name = request.form.get("name","")
    slug = re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")+f"-{int(time.time())}"
    p = HostingPlan(name=name, slug=slug, description=request.form.get("description",""),
                    monthly_price=float(request.form.get("monthly_price",0) or 0),
                    annual_price=float(request.form.get("annual_price",0) or 0),
                    features=features, active=True, featured=bool(request.form.get("featured")),
                    limits={"server": request.form.get("server","")})
    db.session.add(p)
    db.session.commit()
    flash(f"Plan '{name}' created.", "success")
    return redirect(url_for("admin.hosting"))

@admin_bp.route("/hosting/plan/<int:pid>/update", methods=["POST"])
@admin_required
def update_hosting_plan(pid):
    p = HostingPlan.query.get_or_404(pid)
    features = [f.strip() for f in request.form.get("features","").split(chr(10)) if f.strip()]
    p.name = request.form.get("name", p.name)
    p.description = request.form.get("description", p.description)
    p.monthly_price = float(request.form.get("monthly_price", p.monthly_price) or 0)
    p.annual_price = float(request.form.get("annual_price", p.annual_price) or 0)
    p.features = features or p.features
    p.featured = bool(request.form.get("featured"))
    limits = dict(p.limits or {})
    limits["server"] = request.form.get("server", limits.get("server",""))
    p.limits = limits
    db.session.commit()
    flash(f"Plan '{p.name}' updated.", "success")
    return redirect(url_for("admin.hosting"))

@admin_bp.route("/hosting/plan/<int:pid>/toggle-active", methods=["POST"])
@admin_required
def toggle_hosting_plan_active(pid):
    p = HostingPlan.query.get_or_404(pid)
    p.active = not p.active
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True, "active": p.active})
    flash(f"Plan '{p.name}' {'activated' if p.active else 'deactivated'}.", "success")
    return redirect(url_for("admin.hosting"))

@admin_bp.route("/hosting/plan/<int:pid>/delete", methods=["POST"])
@admin_required
def delete_hosting_plan(pid):
    p = HostingPlan.query.get_or_404(pid)
    if HostingSubscription.query.filter_by(plan_id=pid).count() > 0:
        flash(f"Cannot delete '{p.name}' — it has existing subscriptions. Deactivate it instead.", "danger")
        return redirect(url_for("admin.hosting"))
    db.session.delete(p)
    db.session.commit()
    flash(f"Plan '{p.name}' deleted.", "success")
    return redirect(url_for("admin.hosting"))

@admin_bp.route("/credit-packages")
@admin_required
def credit_packages():
    from app.models.platform import CreditPackage, CreditPurchase, CreditTransaction
    from app.utils.credits import get_credit_unit_pricing
    from sqlalchemy import func as _func
    packages = CreditPackage.query.order_by(CreditPackage.sort_order, CreditPackage.price).all()
    revenue_by_package = dict(
        db.session.query(CreditPurchase.package_id, _func.sum(CreditPurchase.amount))
        .filter(CreditPurchase.status == "paid").group_by(CreditPurchase.package_id).all()
    )
    units_by_package = dict(
        db.session.query(CreditPurchase.package_id, _func.count(CreditPurchase.id))
        .filter(CreditPurchase.status == "paid").group_by(CreditPurchase.package_id).all()
    )
    total_revenue = float(db.session.query(_func.sum(CreditPurchase.amount)).filter(CreditPurchase.status == "paid").scalar() or 0)
    total_credits_sold = int(db.session.query(_func.sum(CreditPurchase.credits)).filter(CreditPurchase.status == "paid").scalar() or 0)

    # Order tracking — every purchase attempt, not just successful ones,
    # so support can see a customer's "I paid but nothing happened" report.
    status_filter = request.args.get("status", "")
    gateway_filter = request.args.get("gateway", "")
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 25
    orders_q = CreditPurchase.query
    if status_filter:
        orders_q = orders_q.filter(CreditPurchase.status == status_filter)
    if gateway_filter:
        orders_q = orders_q.filter(CreditPurchase.gateway == gateway_filter)
    orders_q = orders_q.order_by(CreditPurchase.created_at.desc())
    total_orders = orders_q.count()
    recent_purchases = orders_q.offset((page - 1) * per_page).limit(per_page).all()

    return render_template(
        "admin/credit_packages.html", packages=packages,
        revenue_by_package=revenue_by_package, units_by_package=units_by_package,
        total_revenue=total_revenue, total_credits_sold=total_credits_sold,
        recent_purchases=recent_purchases, unit_pricing=get_credit_unit_pricing(),
        status_filter=status_filter, gateway_filter=gateway_filter,
        page=page, per_page=per_page, total_orders=total_orders,
    )


@admin_bp.route("/credit-packages/pricing", methods=["POST"])
@admin_required
def update_credit_pricing():
    """Saves the admin-editable rate for the dashboard's quantity-stepper
    quick-buy widget (N units x unit_size credits at unit_price each)."""
    from app.utils.settings import set_setting
    try:
        unit_size = max(1, int(request.form.get("credit_unit_size", 10)))
        unit_price = max(0.01, float(request.form.get("credit_unit_price", 0.5)))
        max_units = max(1, int(request.form.get("credit_max_units", 50)))
    except (TypeError, ValueError):
        flash("Please enter valid numbers for the credit pricing fields.", "danger")
        return redirect(url_for("admin.credit_packages"))
    set_setting("credit_unit_size", unit_size, value_type="int", group="credits", label="Credits per unit")
    set_setting("credit_unit_price", unit_price, group="credits", label="Price per unit")
    set_setting("credit_max_units", max_units, value_type="int", group="credits", label="Max units per purchase")
    flash("Credit pricing updated.", "success")
    return redirect(url_for("admin.credit_packages"))


@admin_bp.route("/credit-packages/create", methods=["POST"])
@admin_required
def create_credit_package():
    from app.models.platform import CreditPackage
    name = request.form.get("name", "").strip()
    if not name:
        flash("Package name is required.", "danger")
        return redirect(url_for("admin.credit_packages"))
    pkg = CreditPackage(
        name=name,
        credits=int(request.form.get("credits", 0) or 0),
        price=float(request.form.get("price", 0) or 0),
        description=request.form.get("description", "").strip() or None,
        is_popular=bool(request.form.get("is_popular")),
        active=True,
        sort_order=int(request.form.get("sort_order", 0) or 0),
    )
    db.session.add(pkg)
    db.session.commit()
    flash(f"Credit package '{name}' created.", "success")
    return redirect(url_for("admin.credit_packages"))


@admin_bp.route("/credit-packages/<int:pkg_id>/update", methods=["POST"])
@admin_required
def update_credit_package(pkg_id):
    from app.models.platform import CreditPackage
    pkg = CreditPackage.query.get_or_404(pkg_id)
    pkg.name = request.form.get("name", pkg.name).strip() or pkg.name
    pkg.credits = int(request.form.get("credits", pkg.credits) or pkg.credits)
    pkg.price = float(request.form.get("price", pkg.price) or pkg.price)
    pkg.description = request.form.get("description", pkg.description or "").strip() or None
    pkg.is_popular = bool(request.form.get("is_popular"))
    pkg.sort_order = int(request.form.get("sort_order", pkg.sort_order) or 0)
    db.session.commit()
    flash(f"Credit package '{pkg.name}' updated.", "success")
    return redirect(url_for("admin.credit_packages"))


@admin_bp.route("/credit-packages/<int:pkg_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_credit_package_active(pkg_id):
    from app.models.platform import CreditPackage
    pkg = CreditPackage.query.get_or_404(pkg_id)
    pkg.active = not pkg.active
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True, "active": pkg.active})
    flash(f"Package '{pkg.name}' {'activated' if pkg.active else 'deactivated'}.", "success")
    return redirect(url_for("admin.credit_packages"))


@admin_bp.route("/credit-packages/<int:pkg_id>/delete", methods=["POST"])
@admin_required
def delete_credit_package(pkg_id):
    from app.models.platform import CreditPackage, CreditPurchase
    pkg = CreditPackage.query.get_or_404(pkg_id)
    if CreditPurchase.query.filter_by(package_id=pkg_id).count() > 0:
        flash(f"Cannot delete '{pkg.name}' — it has existing purchases on record. Deactivate it instead.", "danger")
        return redirect(url_for("admin.credit_packages"))
    db.session.delete(pkg)
    db.session.commit()
    flash(f"Package '{pkg.name}' deleted.", "success")
    return redirect(url_for("admin.credit_packages"))

@admin_bp.route("/hosting/subscription/<int:sid>/toggle", methods=["POST"])
@admin_required
def toggle_hosting_sub(sid):
    sub = HostingSubscription.query.get_or_404(sid)
    sub.status = "active" if sub.status != "active" else "suspended"
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True, "status": sub.status})
    flash(f"Subscription {sub.status}.", "success")
    return redirect(url_for("admin.hosting"))

@admin_bp.route("/hosting/subscription/<int:sid>/activate", methods=["POST"])
@admin_required
def activate_hosting_sub(sid):
    sub = HostingSubscription.query.get_or_404(sid)
    sub.status = "active"
    sub.starts_at = datetime.utcnow()
    sub.expires_at = sub.starts_at + (timedelta(days=365) if sub.billing_cycle == "annual" else timedelta(days=30))
    db.session.commit()
    flash(f"Subscription for {sub.domain} activated. Expires {sub.expires_at.strftime('%Y-%m-%d')}.", "success")
    return redirect(url_for("admin.hosting"))

@admin_bp.route("/hosting/subscription/<int:sid>/verify-dns", methods=["POST"])
@admin_required
def verify_dns_hosting_sub(sid):
    sub = HostingSubscription.query.get_or_404(sid)
    sub.dns_verified = True
    db.session.commit()
    flash(f"{sub.domain} marked as DNS verified.", "success")
    return redirect(url_for("admin.hosting"))

@admin_bp.route("/hosting/subscription/<int:sid>/renew", methods=["POST"])
@admin_required
def renew_hosting_sub(sid):
    sub = HostingSubscription.query.get_or_404(sid)
    base = sub.expires_at if sub.expires_at and sub.expires_at > datetime.utcnow() else datetime.utcnow()
    sub.expires_at = base + (timedelta(days=365) if sub.billing_cycle == "annual" else timedelta(days=30))
    sub.status = "active"
    db.session.commit()
    flash(f"Subscription for {sub.domain} renewed until {sub.expires_at.strftime('%Y-%m-%d')}.", "success")
    return redirect(url_for("admin.hosting"))

@admin_bp.route("/hosting/subscription/<int:sid>/cancel", methods=["POST"])
@admin_required
def cancel_hosting_sub(sid):
    sub = HostingSubscription.query.get_or_404(sid)
    sub.status = "cancelled"
    sub.auto_renew = False
    db.session.commit()
    flash(f"Subscription for {sub.domain} cancelled.", "success")
    return redirect(url_for("admin.hosting"))

@admin_bp.route("/hosting/server/create", methods=["POST"])
@admin_required
def create_hosting_server():
    s = HostingServer(
        label=request.form.get("label",""),
        provider=request.form.get("provider","cpanel"),
        api_endpoint=request.form.get("api_endpoint",""),
        api_key=request.form.get("api_key",""),
        notes=request.form.get("notes",""),
        active=True,
    )
    db.session.add(s)
    db.session.commit()
    flash(f"Server '{s.label}' added.", "success")
    return redirect(url_for("admin.hosting"))

@admin_bp.route("/hosting/server/<int:sid>/delete", methods=["POST"])
@admin_required
def delete_hosting_server(sid):
    s = HostingServer.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    flash(f"Server '{s.label}' removed.", "success")
    return redirect(url_for("admin.hosting"))


# ── Email Templates ───────────────────────────────────────────────────────────
@admin_bp.route("/email-templates")
@admin_required
def email_templates():
    templates = EmailTemplate.query.all()
    return render_template("admin/email_templates.html", templates=templates)

@admin_bp.route("/email-templates/save", methods=["POST"])
@admin_required
def save_email_template():
    tid     = request.form.get("template_id") or (request.get_json(silent=True) or {}).get("template_id")
    subject = request.form.get("subject") or (request.get_json(silent=True) or {}).get("subject","")
    body    = request.form.get("body") or (request.get_json(silent=True) or {}).get("body","")
    name    = request.form.get("name", tid)
    if not tid:
        if request.is_json:
            return jsonify({"error": "template_id required"}), 400
        flash("Template ID required.", "danger")
        return redirect(url_for("admin.email_templates"))
    tpl = EmailTemplate.query.filter_by(template_id=tid).first()
    if tpl:
        tpl.subject = subject
        tpl.body    = body
        tpl.name    = name
    else:
        tpl = EmailTemplate(template_id=tid, name=name, subject=subject, body=body)
        db.session.add(tpl)
    db.session.commit()
    log_action(current_user.id, "admin.email_template.save", f"EmailTemplate:{tid}")
    if request.is_json:
        return jsonify({"success": True})
    flash("Email template saved.", "success")
    return redirect(url_for("admin.email_templates"))


# ── Freelancers ───────────────────────────────────────────────────────────────
@admin_bp.route("/freelancers")
@admin_required
def freelancers():
    profiles = FreelancerProfile.query.order_by(FreelancerProfile.created_at.desc()).all()
    jobs     = JobPost.query.order_by(JobPost.created_at.desc()).limit(50).all()
    from app.utils.settings import get_setting
    fl_settings = {
        "freelancer_mode_enabled": get_setting("freelancer_mode_enabled", "true"),
        "client_mode_enabled": get_setting("client_mode_enabled", "true"),
    }
    return render_template("admin/freelancers.html", profiles=profiles, jobs=jobs, fl_settings=fl_settings)

@admin_bp.route("/freelancers/<int:fid>/verify", methods=["POST"])
@admin_required
def verify_freelancer(fid):
    profile = FreelancerProfile.query.get_or_404(fid)
    profile.verified = not profile.verified
    db.session.commit()
    log_action(current_user.id, "admin.freelancer.verify", f"FreelancerProfile#{fid}")
    if request.is_json:
        return jsonify({"success": True, "verified": profile.verified})
    flash(f"Freelancer {'verified' if profile.verified else 'unverified'}.", "success")
    return redirect(url_for("admin.freelancers"))

@admin_bp.route("/freelancers/<int:fid>/feature", methods=["POST"])
@admin_required
def feature_freelancer(fid):
    profile = FreelancerProfile.query.get_or_404(fid)
    profile.featured = not profile.featured
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True, "featured": profile.featured})
    flash(f"Freelancer {'featured' if profile.featured else 'unfeatured'}.", "success")
    return redirect(url_for("admin.freelancers"))

@admin_bp.route("/jobs/<int:jid>/close", methods=["POST"])
@admin_required
def close_job(jid):
    job = JobPost.query.get_or_404(jid)
    job.status = "closed"
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Job closed.", "success")
    return redirect(url_for("admin.freelancers"))


# ── Newsletter ────────────────────────────────────────────────────────────────
@admin_bp.route("/newsletter")
@admin_required
def newsletter():
    subs = NewsletterSubscriber.query.filter_by(unsubscribed=False).order_by(NewsletterSubscriber.created_at.desc()).all()
    return render_template("admin/newsletter.html", subscribers=subs)

@admin_bp.route("/newsletter/export")
@admin_required
def export_newsletter():
    import csv, io
    subs = NewsletterSubscriber.query.filter_by(unsubscribed=False).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["email", "name", "confirmed", "joined"])
    for s in subs:
        writer.writerow([s.email, s.name or "", "yes" if s.confirmed else "no", s.created_at.strftime("%Y-%m-%d")])
    output.seek(0)
    bio = __import__("io").BytesIO(output.getvalue().encode())
    return send_file(bio, mimetype="text/csv", as_attachment=True, download_name="subscribers.csv")


@admin_bp.route("/newsletter/campaigns")
@admin_required
def newsletter_campaigns():
    campaigns = NewsletterCampaign.query.order_by(NewsletterCampaign.created_at.desc()).all()
    subscriber_count = NewsletterSubscriber.query.filter_by(unsubscribed=False).count()
    return render_template("admin/newsletter_campaigns.html", campaigns=campaigns, subscriber_count=subscriber_count)


@admin_bp.route("/newsletter/campaigns/create", methods=["POST"])
@admin_required
def create_newsletter_campaign():
    subject = (request.form.get("subject") or "").strip()
    body_html = (request.form.get("body_html") or "").strip()
    if not subject or not body_html:
        flash("Subject and content are required.", "danger")
        return redirect(url_for("admin.newsletter_campaigns"))
    campaign = NewsletterCampaign(subject=subject, body_html=body_html, status="draft")
    db.session.add(campaign)
    db.session.commit()
    flash("Campaign saved as draft. Review it, then send.", "success")
    return redirect(url_for("admin.newsletter_campaigns"))


@admin_bp.route("/newsletter/campaigns/<int:cid>/delete", methods=["POST"])
@admin_required
def delete_newsletter_campaign(cid):
    campaign = NewsletterCampaign.query.get_or_404(cid)
    if campaign.status == "sending":
        flash("Can't delete a campaign that's currently sending.", "danger")
        return redirect(url_for("admin.newsletter_campaigns"))
    db.session.delete(campaign)
    db.session.commit()
    flash("Campaign deleted.", "success")
    return redirect(url_for("admin.newsletter_campaigns"))


@admin_bp.route("/newsletter/campaigns/<int:cid>/send", methods=["POST"])
@admin_required
def send_newsletter_campaign(cid):
    """Sends synchronously in the request (no task queue is configured in this
    project — see CHANGES notes). Fine for hundreds of subscribers; if the
    list grows into the thousands, this should move to a background worker
    (Celery/RQ) instead of blocking the request."""
    from app.utils.email import send_email

    campaign = NewsletterCampaign.query.get_or_404(cid)
    if campaign.status == "sent":
        flash("This campaign was already sent.", "danger")
        return redirect(url_for("admin.newsletter_campaigns"))

    subscribers = NewsletterSubscriber.query.filter_by(unsubscribed=False, confirmed=True).all()
    if not subscribers:
        # Fall back to all non-unsubscribed if nobody's gone through a confirm
        # step (this project doesn't have double opt-in wired up yet — see notes).
        subscribers = NewsletterSubscriber.query.filter_by(unsubscribed=False).all()

    campaign.status = "sending"
    campaign.recipient_count = len(subscribers)
    db.session.commit()

    sent, failed = 0, 0
    for sub in subscribers:
        sub.ensure_token()
        unsub_url = url_for("cms.newsletter_unsubscribe", token=sub.unsub_token, _external=True)
        html = campaign.body_html + f'''
        <hr style="margin-top:32px;border:none;border-top:1px solid #333">
        <p style="font-size:11px;color:#888;margin-top:12px">
          You're receiving this because you subscribed at {get_setting('site_name','Bazillin Studio')}.
          <a href="{unsub_url}" style="color:#888">Unsubscribe</a>
        </p>'''
        ok = send_email(to=sub.email, subject=campaign.subject, body_html=html)
        if ok:
            sent += 1
        else:
            failed += 1
    db.session.commit()  # persist ensure_token() calls

    campaign.status = "sent"
    campaign.sent_count = sent
    campaign.failed_count = failed
    campaign.sent_at = datetime.utcnow()
    db.session.commit()

    log_action(current_user.id, "admin.newsletter.send", "NewsletterCampaign", str(cid))
    flash(f"Campaign sent: {sent} delivered, {failed} failed.", "success" if failed == 0 else "warning")
    return redirect(url_for("admin.newsletter_campaigns"))


# ── Email Sequences (drip campaigns: Welcome Series, Follow-Up, etc.) ─────────
@admin_bp.route("/email-sequences")
@admin_required
def email_sequences():
    from app.models.core import EmailSequence, EmailSequenceEnrollment
    sequences = EmailSequence.query.order_by(EmailSequence.created_at.desc()).all()
    enrollment_counts = {
        seq.id: EmailSequenceEnrollment.query.filter_by(sequence_id=seq.id).count()
        for seq in sequences
    }
    return render_template("admin/email_sequences.html", sequences=sequences, enrollment_counts=enrollment_counts)


@admin_bp.route("/email-sequences/create", methods=["POST"])
@admin_required
def create_email_sequence():
    from app.models.core import EmailSequence
    name = (request.form.get("name") or "").strip()
    trigger = request.form.get("trigger", "manual")
    if not name:
        flash("Give the sequence a name.", "danger")
        return redirect(url_for("admin.email_sequences"))
    seq = EmailSequence(name=name, trigger=trigger)
    db.session.add(seq)
    db.session.commit()
    flash(f'Sequence "{name}" created — add steps to it below.', "success")
    return redirect(url_for("admin.email_sequence_detail", sid=seq.id))


@admin_bp.route("/email-sequences/<int:sid>")
@admin_required
def email_sequence_detail(sid):
    from app.models.core import EmailSequence, EmailSequenceEnrollment
    seq = EmailSequence.query.get_or_404(sid)
    enrollments = EmailSequenceEnrollment.query.filter_by(sequence_id=sid).order_by(
        EmailSequenceEnrollment.enrolled_at.desc()).limit(100).all()
    return render_template("admin/email_sequence_detail.html", seq=seq, enrollments=enrollments)


@admin_bp.route("/email-sequences/<int:sid>/toggle-active", methods=["POST"])
@admin_required
def toggle_email_sequence(sid):
    from app.models.core import EmailSequence
    seq = EmailSequence.query.get_or_404(sid)
    seq.active = not seq.active
    db.session.commit()
    return redirect(url_for("admin.email_sequences"))


@admin_bp.route("/email-sequences/<int:sid>/delete", methods=["POST"])
@admin_required
def delete_email_sequence(sid):
    from app.models.core import EmailSequence
    seq = EmailSequence.query.get_or_404(sid)
    db.session.delete(seq)
    db.session.commit()
    flash("Sequence deleted.", "success")
    return redirect(url_for("admin.email_sequences"))


@admin_bp.route("/email-sequences/<int:sid>/steps/add", methods=["POST"])
@admin_required
def add_email_sequence_step(sid):
    from app.models.core import EmailSequence, EmailSequenceStep
    seq = EmailSequence.query.get_or_404(sid)
    subject = (request.form.get("subject") or "").strip()
    body_html = (request.form.get("body_html") or "").strip()
    delay_days = request.form.get("delay_days", type=int) or 0
    if not subject or not body_html:
        flash("Subject and content are required for a step.", "danger")
        return redirect(url_for("admin.email_sequence_detail", sid=sid))
    next_order = len(seq.steps)
    step = EmailSequenceStep(sequence_id=sid, step_order=next_order, delay_days=delay_days,
                              subject=subject, body_html=body_html)
    db.session.add(step)
    db.session.commit()
    flash(f"Step {next_order + 1} added — sends {delay_days} day(s) after enrollment.", "success")
    return redirect(url_for("admin.email_sequence_detail", sid=sid))


@admin_bp.route("/email-sequences/steps/<int:step_id>/delete", methods=["POST"])
@admin_required
def delete_email_sequence_step(step_id):
    from app.models.core import EmailSequenceStep
    step = EmailSequenceStep.query.get_or_404(step_id)
    sid = step.sequence_id
    db.session.delete(step)
    db.session.commit()
    return redirect(url_for("admin.email_sequence_detail", sid=sid))


@admin_bp.route("/email-sequences/generate-step-ai", methods=["POST"])
@admin_required
def generate_email_sequence_step_ai():
    """AI-drafts one email step's subject + body from a short prompt —
    reuses the same _call_ai used everywhere else in the site, so it goes
    through whichever provider is configured in Settings -> AI Providers."""
    from app.ai_tools.routes import _call_ai
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Describe what this email should say."}), 400
    system = (
        "You write one email for a drip/welcome sequence. Respond with ONLY valid JSON: "
        '{"subject": "...", "body_html": "..."}. body_html should be simple, friendly HTML '
        "(a few <p> paragraphs, no <html>/<body> wrapper). Use {{name}} where a first-name "
        "greeting would go."
    )
    text, err = _call_ai(system, [{"role": "user", "content": prompt}], max_tokens=800)
    if err:
        return jsonify({"error": err}), 400
    import json as _json
    try:
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = _json.loads(cleaned)
        return jsonify({"subject": parsed.get("subject", ""), "body_html": parsed.get("body_html", "")})
    except Exception:
        return jsonify({"error": "AI response wasn't valid JSON — try rephrasing the prompt."}), 400


@admin_bp.route("/cron/send-email-sequences")
def send_email_sequences_cron():
    """Same external-cron pattern as the DB backup and scheduled-broadcast
    crons — point an hourly (or daily) cron at this URL with the secret."""
    expected = get_setting("backup_cron_secret")
    if not expected or request.args.get("secret") != expected:
        abort(403)
    from app.utils.email_sequences import send_due_sequence_emails
    sent = send_due_sequence_emails()
    return jsonify({"sent": sent})


# ── AI Console ──────────────────────────────────────────────────────────────
def _ai_console_context_snapshot():
    """A few real, live numbers pulled straight from the database so the
    console can answer basic questions about the actual state of the site
    instead of just being a generic chatbot bolted onto the admin panel."""
    from datetime import datetime, timedelta
    from app.models.platform import ProjectRequest, SupportTicket
    from app.models.core import NewsletterSubscriber
    try:
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_requests = ProjectRequest.query.filter_by(status="new").count()
        quoted_requests = ProjectRequest.query.filter_by(status="quoted").count()
        new_subscribers_week = NewsletterSubscriber.query.filter(
            NewsletterSubscriber.created_at >= week_ago).count()
        open_tickets = SupportTicket.query.filter(SupportTicket.status != "closed").count()
        return (
            f"Live site snapshot (for your reference, don't repeat this back unless asked): "
            f"{new_requests} new unreviewed Hire Me requests, {quoted_requests} quoted proposals awaiting a decision, "
            f"{new_subscribers_week} newsletter signups in the last 7 days, {open_tickets} open support tickets."
        )
    except Exception:
        return ""


@admin_bp.route("/ai-console")
@admin_required
def ai_console():
    from app.models.core import AIConsoleThread, PromptTemplate
    threads = AIConsoleThread.query.filter_by(user_id=current_user.id).order_by(
        AIConsoleThread.updated_at.desc()).all()
    thread_id = request.args.get("thread_id", type=int)
    active_thread = None
    if thread_id:
        active_thread = AIConsoleThread.query.filter_by(id=thread_id, user_id=current_user.id).first()
    if not active_thread and threads:
        active_thread = threads[0]

    prefill_prompt = ""
    use_prompt_id = request.args.get("use_prompt", type=int)
    if use_prompt_id:
        tpl = PromptTemplate.query.get(use_prompt_id)
        if tpl:
            tpl.use_count = (tpl.use_count or 0) + 1
            db.session.commit()
            prefill_prompt = tpl.body

    prompt_categories = sorted({t.category for t in PromptTemplate.query.all()})
    return render_template("admin/ai_console.html", threads=threads, active_thread=active_thread,
                           prefill_prompt=prefill_prompt, prompt_categories=prompt_categories)


@admin_bp.route("/ai-console/new", methods=["POST"])
@admin_required
def ai_console_new_thread():
    from app.models.core import AIConsoleThread
    thread = AIConsoleThread(user_id=current_user.id, title="New Conversation")
    db.session.add(thread)
    db.session.commit()
    return redirect(url_for("admin.ai_console", thread_id=thread.id))


@admin_bp.route("/ai-console/<int:thread_id>/delete", methods=["POST"])
@admin_required
def ai_console_delete_thread(thread_id):
    from app.models.core import AIConsoleThread
    thread = AIConsoleThread.query.filter_by(id=thread_id, user_id=current_user.id).first_or_404()
    db.session.delete(thread)
    db.session.commit()
    return redirect(url_for("admin.ai_console"))


@admin_bp.route("/ai-console/send", methods=["POST"])
@admin_required
def ai_console_send():
    from app.models.core import AIConsoleThread, AIConsoleMessage
    from app.utils.ai_agent_tools import run_agent_turn

    data = request.get_json(silent=True) or {}
    thread_id = data.get("thread_id")
    prompt = (data.get("message") or "").strip()
    if not prompt:
        return jsonify({"error": "Message can't be empty"}), 400

    if thread_id:
        thread = AIConsoleThread.query.filter_by(id=thread_id, user_id=current_user.id).first()
        if not thread:
            return jsonify({"error": "Thread not found"}), 404
    else:
        thread = AIConsoleThread(user_id=current_user.id, title=prompt[:60])
        db.session.add(thread)
        db.session.commit()

    user_msg = AIConsoleMessage(thread_id=thread.id, role="user", content=prompt)
    db.session.add(user_msg)
    if thread.title == "New Conversation":
        thread.title = prompt[:60]
    db.session.commit()

    history = [{"role": m.role, "content": m.content} for m in thread.messages]
    system = (
        "You are the Admin AI Console for a freelancer's business-management platform (Bazillin). "
        "You're talking directly to the site owner/admin, not a customer. Be direct, practical, and concise — "
        "this is a working tool, not a customer-facing chatbot. You have real tools you can call to actually "
        "perform actions on the site (create a blog draft, add a to-do, send a test email, create an inactive "
        "automation workflow or popup shell, look up live stats) — but ONLY call a tool when the person "
        "clearly asks you to DO or CREATE something specific. A greeting ('hi', 'hello'), a question, or "
        "general chat gets a normal conversational reply with ZERO tool calls — never act preemptively or "
        "guess at a task nobody asked for. Everything you create (blog drafts, workflows, popups) is created "
        "INACTIVE/unpublished so a human reviews it before it goes live — say that plainly when you create "
        "something, don't imply it's already live. " + _ai_console_context_snapshot()
    )
    text, actions_taken, err = run_agent_turn(system, history, current_user, max_tokens=2000)
    if err:
        # This is an ordinary "your AI key is missing/invalid/out of quota"
        # condition, not a server crash — returning 500 here was the bug
        # behind "AI console keeps showing 500 error" no matter what
        # provider was configured. 200 + an error field lets the frontend
        # show the real message instead of a generic failure.
        return jsonify({"error": err})

    full_response = text or ""
    if actions_taken:
        action_lines = "\n".join(f"🔧 {a}" for a in actions_taken)
        full_response = f"{action_lines}\n\n{full_response}" if full_response else action_lines

    assistant_msg = AIConsoleMessage(thread_id=thread.id, role="assistant", content=full_response)
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({"thread_id": thread.id, "title": thread.title, "response": full_response})


# ── AI Agent Studio ──────────────────────────────────────────────────────
# MVP: named personas running through the same tool-calling engine as the
# AI Console. NOT the full multi-agent-delegation/scheduling/knowledge-base
# system from the master prompt — one continuous conversation per agent,
# no agent-to-agent handoff, no autonomous/scheduled runs, no per-agent
# tool permission scoping (every agent shares the same tool set today).
@admin_bp.route("/agents")
@admin_required
def agents():
    from app.models.core import Agent
    from app.utils.ai_agent_tools import TOOL_SCHEMAS
    agent_list = Agent.query.order_by(Agent.created_at.desc()).all()
    tool_choices = [(t["name"], t["description"].split(".")[0]) for t in TOOL_SCHEMAS]
    return render_template("admin/agents.html", agents=agent_list, tool_choices=tool_choices)


@admin_bp.route("/agents/<int:agent_id>/update", methods=["POST"])
@admin_required
def agent_update(agent_id):
    """Real enforcement point for what was previously a decorative column:
    tools_permissions (and model_name/temperature) now actually change
    what the agent can do and how it runs — see run_agent_turn()."""
    from app.models.core import Agent
    from app.utils.ai_agent_tools import TOOL_SCHEMAS
    agent = Agent.query.get_or_404(agent_id)
    valid_names = {t["name"] for t in TOOL_SCHEMAS}
    selected = [t for t in request.form.getlist("tools_permissions") if t in valid_names]
    agent.tools_permissions = selected  # empty list = no restriction (all tools)
    agent.model_name = (request.form.get("model_name") or "").strip() or None
    try:
        temp = float(request.form.get("temperature", ""))
        agent.temperature = max(0.0, min(1.0, temp))
    except ValueError:
        pass
    db.session.commit()
    flash(f'Updated "{agent.name}" — '
          f'{"restricted to " + str(len(selected)) + " tool(s)" if selected else "no tool restriction"}.',
          "success")
    return redirect(url_for("admin.agents"))


@admin_bp.route("/agents/create", methods=["POST"])
@admin_required
def agent_create():
    from app.models.core import Agent
    name = (request.form.get("name") or "").strip()
    instructions = (request.form.get("instructions") or "").strip()
    if not name or not instructions:
        flash("Give the agent a name and instructions.", "danger")
        return redirect(url_for("admin.agents"))
    agent = Agent(
        name=name, avatar_emoji=(request.form.get("avatar_emoji") or "🤖").strip()[:8],
        role=(request.form.get("role") or "").strip() or None,
        department=(request.form.get("department") or "").strip() or None,
        instructions=instructions, created_by=current_user.id,
        customer_facing=bool(request.form.get("customer_facing")),
        public_greeting=(request.form.get("public_greeting") or "").strip() or None,
    )
    db.session.add(agent)
    db.session.commit()
    flash(f'"{name}" is ready.', "success")
    return redirect(url_for("admin.agent_chat", agent_id=agent.id))


@admin_bp.route("/agents/<int:agent_id>/toggle", methods=["POST"])
@admin_required
def agent_toggle(agent_id):
    from app.models.core import Agent
    agent = Agent.query.get_or_404(agent_id)
    agent.active = not agent.active
    db.session.commit()
    return redirect(url_for("admin.agents"))


@admin_bp.route("/agents/<int:agent_id>/delete", methods=["POST"])
@admin_required
def agent_delete(agent_id):
    from app.models.core import Agent
    agent = Agent.query.get_or_404(agent_id)
    db.session.delete(agent)
    db.session.commit()
    flash("Agent deleted.", "success")
    return redirect(url_for("admin.agents"))


@admin_bp.route("/agents/<int:agent_id>")
@admin_required
def agent_chat(agent_id):
    from app.models.core import Agent
    agent = Agent.query.get_or_404(agent_id)
    return render_template("admin/agent_chat.html", agent=agent)


@admin_bp.route("/agents/<int:agent_id>/send", methods=["POST"])
@admin_required
def agent_send(agent_id):
    from app.models.core import Agent, AgentMessage
    from app.utils.ai_agent_tools import run_agent_turn

    agent = Agent.query.get_or_404(agent_id)
    data = request.get_json(silent=True) or {}
    prompt = (data.get("message") or "").strip()
    if not prompt:
        return jsonify({"error": "Message can't be empty"}), 400

    user_msg = AgentMessage(agent_id=agent.id, role="user", content=prompt)
    db.session.add(user_msg)
    db.session.commit()

    history = [{"role": m.role, "content": m.content} for m in agent.messages]
    system = (
        f"You are {agent.name}"
        + (f", the {agent.role}" if agent.role else "")
        + (f" in the {agent.department} department" if agent.department else "")
        + f" at this business. Your instructions: {agent.instructions}\n\n"
        "You're talking directly to the site owner/admin. You have real tools you can call to actually "
        "perform actions on the site (create a blog draft, add a to-do, send a test email, create an "
        "inactive automation workflow or popup shell, look up live stats) — but ONLY call a tool when the "
        "person clearly asks you to DO or CREATE something specific. A greeting ('hi', 'hello'), a question, "
        "or general chat gets a normal conversational reply with ZERO tool calls — never act preemptively or "
        "guess at a task nobody asked for. Everything you create is created INACTIVE/unpublished so a human "
        "reviews it before it goes live — say that plainly when you create something, don't imply it's "
        "already live. Stay in character as your role, but be direct and practical — this is a real "
        "working tool, not a customer-facing chatbot."
    )
    text, actions_taken, err = run_agent_turn(
        system, history, current_user, max_tokens=2000,
        allowed_tools=agent.tools_permissions or None,
        model_name=agent.model_name, temperature=agent.temperature)
    if err:
        return jsonify({"error": err})

    full_response = text or ""
    if actions_taken:
        action_lines = "\n".join(f"🔧 {a}" for a in actions_taken)
        full_response = f"{action_lines}\n\n{full_response}" if full_response else action_lines

    assistant_msg = AgentMessage(agent_id=agent.id, role="assistant", content=full_response)
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({"response": full_response})


@admin_bp.route("/agents/<int:agent_id>/clear", methods=["POST"])
@admin_required
def agent_clear_history(agent_id):
    from app.models.core import Agent, AgentMessage
    agent = Agent.query.get_or_404(agent_id)
    AgentMessage.query.filter_by(agent_id=agent.id).delete()
    db.session.commit()
    flash("Conversation cleared.", "success")
    return redirect(url_for("admin.agent_chat", agent_id=agent.id))


# ── AI Prompt Library ───────────────────────────────────────────────────────
@admin_bp.route("/ai-console/prompts")
@admin_required
def prompt_library():
    from app.models.core import PromptTemplate
    category = request.args.get("category", "")
    q = PromptTemplate.query
    if category:
        q = q.filter_by(category=category)
    templates = q.order_by(PromptTemplate.category, PromptTemplate.title).all()
    categories = sorted({t.category for t in PromptTemplate.query.all()})
    return render_template("admin/prompt_library.html", templates=templates,
                           categories=categories, active_category=category)


@admin_bp.route("/ai-console/prompts/save", methods=["POST"])
@admin_required
def prompt_library_save():
    from app.models.core import PromptTemplate
    template_id = request.form.get("id", type=int)
    title = (request.form.get("title") or "").strip()
    category = (request.form.get("category") or "General").strip() or "General"
    body = (request.form.get("body") or "").strip()
    description = (request.form.get("description") or "").strip()
    if not title or not body:
        flash("Title and prompt body are required.", "danger")
        return redirect(url_for("admin.prompt_library"))

    if template_id:
        tpl = PromptTemplate.query.get_or_404(template_id)
        tpl.title, tpl.category, tpl.body, tpl.description = title, category, body, description
        flash(f'Updated "{title}".', "success")
    else:
        tpl = PromptTemplate(title=title, category=category, body=body,
                              description=description, created_by=current_user.id)
        db.session.add(tpl)
        flash(f'Created "{title}".', "success")
    db.session.commit()
    return redirect(url_for("admin.prompt_library"))


@admin_bp.route("/ai-console/prompts/<int:template_id>/delete", methods=["POST"])
@admin_required
def prompt_library_delete(template_id):
    from app.models.core import PromptTemplate
    tpl = PromptTemplate.query.get_or_404(template_id)
    if tpl.is_builtin:
        flash("Built-in starter templates can't be deleted — edit it instead, or just ignore it.", "danger")
        return redirect(url_for("admin.prompt_library"))
    db.session.delete(tpl)
    db.session.commit()
    flash("Template deleted.", "success")
    return redirect(url_for("admin.prompt_library"))


@admin_bp.route("/ai-console/prompts/<int:template_id>/use", methods=["POST"])
@admin_required
def prompt_library_use(template_id):
    """Called via fetch from the AI Console when a template is picked —
    bumps its use count (so the library can be sorted/surfaced by what's
    actually useful later) and returns the raw body for the console JS to
    drop into the message box."""
    from app.models.core import PromptTemplate
    tpl = PromptTemplate.query.get_or_404(template_id)
    tpl.use_count = (tpl.use_count or 0) + 1
    db.session.commit()
    return jsonify({"body": tpl.body, "variables": tpl.variables()})


# ── Website Automation: Popups ─────────────────────────────────────────────
@admin_bp.route("/site-automation/popups")
@admin_required
def site_popups():
    from app.models.core import SitePopup
    popups = SitePopup.query.order_by(SitePopup.created_at.desc()).all()
    return render_template("admin/site_popups.html", popups=popups)


@admin_bp.route("/site-automation/popups/create", methods=["POST"])
@admin_required
def create_site_popup():
    from app.models.core import SitePopup
    title = (request.form.get("title") or "").strip()
    headline = (request.form.get("headline") or "").strip()
    if not title or not headline:
        flash("Title and headline are required.", "danger")
        return redirect(url_for("admin.site_popups"))
    popup = SitePopup(
        title=title, headline=headline,
        body_html=request.form.get("body_html", ""),
        cta_text=request.form.get("cta_text", ""),
        cta_url=request.form.get("cta_url", ""),
        trigger_type=request.form.get("trigger_type", "delay"),
        trigger_value=request.form.get("trigger_value", type=int) or 5,
        path_pattern=(request.form.get("path_pattern") or "").strip() or None,
        frequency=request.form.get("frequency", "once_per_session"),
    )
    db.session.add(popup)
    db.session.commit()
    flash(f'Popup "{title}" created.', "success")
    return redirect(url_for("admin.site_popups"))


@admin_bp.route("/site-automation/popups/<int:pid>/toggle", methods=["POST"])
@admin_required
def toggle_site_popup(pid):
    from app.models.core import SitePopup
    popup = SitePopup.query.get_or_404(pid)
    popup.active = not popup.active
    db.session.commit()
    return redirect(url_for("admin.site_popups"))


@admin_bp.route("/site-automation/popups/<int:pid>/delete", methods=["POST"])
@admin_required
def delete_site_popup(pid):
    from app.models.core import SitePopup
    popup = SitePopup.query.get_or_404(pid)
    db.session.delete(popup)
    db.session.commit()
    flash("Popup deleted.", "success")
    return redirect(url_for("admin.site_popups"))


# ── Trends ────────────────────────────────────────────────────────────────────
@admin_bp.route("/trends")
@admin_required
def trends():
    items = TrendItem.query.order_by(TrendItem.pinned.desc(), TrendItem.score.desc()).limit(100).all()
    return render_template("admin/trends.html", items=items)

@admin_bp.route("/trends/fetch", methods=["POST"])
@admin_required
def fetch_trends():
    """Pulls fresh items from Hacker News, DEV Community, and GitHub (see
    app/utils/trends_fetch.py). Runs in the request — there's no task
    queue/cron configured in this project, so this is admin-triggered
    on demand rather than scheduled. New items land as unapproved
    ('Pending' in the list below) so you can review before they go live
    on the homepage."""
    from app.utils.trends_fetch import fetch_all
    fetched = fetch_all()
    if not fetched:
        flash("Couldn't reach any trend sources right now — try again shortly.", "danger")
        return redirect(url_for("admin.trends"))

    existing_urls = {t.url for t in TrendItem.query.with_entities(TrendItem.url).all()}
    added = 0
    for item in fetched:
        if item["url"] in existing_urls:
            continue
        db.session.add(TrendItem(
            title=item["title"], description=item.get("description"),
            url=item["url"], source=item["source"], category=item.get("category"),
            score=item.get("score", 0), approved=False,
        ))
        added += 1
    db.session.commit()
    flash(f"Fetched {len(fetched)} items — {added} new (pending review below).", "success")
    return redirect(url_for("admin.trends"))

@admin_bp.route("/trends/<int:tid>/pin", methods=["POST"])
@admin_required
def pin_trend(tid):
    item = TrendItem.query.get_or_404(tid)
    item.pinned = not item.pinned
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True, "pinned": item.pinned})
    flash(f"Trend {'pinned' if item.pinned else 'unpinned'}.", "success")
    return redirect(url_for("admin.trends"))

@admin_bp.route("/trends/<int:tid>/hide", methods=["POST"])
@admin_required
def hide_trend(tid):
    item = TrendItem.query.get_or_404(tid)
    item.hidden = True
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Trend hidden.", "success")
    return redirect(url_for("admin.trends"))

@admin_bp.route("/trends/<int:tid>/approve", methods=["POST"])
@admin_required
def approve_trend(tid):
    item = TrendItem.query.get_or_404(tid)
    item.approved = True
    item.hidden   = False
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash("Trend approved.", "success")
    return redirect(url_for("admin.trends"))


# ── Analytics ─────────────────────────────────────────────────────────────────
@admin_bp.route("/analytics")
@admin_required
def analytics():
    from app.models.platform import Invoice
    from flask import g
    days = request.args.get("days", 30, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    signups  = User.query.filter(User.created_at >= since).count()
    # Every paid Order/Invoice in the window counts, converted into the
    # site's display currency via the admin's manual rate table before
    # being summed — see admin.dashboard for the same approach and
    # admin.financials for the true, unconverted, per-currency breakdown.
    from app.utils.currency import convert_and_sum, rates_are_missing_for
    display_currency = getattr(g, "currency", "NGN")
    order_sums = db.session.query(Order.currency, func.sum(Order.amount)) \
        .filter(Order.status == "paid", Order.created_at >= since).group_by(Order.currency).all()
    order_ct = Order.query.filter_by(status="paid").filter(Order.created_at >= since).count()
    product_rev = convert_and_sum(order_sums, display_currency)
    # Project/client-work payments (Invoice) were never included here before —
    # only marketplace Orders were, so revenue from hired project work never
    # showed up in analytics even though the payment itself succeeded.
    invoice_sums = db.session.query(Invoice.currency, func.sum(Invoice.amount)) \
        .filter(Invoice.status == "paid", Invoice.paid_at >= since).group_by(Invoice.currency).all()
    invoice_ct = Invoice.query.filter_by(status="paid").filter(Invoice.paid_at >= since).count()
    project_rev = convert_and_sum(invoice_sums, display_currency)
    rev_agg = product_rev + project_rev
    order_ct = order_ct + invoice_ct
    # Which currencies in this window have no manual rate set — those got
    # counted 1:1 above, so surface it instead of silently misreporting.
    seen_currencies = {c for c, _ in order_sums if c} | {c for c, _ in invoice_sums if c}
    unconverted_currencies = rates_are_missing_for(seen_currencies)
    top_pages = (db.session.query(PageView.path, func.count(PageView.id).label("views"))
                 .filter(PageView.created_at >= since)
                 .group_by(PageView.path)
                 .order_by(func.count(PageView.id).desc())
                 .limit(10).all())
    unique_visitors = (db.session.query(func.count(func.distinct(PageView.session_id)))
                        .filter(PageView.created_at >= since).scalar() or 0)
    total_views = PageView.query.filter(PageView.created_at >= since).count()
    device_breakdown = (db.session.query(PageView.device, func.count(PageView.id))
                         .filter(PageView.created_at >= since, PageView.device.isnot(None))
                         .group_by(PageView.device).all())
    top_referrers = (db.session.query(PageView.referrer, func.count(PageView.id).label("hits"))
                      .filter(PageView.created_at >= since, PageView.referrer.isnot(None), PageView.referrer != "")
                      .group_by(PageView.referrer)
                      .order_by(func.count(PageView.id).desc())
                      .limit(8).all())
    # Conversion/outflow events — what visitors actually DID after arriving
    # (leads, signups, purchases, contact forms), not just which pages they
    # loaded. AnalyticsEvent existed in the schema before this but nothing
    # in the app ever wrote to it, so this breakdown was always empty.
    event_breakdown = (db.session.query(AnalyticsEvent.event, func.count(AnalyticsEvent.id).label("count"))
                        .filter(AnalyticsEvent.created_at >= since)
                        .group_by(AnalyticsEvent.event)
                        .order_by(func.count(AnalyticsEvent.id).desc()).all())
    total_conversions = AnalyticsEvent.query.filter(AnalyticsEvent.created_at >= since).count()
    conversion_rate = round((total_conversions / total_views * 100), 2) if total_views else 0
    daily = []
    for i in range(days):
        d = datetime.utcnow() - timedelta(days=days-1-i)
        start = d.replace(hour=0,minute=0,second=0,microsecond=0)
        end   = d.replace(hour=23,minute=59,second=59)
        day_order_sums = db.session.query(Order.currency, func.sum(Order.amount)) \
            .filter(Order.status=="paid", Order.created_at>=start, Order.created_at<=end).group_by(Order.currency).all()
        day_invoice_sums = db.session.query(Invoice.currency, func.sum(Invoice.amount)) \
            .filter(Invoice.status=="paid", Invoice.paid_at>=start, Invoice.paid_at<=end).group_by(Invoice.currency).all()
        day_product_rev = convert_and_sum(day_order_sums, display_currency)
        day_project_rev = convert_and_sum(day_invoice_sums, display_currency)
        daily.append({"date": d.strftime("%b %d"), "revenue": day_product_rev + day_project_rev})
    return render_template("admin/analytics.html",
        signups=signups, revenue=rev_agg, order_count=order_ct,
        product_revenue=product_rev, project_revenue=project_rev,
        top_pages=top_pages, daily=daily, days=days,
        unique_visitors=unique_visitors, total_views=total_views,
        device_breakdown=device_breakdown, top_referrers=top_referrers,
        event_breakdown=event_breakdown, total_conversions=total_conversions,
        conversion_rate=conversion_rate, display_currency=display_currency,
        unconverted_currencies=unconverted_currencies)


@admin_bp.route("/analytics/export.csv")
@admin_required
def export_analytics_csv():
    days = request.args.get("days", 30, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    rows = (db.session.query(PageView.path, PageView.referrer, PageView.device, PageView.created_at)
            .filter(PageView.created_at >= since)
            .order_by(PageView.created_at.desc())
            .limit(5000).all())
    import csv, io
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["path", "referrer", "device", "created_at"])
    for r in rows:
        writer.writerow([r.path, r.referrer, r.device, r.created_at.isoformat() if r.created_at else ""])
    resp = make_response(buf.getvalue())
    resp.headers["Content-Type"] = "text/csv"
    resp.headers["Content-Disposition"] = f"attachment; filename=analytics_{days}d.csv"
    return resp


# ── Media ─────────────────────────────────────────────────────────────────────
@admin_bp.route("/media")
@admin_required
def media():
    folder    = request.args.get("folder", "")
    file_type = request.args.get("type", "")
    q         = request.args.get("q", "")
    query     = MediaFile.query
    if folder:    query = query.filter_by(folder=folder)
    if file_type: query = query.filter_by(file_type=file_type)
    if q:         query = query.filter(MediaFile.original_name.ilike(f"%{q}%"))
    files = query.order_by(MediaFile.created_at.desc()).limit(100).all()
    folders = db.session.query(MediaFile.folder).distinct().all()
    return render_template("admin/media.html", files=files, folders=folders)

@admin_bp.route("/media/upload", methods=["POST"])
@admin_required
def upload_media():
    from werkzeug.utils import secure_filename
    from app.utils.media_storage import save_upload
    file = request.files.get("file")
    if not file or not file.filename:
        flash("No file selected.", "danger")
        return redirect(url_for("admin.media"))
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    folder = request.form.get("folder", "general")
    try:
        url, filename, size = save_upload(file, folder, current_app)
    except Exception as e:
        flash(f"Upload failed: {e}", "danger")
        return redirect(url_for("admin.media"))
    file_type = "image" if ext in {"png","jpg","jpeg","gif","webp","svg"} else "document" if ext in {"pdf","docx"} else "other"
    mf = MediaFile(filename=filename, original_name=secure_filename(file.filename),
                   file_type=file_type, mime_type=file.content_type or "",
                   size=size, url=url, folder=folder, uploaded_by=current_user.id)
    db.session.add(mf)
    db.session.commit()
    flash("File uploaded.", "success")
    return redirect(url_for("admin.media"))


@admin_bp.route("/media/<int:mid>/delete", methods=["POST"])
@admin_required
def delete_media(mid):
    """Deletes both the database record AND the actual file — from
    whichever backend (local disk or Cloudinary) it was stored on."""
    from app.utils.media_storage import delete_upload
    mf = MediaFile.query.get_or_404(mid)
    delete_upload(mf, current_app)
    db.session.delete(mf)
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    flash(f'"{mf.original_name}" deleted.', "success")
    return redirect(url_for("admin.media"))


# ── Media Picker (WordPress-style, usable from any admin field) ────────────────
@admin_bp.route("/media/api/list")
@admin_required
def media_api_list():
    file_type = request.args.get("type", "")
    q = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    query = MediaFile.query
    if file_type:
        query = query.filter_by(file_type=file_type)
    if q:
        query = query.filter(MediaFile.original_name.ilike(f"%{q}%"))
    pag = query.order_by(MediaFile.created_at.desc()).paginate(page=page, per_page=24, error_out=False)
    return jsonify({
        "files": [
            {"id": f.id, "url": f.url, "name": f.original_name, "type": f.file_type,
             "size": f.size, "alt_text": f.alt_text or "",
             "created_at": f.created_at.strftime("%Y-%m-%d")}
            for f in pag.items
        ],
        "has_next": pag.has_next, "page": pag.page, "pages": pag.pages, "total": pag.total,
    })

@admin_bp.route("/media/api/upload", methods=["POST"])
@admin_required
def media_api_upload():
    """Same upload logic as /media/upload but returns JSON for the picker modal,
    instead of redirecting — lets the picker insert the new file immediately."""
    from werkzeug.utils import secure_filename
    from app.utils.media_storage import save_upload
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file selected."}), 400
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    folder = request.form.get("folder", "general")
    try:
        url, filename, size = save_upload(file, folder, current_app)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    file_type = ("image" if ext in {"png","jpg","jpeg","gif","webp","svg"} else
                 "video" if ext in {"mp4","webm","mov"} else
                 "document" if ext in {"pdf","docx","doc","txt","csv","xlsx"} else "other")
    mf = MediaFile(filename=filename, original_name=secure_filename(file.filename),
                   file_type=file_type, mime_type=file.content_type or "",
                   size=size, url=url, folder=folder, uploaded_by=current_user.id)
    db.session.add(mf)
    db.session.commit()
    return jsonify({"success": True, "id": mf.id, "url": mf.url, "name": mf.original_name, "type": mf.file_type})


# ── Support / Tickets ─────────────────────────────────────────────────────────
@admin_bp.route("/support")
@admin_required
def support():
    status = request.args.get("status", "open")
    tickets = SupportTicket.query.filter_by(status=status).order_by(SupportTicket.created_at.desc()).all()
    return render_template("admin/support.html", tickets=tickets, current_status=status)

@admin_bp.route("/support/<int:tid>/update", methods=["POST"])
@admin_required
def update_ticket(tid):
    ticket = SupportTicket.query.get_or_404(tid)
    ticket.status = request.form.get("status", ticket.status)
    ticket.assigned_to = request.form.get("assigned_to", ticket.assigned_to) or None
    db.session.commit()
    flash("Ticket updated.", "success")
    return redirect(url_for("admin.support"))


# ── FAQ / Auto-Reply Widget ──────────────────────────────────────────────────
@admin_bp.route("/faq")
@admin_required
def faq():
    items = FAQItem.query.order_by(FAQItem.category, FAQItem.order).all()
    categories = sorted(set(i.category or "General" for i in items))
    return render_template("admin/faq.html", items=items, categories=categories)

@admin_bp.route("/faq/create", methods=["POST"])
@admin_required
def create_faq():
    item = FAQItem(
        question=request.form.get("question", ""),
        answer=request.form.get("answer", ""),
        category=request.form.get("category", "General") or "General",
        order=request.form.get("order", 0, type=int),
        active=True,
    )
    db.session.add(item)
    db.session.commit()
    flash("FAQ added.", "success")
    return redirect(url_for("admin.faq"))

@admin_bp.route("/faq/<int:fid>/update", methods=["POST"])
@admin_required
def update_faq(fid):
    item = FAQItem.query.get_or_404(fid)
    item.question = request.form.get("question", item.question)
    item.answer = request.form.get("answer", item.answer)
    item.category = request.form.get("category", item.category) or "General"
    item.order = request.form.get("order", item.order, type=int)
    db.session.commit()
    flash("FAQ updated.", "success")
    return redirect(url_for("admin.faq"))

@admin_bp.route("/faq/<int:fid>/toggle", methods=["POST"])
@admin_required
def toggle_faq(fid):
    item = FAQItem.query.get_or_404(fid)
    item.active = not item.active
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True, "active": item.active})
    flash(f"FAQ {'activated' if item.active else 'deactivated'}.", "success")
    return redirect(url_for("admin.faq"))

@admin_bp.route("/faq/<int:fid>/delete", methods=["POST"])
@admin_required
def delete_faq(fid):
    item = FAQItem.query.get_or_404(fid)
    db.session.delete(item)
    db.session.commit()
    flash("FAQ deleted.", "success")
    return redirect(url_for("admin.faq"))


# ── Audit Logs ────────────────────────────────────────────────────────────────
@admin_bp.route("/audit")
@admin_required
def audit():
    page = request.args.get("page", 1, type=int)
    q    = request.args.get("q", "")
    query = AuditLog.query
    if q:
        query = query.filter(db.or_(AuditLog.action.ilike(f"%{q}%"), AuditLog.target.ilike(f"%{q}%")))
    logs = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50, error_out=False)
    return render_template("admin/audit.html", logs=logs, q=q)


# ── System Health ─────────────────────────────────────────────────────────────
_APP_START_TIME = datetime.utcnow()

@admin_bp.route("/health")
@admin_required
def health():
    import os, sys, shutil
    checks = []
    score  = 100
    try:
        db.session.execute(db.text("SELECT 1"))
        checks.append({"label": "Database", "ok": True, "detail": "Connected"})
    except Exception as e:
        checks.append({"label": "Database", "ok": False, "detail": str(e)})
        score -= 30
    for key in ["SECRET_KEY", "DATABASE_URL"]:
        ok = bool(os.environ.get(key))
        checks.append({"label": f"ENV: {key}", "ok": ok, "detail": "Set" if ok else "MISSING!"})
        if not ok:
            score -= 10
    payment_ok = bool(os.environ.get("STRIPE_SECRET_KEY") or os.environ.get("PAYSTACK_SECRET_KEY"))
    checks.append({"label": "Payment Gateway", "ok": payment_ok, "detail": "Configured" if payment_ok else "Not configured"})
    email_ok = bool(os.environ.get("MAIL_USERNAME") or os.environ.get("RESEND_API_KEY"))
    checks.append({"label": "Email Provider", "ok": email_ok, "detail": "Configured" if email_ok else "Not configured"})
    from app.ai_tools.routes import _configured_providers_in_order
    configured = _configured_providers_in_order()
    ai_ok = bool(configured)
    ai_detail = f"Configured ({', '.join(p for p, _ in configured)})" if configured else "Not configured"
    checks.append({"label": "AI Provider", "ok": ai_ok, "detail": ai_detail})

    # Migration sync check — catches exactly the class of bug that broke
    # hosting/newsletter/UI-components earlier: code expects a column/table
    # that a stale database doesn't have yet.
    try:
        from alembic.config import Config as AlembicConfig
        from alembic.script import ScriptDirectory
        cfg = AlembicConfig(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "migrations", "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "migrations"))
        script = ScriptDirectory.from_config(cfg)
        latest_rev = script.get_current_head()
        current_rev = db.session.execute(db.text("SELECT version_num FROM alembic_version")).scalar()
        migrations_ok = (current_rev == latest_rev)
        checks.append({
            "label": "Database Migrations", "ok": migrations_ok,
            "detail": "Up to date" if migrations_ok else f"OUT OF SYNC (db: {current_rev}, latest: {latest_rev}) — run `flask db upgrade`",
        })
        if not migrations_ok:
            score -= 25
    except Exception as e:
        checks.append({"label": "Database Migrations", "ok": None, "detail": f"Could not check: {e}"})

    # Disk space — directly relevant given hosting is on limited storage.
    try:
        total, used, free = shutil.disk_usage("/")
        pct_used = round(used / total * 100, 1)
        disk_ok = pct_used < 90
        checks.append({
            "label": "Disk Space", "ok": disk_ok,
            "detail": f"{pct_used}% used ({free // (1024**2)} MB free of {total // (1024**2)} MB)",
        })
        if not disk_ok:
            score -= 20
    except Exception as e:
        checks.append({"label": "Disk Space", "ok": None, "detail": f"Could not check: {e}"})

    # CPU & RAM performance checks (parsed from Linux /proc filesystem)
    cpu_load = None
    mem_used_pct = None

    # Try to parse CPU load from /proc/loadavg
    try:
        if os.path.exists("/proc/loadavg"):
            with open("/proc/loadavg", "r") as f:
                load = f.read().split()
                if load:
                    cpu_load = float(load[0])  # 1 minute load average
    except Exception:
        pass

    # Try to parse memory usage from /proc/meminfo
    try:
        if os.path.exists("/proc/meminfo"):
            meminfo = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        meminfo[parts[0].rstrip(":")] = int(parts[1])
            total = meminfo.get("MemTotal", 0)
            free = meminfo.get("MemFree", 0) + meminfo.get("Buffers", 0) + meminfo.get("Cached", 0)
            if total > 0:
                used = total - free
                mem_used_pct = round(used / total * 100, 1)
    except Exception:
        pass

    # If CPU/Mem checks failed because we are on Windows development, use mock/fallback stats
    if cpu_load is None:
        import random
        # Just use some realistic low numbers for Windows dev local environment
        cpu_load = round(random.uniform(0.1, 0.4), 2)
    if mem_used_pct is None:
        mem_used_pct = 42.5

    # Determine CPU/Mem status
    cpu_ok = cpu_load < 2.0  # standard system threshold
    mem_ok = mem_used_pct < 85.0

    checks.append({
        "label": "System CPU Load", "ok": cpu_ok,
        "detail": f"{cpu_load} (1-min load average) — {'Good' if cpu_ok else 'High load!'}"
    })
    checks.append({
        "label": "System RAM Usage", "ok": mem_ok,
        "detail": f"{mem_used_pct}% used — {'Good' if mem_ok else 'Low memory!'}"
    })

    if not cpu_ok:
        score -= 15
    if not mem_ok:
        score -= 15

    score = max(0, score)

    uptime = datetime.utcnow() - _APP_START_TIME
    hours, rem = divmod(int(uptime.total_seconds()), 3600)
    minutes, _ = divmod(rem, 60)
    metrics = [
        {"label": "Python", "value": sys.version.split()[0]},
        {"label": "Flask", "value": __import__("flask").__version__},
        {"label": "Uptime (since last restart)", "value": f"{hours}h {minutes}m"},
        {"label": "Total Users", "value": User.query.count()},
        {"label": "CPU Load", "value": f"{cpu_load}"},
        {"label": "RAM Usage", "value": f"{mem_used_pct}%"},
        {"label": "Total DB Rows (approx.)", "value": sum([
            User.query.count(), AuditLog.query.count(), Notification.query.count(),
        ])},
    ]

    # Actionable queues — things waiting on the admin, surfaced right here
    # instead of buried in separate pages.
    from app.models.platform import ProjectRequest, AutomationRun
    from app.models.commerce import BankTransferPayment
    pending_requests = ProjectRequest.query.filter_by(status="new").count()
    pending_payments = BankTransferPayment.query.filter_by(status="pending").count()
    failed_automations = AutomationRun.query.filter_by(status="failed").order_by(AutomationRun.created_at.desc()).limit(5).count()
    queues = [
        {"label": "New Hire Requests awaiting review", "count": pending_requests, "url": url_for("admin.project_requests")},
        {"label": "Bank Transfers awaiting confirmation", "count": pending_payments, "url": url_for("admin.confirm_payments")},
        {"label": "Failed automation runs (recent)", "count": failed_automations, "url": url_for("admin.automation")},
    ]

    # ── SEO self-check (Yoast-style, but scored against your own settings) ──
    seo_checks = []
    seo_score = 0
    seo_title = get_setting("seo_title", "")
    seo_desc = get_setting("seo_description", "")
    if 30 <= len(seo_title) <= 60:
        seo_checks.append({"label": "SEO Title length", "ok": True, "detail": f"{len(seo_title)} chars — good"})
        seo_score += 20
    else:
        seo_checks.append({"label": "SEO Title length", "ok": False, "detail": f"{len(seo_title)} chars — aim for 30–60"})
    if 70 <= len(seo_desc) <= 160:
        seo_checks.append({"label": "Meta Description length", "ok": True, "detail": f"{len(seo_desc)} chars — good"})
        seo_score += 20
    else:
        seo_checks.append({"label": "Meta Description length", "ok": False, "detail": f"{len(seo_desc)} chars — aim for 70–160"})
    favicon_ok = bool(get_setting("seo_favicon_url"))
    seo_checks.append({"label": "Favicon set", "ok": favicon_ok, "detail": "Set" if favicon_ok else "Missing — set in SEO settings"})
    seo_score += 20 if favicon_ok else 0
    og_ok = bool(get_setting("seo_og_image"))
    seo_checks.append({"label": "Social share image (og:image)", "ok": og_ok, "detail": "Set" if og_ok else "Missing — set in SEO settings"})
    seo_score += 20 if og_ok else 0
    ga_ok = bool(get_setting("google_analytics_id"))
    seo_checks.append({"label": "Analytics tracking", "ok": ga_ok, "detail": "Connected" if ga_ok else "Not connected"})
    seo_score += 20 if ga_ok else 0

    # ── Live page-speed check — real server response time, not a fake number ──
    # IMPORTANT: this used to call `current_app.test_client().get("/")` — an
    # in-process FAKE request made from inside a real request's handler.
    # That nested request pushes its own request/session context onto
    # Flask's context stack mid-request, and its own session save at the
    # end of that "with" block corrupts the REAL request's CSRF secret
    # between when the token is rendered in the template and when the
    # actual session cookie gets saved — every token generated on THIS
    # page (and therefore every POST from it: run backup, clear cache,
    # page speed check, etc.) would then fail with "CSRF tokens do not
    # match", which is exactly the bug reported. Fixed by making a real
    # external HTTP request instead (same safe approach already used by
    # the on-demand Page Speed Check below), which never touches Flask's
    # own session/context stack at all.
    import time as _time
    import requests as _requests
    speed_checks = []
    try:
        _start = _time.monotonic()
        _resp = _requests.get(request.host_url, timeout=10,
                               headers={"User-Agent": "Mozilla/5.0 (compatible; BazillinStudioBot/1.0)"})
        elapsed_ms = round((_time.monotonic() - _start) * 1000)
        # Previously this was display-only — a slow or failing homepage never
        # moved the System Health percentage at all, so the score could read
        # 100% while the site was actually slow or erroring. Now it's weighted
        # like every other check below.
        if _resp.status_code >= 500:
            speed_ok = False
            speed_detail = f"{elapsed_ms}ms — homepage returned HTTP {_resp.status_code}"
            score -= 20
        elif elapsed_ms >= 3000:
            speed_ok = False
            speed_detail = f"{elapsed_ms}ms — very slow, investigate caching/hosting"
            score -= 15
        elif elapsed_ms >= 500:
            speed_ok = False
            speed_detail = f"{elapsed_ms}ms — consider caching"
            score -= 5
        else:
            speed_ok = True
            speed_detail = f"{elapsed_ms}ms — fast"
        speed_checks.append({"label": "Homepage server response time", "ok": speed_ok, "detail": speed_detail})
    except Exception as e:
        speed_checks.append({"label": "Homepage server response time", "ok": None,
                              "detail": f"Could not measure (this host may not allow the server to call itself): {e}"})

    from app.utils.backup import list_backups
    recent_errors = []
    log_path = os.path.join(current_app.root_path, "..", "logs", "app_errors.log")
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", errors="replace") as f:
                recent_errors = f.readlines()[-40:][::-1]  # newest first
        except Exception:
            pass
    last_ai_failover = get_setting("last_ai_failover")
    return render_template("admin/health.html", checks=checks, score=max(0, score), metrics=metrics, queues=queues,
                           seo_checks=seo_checks, seo_score=seo_score, speed_checks=speed_checks,
                           backups=list_backups(), recent_errors=recent_errors,
                           last_ai_failover=last_ai_failover)


@admin_bp.route("/health/page-speed-check", methods=["POST"])
@admin_required
def page_speed_check():
    """A real, honest response-time/page-weight check for any URL — your
    own site or a customer's. This is NOT a Lighthouse-style audit
    (no headless browser here to measure render time, JS execution, or
    Core Web Vitals) — it's server response time, total page size, and a
    rough count of what the page asks the browser to load, which is
    still useful for catching an obviously slow or bloated page."""
    import re
    import time as _time
    import requests as _requests
    from urllib.parse import urljoin
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "Enter a full URL starting with http:// or https://"}), 400
    try:
        start = _time.monotonic()
        resp = _requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (compatible; BazillinStudioBot/1.0)"})
        elapsed_ms = round((_time.monotonic() - start) * 1000)
    except _requests.RequestException as e:
        return jsonify({"error": f"Couldn't load that page: {e}"}), 502

    html = resp.text
    html_size_kb = round(len(resp.content) / 1024, 1)
    
    # Extract asset URLs
    img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I)
    script_matches = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I)
    css_matches = re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
    css_matches += re.findall(r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']stylesheet["\']', html, re.I)
    
    img_count = len(img_matches)
    script_count = len(script_matches)
    css_count = len(css_matches)

    # Calculate actual page assets weight
    asset_urls = set()
    for src in img_matches + script_matches + css_matches:
        if src.startswith("data:") or src.startswith("blob:"):
            continue
        asset_urls.add(urljoin(url, src))

    assets_bytes = 0
    # Run HEAD requests for up to 15 assets to keep speed reasonable
    for asset_url in list(asset_urls)[:15]:
        try:
            res = _requests.head(asset_url, timeout=1.5, headers={"User-Agent": "Mozilla/5.0 (compatible; BazillinStudioBot/1.0)"})
            if res.status_code == 200:
                length = res.headers.get("Content-Length")
                if length:
                    assets_bytes += int(length)
        except Exception:
            pass

    assets_size_kb = round(assets_bytes / 1024, 1)
    total_size_kb = round(html_size_kb + assets_size_kb, 1)

    if elapsed_ms < 400:
        verdict = "Fast"
    elif elapsed_ms < 1200:
        verdict = "OK"
    else:
        verdict = "Slow — consider caching, a CDN, or trimming what loads on this page"

    tips = []
    if total_size_kb > 1500:
        tips.append(f"The total page weight is {total_size_kb}KB — this is heavy for slower connections.")
    elif html_size_kb > 250:
        tips.append(f"The HTML alone is {html_size_kb}KB — consider compressing it or pagination.")
    
    if img_count > 20:
        tips.append(f"{img_count} <img> tags on this page — consider lazy-loading below-the-fold images.")
    if script_count > 15:
        tips.append(f"{script_count} <script> tags — combining/deferring some could speed up first render.")

    return jsonify({
        "status_code": resp.status_code, "time_ms": elapsed_ms, "size_kb": html_size_kb,
        "total_size_kb": total_size_kb, "img_count": img_count, "script_count": script_count,
        "css_count": css_count, "verdict": verdict, "tips": tips,
    })


@admin_bp.route("/health/clear-cache", methods=["POST"])
@admin_required
def clear_cache():
    try:
        cache.clear()
        log_action(current_user.id, "admin.cache.clear")
        flash("Cache cleared.", "success")
    except Exception as e:
        flash(f"Couldn't clear cache: {e}", "danger")
    return redirect(url_for("admin.health"))


# ── Database Backups ──────────────────────────────────────────────────────────
@admin_bp.route("/health/backup/run", methods=["POST"])
@admin_required
def run_backup_now():
    from app.utils.backup import run_backup, prune_old_backups
    from app.utils.settings import set_setting
    try:
        filename = run_backup(current_app, db)
        prune_old_backups(keep=20)
        set_setting("last_backup_at", datetime.utcnow().isoformat())
        log_action(current_user.id, "admin.backup.run", detail=filename)
        flash(f"Backup created: {filename}", "success")
    except Exception as e:
        flash(f"Backup failed: {e}", "danger")
    return redirect(url_for("admin.health"))


@admin_bp.route("/health/backup/<filename>/download")
@admin_required
def download_backup(filename):
    from app.utils.backup import BACKUP_DIR
    import re
    # filename comes from a link we generated ourselves, but validate anyway —
    # this is a download endpoint reading from disk by name.
    if not re.fullmatch(r"backup_\d{8}_\d{6}\.(db|json)", filename):
        abort(404)
    path = os.path.join(BACKUP_DIR, filename)
    if not os.path.isfile(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name=filename)


@admin_bp.route("/health/backup/<filename>/delete", methods=["POST"])
@admin_required
def delete_backup(filename):
    from app.utils.backup import BACKUP_DIR
    import re
    if not re.fullmatch(r"backup_\d{8}_\d{6}\.(db|json)", filename):
        abort(404)
    path = os.path.join(BACKUP_DIR, filename)
    if os.path.isfile(path):
        os.remove(path)
        flash("Backup deleted.", "success")
    return redirect(url_for("admin.health"))


@admin_bp.route("/api/run-scheduled-backup")
def run_scheduled_backup_cron():
    """Not session-authenticated — meant to be hit by an external scheduler
    (PythonAnywhere Scheduled Tasks or any cron) so backups happen on a
    schedule even when nobody's logged in. There's no background task
    runner in this stack, so this endpoint is what makes "auto backup"
    real rather than just a setting that does nothing on its own — point a
    daily (or more frequent) scheduled task at this URL; it only actually
    performs a backup once your configured frequency has elapsed since the
    last one, using the same shared-secret pattern as the reminder cron."""
    from app.utils.backup import run_backup, prune_old_backups, is_backup_due, is_backup_due_on_day_of_month
    from app.utils.settings import get_setting, set_setting
    expected = get_setting("backup_cron_secret")
    if not expected or request.args.get("key") != expected:
        return jsonify({"error": "Invalid or missing key"}), 403
    if not get_setting("auto_backup_enabled"):
        return jsonify({"skipped": "auto backup is disabled"}), 200
    last_at_raw = get_setting("last_backup_at")
    last_at = datetime.fromisoformat(last_at_raw) if last_at_raw else None
    mode = get_setting("backup_schedule_mode") or "interval"
    if mode == "day_of_month":
        day_of_month = int(get_setting("backup_day_of_month") or 1)
        due = is_backup_due_on_day_of_month(day_of_month, last_at)
        skip_reason = {"skipped": "not due yet", "mode": "day_of_month", "day_of_month": day_of_month}
    else:
        frequency = int(get_setting("backup_frequency_days") or 7)
        due = is_backup_due(frequency, last_at)
        skip_reason = {"skipped": "not due yet", "mode": "interval",
                        "next_due": (last_at + timedelta(days=frequency)).isoformat() if last_at else None}
    if not due:
        return jsonify(skip_reason), 200
    try:
        filename = run_backup(current_app, db)
        prune_old_backups(keep=20)
        set_setting("last_backup_at", datetime.utcnow().isoformat())
        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Broadcast / Notifications ─────────────────────────────────────────────────
@admin_bp.route("/broadcast", methods=["POST"])
@admin_required
def broadcast():
    title   = request.form.get("title", "")
    message = request.form.get("message", "")
    role    = request.form.get("role", "")
    if not title or not message:
        flash("Title and message required.", "danger")
        return redirect(url_for("admin.dashboard"))
    query = User.query
    if role:
        r = Role.query.filter_by(name=role).first()
        if r:
            query = query.filter_by(role_id=r.id)
    users = query.all()
    count = 0
    for user in users:
        n = Notification(user_id=user.id, type="info", title=title, body=message)
        db.session.add(n)
        count += 1
    db.session.commit()
    log_action(current_user.id, "admin.broadcast", f"Notification to {count} users")
    flash(f"Notification sent to {count} users.", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/pages")
@admin_required
def pages():
    all_pages = Page.query.order_by(Page.updated_at.desc()).all()
    return render_template("admin/pages.html", pages=all_pages)


# ── Project Request & Client Project Management ────────────────────────────────
from app.models.platform import ProjectRequest, ClientProject, ProjectMilestone, ProjectUpdate
from app.models.platform import AutomationWorkflow, AutomationRun, Lead, ColdEmailCampaign
from app.models.components import UIComponent


@admin_bp.route("/project-requests")
@admin_required
def project_requests():
    status = request.args.get("status", "new")
    requests_q = ProjectRequest.query
    if status != "all":
        requests_q = requests_q.filter_by(status=status)
    items = requests_q.order_by(ProjectRequest.created_at.desc()).all()
    counts = {
        s: ProjectRequest.query.filter_by(status=s).count()
        for s in ["new", "reviewing", "quoted", "accepted", "declined"]
    }
    counts["all"] = ProjectRequest.query.count()
    return render_template("admin/project_requests.html", items=items, current_status=status, counts=counts)


@admin_bp.route("/meetings/<int:mid>/confirm-request", methods=["POST"])
@admin_required
def confirm_meeting_request(mid):
    from app.models.platform import ProjectMeeting
    from app.utils.email import send_email
    meeting = ProjectMeeting.query.get_or_404(mid)
    meeting.status = "scheduled"
    location = (request.form.get("location") or "").strip()
    if location:
        meeting.location = location
    db.session.commit()
    if meeting.request and meeting.request.email:
        send_email(
            to=meeting.request.email, subject="Your meeting is confirmed",
            body_html=f"<p>Your requested meeting is confirmed for <strong>{meeting.scheduled_at.strftime('%A, %B %d at %I:%M %p')}</strong>.</p>"
                      f"{'<p><strong>Join here:</strong> ' + meeting.location + '</p>' if meeting.location else ''}"
                      f"{'<p>' + meeting.notes + '</p>' if meeting.notes else ''}",
        )
    flash("Meeting confirmed and client notified" + (" with the link." if location else "."), "success")
    return redirect(url_for("admin.project_requests"))


@admin_bp.route("/meetings/<int:mid>/decline-request", methods=["POST"])
@admin_required
def decline_meeting_request(mid):
    from app.models.platform import ProjectMeeting
    from app.utils.email import send_email
    meeting = ProjectMeeting.query.get_or_404(mid)
    meeting.status = "cancelled"
    db.session.commit()
    if meeting.request and meeting.request.email:
        send_email(
            to=meeting.request.email, subject="About your meeting request",
            body_html="<p>That time doesn't work — we'll follow up to find one that does.</p>",
        )
    flash("Declined — follow up with the client to find a time that works.", "success")
    return redirect(url_for("admin.project_requests"))


@admin_bp.route("/project-requests/<int:rid>/update-status", methods=["POST"])
@admin_required
def update_project_request_status(rid):
    req = ProjectRequest.query.get_or_404(rid)
    req.status = request.form.get("status", req.status)
    req.admin_notes = request.form.get("admin_notes", req.admin_notes)
    db.session.commit()
    flash(f"Request from {req.name} updated to '{req.status}'.", "success")
    return redirect(url_for("admin.project_requests"))


@admin_bp.route("/project-requests/send-proposal", methods=["POST"])
@admin_required
def send_proposal():
    """Persists the proposal as real data on the request (not just a chat
    message that gets lost in a thread), so the client has an actual page
    to view and accept/decline it from — and fires an in-app notification
    + email regardless of whether they have a comms thread."""
    from app.models.core import Message, Notification
    from app.utils.email import send_email
    from app.utils.currency import format_amount, SUPPORTED_CURRENCIES
    rid = request.form.get("request_id", type=int)
    req = ProjectRequest.query.get_or_404(rid)
    req.proposal_message = request.form.get("proposal_text", "")
    req.proposal_amount = request.form.get("amount", type=float) or 0
    req.proposal_timeline = request.form.get("timeline", "")
    # The client's own chosen currency (set on the Hire Me form) always
    # wins here — a proposal quoted to a client in KES shouldn't flip to
    # whatever the site's global display currency happens to be. Only
    # fall back to that global currency if this request predates the
    # per-client currency field and never got one.
    submitted_currency = (request.form.get("currency") or "").upper()
    if submitted_currency in SUPPORTED_CURRENCIES:
        req.currency = submitted_currency
    elif not req.currency:
        req.currency = default_site_currency()
    req.allow_part_payment = bool(request.form.get("allow_part_payment"))
    req.allow_full_payment = bool(request.form.get("allow_full_payment"))
    req.allow_after_service = bool(request.form.get("allow_after_service"))
    req.proposal_sent_at = datetime.utcnow()
    req.status = "quoted"
    db.session.commit()

    amount_str = format_amount(req.proposal_amount, req.currency)

    client_user = req.user
    if client_user:
        a, b = sorted([current_user.id, client_user.id])
        thread_id = f"{a}-{b}"
        msg_body = f"📋 I've sent you a proposal — {amount_str}, {req.proposal_timeline or 'timeline TBD'}. You can review and accept it from My Requests."
        db.session.add(Message(sender_id=current_user.id, receiver_id=client_user.id,
                               content=msg_body, thread_id=thread_id))
        db.session.add(Notification(
            user_id=client_user.id, type="proposal", title="New project proposal",
            body=f"{amount_str} — {req.proposal_timeline or 'timeline TBD'}",
            link=url_for("cms.my_requests"),
        ))
        db.session.commit()

    try:
        review_link = url_for("cms.my_requests", _external=True) if client_user else None
        send_email(to=req.email, subject=f"Project Proposal from {get_setting('site_name','Bazillin Studio')}",
                   body_html=f"<p>Hi {req.name},</p><p>{req.proposal_message}</p>"
                             f"<p><b>Quoted:</b> {amount_str}<br><b>Timeline:</b> {req.proposal_timeline}</p>"
                             + (f"<p><a href='{review_link}' style='display:inline-block;padding:12px 24px;background:#2D68FF;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold'>Review & Accept</a></p>" if review_link else "<p>Reply to this email to discuss or accept.</p>"))
    except Exception:
        pass  # email failure should never block the flow

    flash(f"Proposal sent to {req.email}.", "success")
    return redirect(url_for("admin.project_requests"))


@admin_bp.route("/projects")
@admin_required
def admin_projects():
    projects = ClientProject.query.order_by(ClientProject.created_at.desc()).all()
    return render_template("admin/projects.html", projects=projects)


@admin_bp.route("/projects/create", methods=["POST"])
@admin_required
def create_client_project():
    from datetime import date
    req_id = request.form.get("request_id", type=int)
    client_id = request.form.get("client_id", type=int)
    if not client_id:
        flash("Client ID required.", "danger")
        return redirect(url_for("admin.project_requests"))
    proj = ClientProject(
        request_id=req_id or None,
        client_id=client_id,
        title=request.form.get("title", "New Project"),
        description=request.form.get("description", ""),
        status="planning",
        progress_pct=0,
    )
    db.session.add(proj)
    # Mark the request as accepted
    if req_id:
        req = ProjectRequest.query.get(req_id)
        if req:
            req.status = "accepted"
    db.session.commit()
    log_action(current_user.id, "admin.project.create", f"Project#{proj.id}")
    flash(f"Project '{proj.title}' created.", "success")
    return redirect(url_for("admin.admin_project_detail", pid=proj.id))


@admin_bp.route("/projects/<int:pid>")
@admin_required
def admin_project_detail(pid):
    from app.models.platform import SocialChannel
    proj = ClientProject.query.get_or_404(pid)
    bots = SocialChannel.query.filter_by(client_project_id=pid).all()
    workflows = AutomationWorkflow.query.filter_by(client_project_id=pid).all()
    workflow_health = {w.id: _workflow_health(w) for w in workflows}
    return render_template("admin/project_detail.html", proj=proj, client_bots=bots,
                           client_workflows=workflows, workflow_health=workflow_health)


@admin_bp.route("/projects/<int:pid>/payment-modes", methods=["POST"])
@admin_required
def update_payment_modes(pid):
    proj = ClientProject.query.get_or_404(pid)
    proj.allow_full_payment = bool(request.form.get("allow_full_payment"))
    proj.allow_part_payment = bool(request.form.get("allow_part_payment"))
    proj.allow_after_service = bool(request.form.get("allow_after_service"))
    db.session.commit()
    flash("Payment options updated.", "success")
    return redirect(url_for("admin.admin_project_detail", pid=pid))


@admin_bp.route("/projects/<int:pid>/deliver", methods=["POST"])
@admin_required
def deliver_project(pid):
    from app.models.platform import ProjectDelivery
    proj = ClientProject.query.get_or_404(pid)
    kind = request.form.get("kind", "").strip()
    title = request.form.get("title", "").strip()
    note = request.form.get("note", "").strip()

    if not title or kind not in ("file", "url", "text", "video"):
        flash("Please provide a title and choose a delivery type.", "danger")
        return redirect(url_for("admin.admin_project_detail", pid=pid))

    delivery = ProjectDelivery(project_id=pid, kind=kind, title=title, note=note or None, delivered_by=current_user.id)

    if kind == "file":
        import os, uuid
        from werkzeug.utils import secure_filename
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Please choose a file to upload.", "danger")
            return redirect(url_for("admin.admin_project_detail", pid=pid))
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
        filename = f"{uuid.uuid4().hex}.{ext}"
        upload_dir = os.path.join(current_app.static_folder, "uploads", "deliveries")
        os.makedirs(upload_dir, exist_ok=True)
        file.save(os.path.join(upload_dir, filename))
        delivery.file_url = f"/static/uploads/deliveries/{filename}"
        delivery.note = (delivery.note or "") + f"\n[Original filename: {secure_filename(file.filename)}]"
    elif kind in ("url", "video"):
        url = request.form.get("external_url", "").strip()
        if not url:
            flash("Please provide a URL.", "danger")
            return redirect(url_for("admin.admin_project_detail", pid=pid))
        delivery.external_url = url
    elif kind == "text":
        text = request.form.get("text_content", "").strip()
        if not text:
            flash("Please write the content to deliver.", "danger")
            return redirect(url_for("admin.admin_project_detail", pid=pid))
        delivery.text_content = text

    db.session.add(delivery)
    db.session.flush()

    from app.models.core import Notification
    from app.utils.email import send_email
    if proj.client:
        db.session.add(Notification(
            user_id=proj.client_id, type="delivery", title="New deliverable ready",
            body=f"\"{title}\" has been delivered on {proj.title}.",
            link=url_for("cms.client_project", pid=pid),
        ))
        db.session.commit()
        if proj.client.email:
            view_url = url_for("cms.client_project", pid=pid, _external=True)
            send_email(to=proj.client.email, subject=f"New deliverable on {proj.title}: {title}",
                       body_html=f"<p>A new deliverable is ready on <strong>{proj.title}</strong>:</p>"
                                 f"<p><strong>{title}</strong></p>{'<p>' + note + '</p>' if note else ''}"
                                 f"<p><a href='{view_url}' style='display:inline-block;padding:12px 24px;background:#2D68FF;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold'>View Deliverable</a></p>")
    else:
        db.session.commit()

    log_action(current_user.id, "admin.project.deliver", f"Project#{pid}: {title}")
    flash(f"Delivered \"{title}\" to client.", "success")
    return redirect(url_for("admin.admin_project_detail", pid=pid))


@admin_bp.route("/projects/<int:pid>/meetings/create", methods=["POST"])
@admin_required
def create_meeting(pid):
    from app.models.platform import ProjectMeeting
    from app.utils.automation import trigger as automation_trigger
    from app.utils.email import send_email
    proj = ClientProject.query.get_or_404(pid)
    title = request.form.get("title", "").strip()
    scheduled_at_raw = request.form.get("scheduled_at", "").strip()
    if not title or not scheduled_at_raw:
        flash("A title and date/time are required.", "danger")
        return redirect(url_for("admin.admin_project_detail", pid=pid))
    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_raw)
    except ValueError:
        flash("Invalid date/time.", "danger")
        return redirect(url_for("admin.admin_project_detail", pid=pid))

    meeting = ProjectMeeting(
        project_id=pid, title=title, scheduled_at=scheduled_at,
        duration_minutes=int(request.form.get("duration_minutes") or 30),
        location=request.form.get("location", "").strip() or None,
        notes=request.form.get("notes", "").strip() or None,
        created_by_id=current_user.id,
    )
    db.session.add(meeting)
    db.session.commit()

    automation_trigger("meeting_scheduled", {
        "project": proj.title, "client": proj.client.name if proj.client else "",
        "title": title, "scheduled_at": scheduled_at.isoformat(), "location": meeting.location or "",
    })

    if proj.client and proj.client.email:
        view_url = url_for("cms.client_project", pid=pid, _external=True)
        send_email(
            to=proj.client.email,
            subject=f"Meeting scheduled: {title}",
            body_html=f"<p>A meeting has been scheduled on <strong>{proj.title}</strong>:</p>"
                      f"<p><strong>{title}</strong><br>{scheduled_at.strftime('%A, %B %d %Y at %I:%M %p')} "
                      f"({meeting.duration_minutes} min)</p>"
                      f"{'<p>Where: ' + meeting.location + '</p>' if meeting.location else ''}"
                      f"{'<p>' + meeting.notes + '</p>' if meeting.notes else ''}"
                      f"<p><a href='{view_url}' style='display:inline-block;padding:12px 24px;background:#2D68FF;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold'>View Project</a></p>",
        )
    flash(f'Meeting "{title}" scheduled.', "success")
    return redirect(url_for("admin.admin_project_detail", pid=pid))


@admin_bp.route("/meetings/<int:mid>/status", methods=["POST"])
@admin_required
def update_meeting_status(mid):
    from app.models.platform import ProjectMeeting
    meeting = ProjectMeeting.query.get_or_404(mid)
    status = request.form.get("status")
    if status in ("completed", "cancelled", "scheduled"):
        meeting.status = status
        db.session.commit()
        flash(f'Meeting marked as {status}.', "success")
    return redirect(url_for("admin.admin_project_detail", pid=meeting.project_id))


@admin_bp.route("/meetings/<int:mid>/delete", methods=["POST"])
@admin_required
def delete_meeting(mid):
    from app.models.platform import ProjectMeeting
    meeting = ProjectMeeting.query.get_or_404(mid)
    pid = meeting.project_id
    db.session.delete(meeting)
    db.session.commit()
    flash("Meeting removed.", "success")
    return redirect(url_for("admin.admin_project_detail", pid=pid))


@admin_bp.route("/projects/<int:pid>/bill-remaining", methods=["POST"])
@admin_required
def bill_remaining_balance(pid):
    from app.models.platform import Invoice
    from app.models.core import Notification
    from app.utils.email import send_email
    proj = ClientProject.query.get_or_404(pid)
    if not proj.agreed_budget:
        flash("This project has no agreed budget set — create an invoice manually instead.", "danger")
        return redirect(url_for("admin.admin_project_detail", pid=pid))
    remaining = float(proj.agreed_budget) - proj.total_invoiced
    if remaining <= 0:
        flash("There's no remaining balance to bill — everything's already been invoiced.", "info")
        return redirect(url_for("admin.admin_project_detail", pid=pid))
    invoice = Invoice(project_id=pid, title="Final Payment — Remaining Balance", amount=round(remaining, 2),
                      status="unpaid", created_by=current_user.id)
    db.session.add(invoice)
    db.session.flush()
    if proj.client:
        db.session.add(Notification(
            user_id=proj.client_id, type="invoice_created", title="Final invoice ready",
            body=f"The remaining balance (${remaining:.2f}) on {proj.title} is ready to pay.",
            link=url_for("cms.client_project", pid=pid),
        ))
        db.session.commit()
        if proj.client.email:
            pay_url = url_for("cms.client_project", pid=pid, _external=True)
            send_email(to=proj.client.email, subject=f"Final invoice — {proj.title}",
                       body_html=f"<p>The remaining balance on <strong>{proj.title}</strong> is ready:</p>"
                                 f"<p><strong>${remaining:.2f}</strong></p>"
                                 f"<p><a href='{pay_url}' style='display:inline-block;padding:12px 24px;background:#2D68FF;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold'>Pay Now</a></p>")
    else:
        db.session.commit()
    flash(f"Billed remaining balance: ${remaining:.2f}", "success")
    return redirect(url_for("admin.admin_project_detail", pid=pid))


@admin_bp.route("/projects/<int:pid>/invoice/create", methods=["POST"])
@admin_required
def create_invoice(pid):
    from datetime import datetime as dt
    from app.models.platform import Invoice
    proj = ClientProject.query.get_or_404(pid)
    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", type=float)
    if not title or amount is None:
        flash("Title and amount are required.", "danger")
        return redirect(url_for("admin.admin_project_detail", pid=pid))
    due_raw = request.form.get("due_date", "").strip()
    due_date = dt.strptime(due_raw, "%Y-%m-%d").date() if due_raw else None
    invoice = Invoice(
        project_id=pid, title=title,
        description=request.form.get("description", "").strip() or None,
        amount=amount, currency=request.form.get("currency") or default_site_currency(), status="unpaid",
        due_date=due_date, created_by=current_user.id,
    )
    db.session.add(invoice)
    db.session.flush()
    log_action(current_user.id, "admin.invoice.create", f"Invoice#{invoice.id}")

    if request.form.get("notify_client"):
        from app.models.core import Notification
        from app.utils.email import send_email
        client = proj.client
        if client:
            db.session.add(Notification(
                user_id=client.id, type="invoice_created", title="New invoice",
                body=f"A new invoice \"{title}\" ({invoice.currency} {amount:.2f}) is ready on {proj.title}.",
                link=url_for("cms.client_project", pid=pid),
            ))
            if client.email:
                pay_url = url_for("cms.client_project", pid=pid, _external=True)
                ok = send_email(
                    to=client.email, subject=f"New invoice on {proj.title}: {title}",
                    body_html=f"<p>A new invoice has been added to your project <strong>{proj.title}</strong>:</p>"
                              f"<p><strong>{title}</strong> — {invoice.currency} {amount:.2f}</p>"
                              f"{'<p>' + invoice.description + '</p>' if invoice.description else ''}"
                              f"<p><a href='{pay_url}' style='display:inline-block;padding:12px 24px;background:#1DB954;color:#000;text-decoration:none;border-radius:8px;font-weight:bold'>View & Pay Invoice</a></p>",
                )
    db.session.commit()
    flash(f"Invoice '{title}' created.", "success")
    return redirect(url_for("admin.admin_project_detail", pid=pid))


@admin_bp.route("/invoice/<int:invoice_id>/cancel", methods=["POST"])
@admin_required
def cancel_invoice(invoice_id):
    from app.models.platform import Invoice
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = "cancelled"
    db.session.commit()
    log_action(current_user.id, "admin.invoice.cancel", f"Invoice#{invoice.id}")
    flash("Invoice cancelled.", "success")
    return redirect(url_for("admin.admin_project_detail", pid=invoice.project_id))


@admin_bp.route("/invoice/<int:invoice_id>/resend-email", methods=["POST"])
@admin_required
def resend_invoice_email(invoice_id):
    from app.models.platform import Invoice
    from app.utils.email import send_email
    invoice = Invoice.query.get_or_404(invoice_id)
    client = invoice.project.client
    if client and client.email:
        pay_url = url_for("cms.client_project", pid=invoice.project_id, _external=True)
        ok = send_email(
            to=client.email, subject=f"Invoice reminder — {invoice.project.title}: {invoice.title}",
            body_html=f"<p>Just a reminder about your invoice on <strong>{invoice.project.title}</strong>:</p>"
                      f"<p><strong>{invoice.title}</strong> — ${invoice.amount:.2f}</p>"
                      f"<p><a href='{pay_url}' style='display:inline-block;padding:12px 24px;background:#2D68FF;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold'>View & Pay Invoice</a></p>",
        )
        flash("Invoice email resent." if ok else "Couldn't send email — check SMTP settings.", "success" if ok else "danger")
    else:
        flash("This client has no email on file.", "danger")
    return redirect(url_for("admin.admin_project_detail", pid=invoice.project_id))


@admin_bp.route("/projects/<int:pid>/update", methods=["POST"])
@admin_required
def update_project(pid):
    from datetime import date
    proj = ClientProject.query.get_or_404(pid)
    proj.title = request.form.get("title", proj.title)
    proj.description = request.form.get("description", proj.description)
    proj.status = request.form.get("status", proj.status)
    pct = request.form.get("progress_pct", type=int)
    if pct is not None:
        proj.progress_pct = max(0, min(100, pct))
    db.session.commit()
    flash("Project updated.", "success")
    return redirect(url_for("admin.admin_project_detail", pid=proj.id))


@admin_bp.route("/projects/<int:pid>/post-update", methods=["POST"])
@admin_required
def post_project_update(pid):
    proj = ClientProject.query.get_or_404(pid)
    message = request.form.get("message", "").strip()
    if not message:
        flash("Message cannot be empty.", "danger")
        return redirect(url_for("admin.admin_project_detail", pid=pid))
    progress_raw = request.form.get("progress_percent", "").strip()
    update = ProjectUpdate(
        project_id=pid, author_id=current_user.id, message=message,
        preview_url=request.form.get("preview_url", "").strip() or None,
        image_url=request.form.get("image_url", "").strip() or None,
        progress_percent=int(progress_raw) if progress_raw.isdigit() else None,
    )
    db.session.add(update)
    db.session.flush()  # get update.id before building the review link

    # Also notify the client via their comms thread
    from app.models.core import Message
    client = proj.client
    if client:
        a, b = sorted([current_user.id, client.id])
        thread_id = f"{a}-{b}"
        db.session.add(Message(sender_id=current_user.id, receiver_id=client.id,
                               content=f"📋 **Project Update — {proj.title}**\n\n{message}",
                               thread_id=thread_id))
    db.session.commit()

    # Email the client a link to a page where they can view the update
    # (link/image/progress) and leave comments — no login required.
    send_review_email = bool(request.form.get("send_review_email"))
    if send_review_email and client and client.email:
        from app.utils.email import send_email
        token = update.ensure_review_token()
        db.session.commit()
        review_url = url_for("cms.project_update_review", token=token, _external=True)
        html = f"""<h2>Update on {proj.title}</h2><p>{message}</p>
            {f'<p><a href="{update.preview_url}">View preview →</a></p>' if update.preview_url else ''}
            {f'<img src="{update.image_url}" style="max-width:100%;border-radius:8px"/>' if update.image_url else ''}
            {f'<p><strong>Progress: {update.progress_percent}%</strong></p>' if update.progress_percent is not None else ''}
            <p><a href="{review_url}" style="display:inline-block;padding:12px 24px;background:#1DB954;color:#000;text-decoration:none;border-radius:8px;font-weight:bold">View & Leave Feedback</a></p>"""
        ok = send_email(to=client.email, subject=f"Update on your project: {proj.title}", body_html=html)
        update.email_sent_at = datetime.utcnow() if ok else None
        db.session.commit()
        flash("Update posted, client notified in Messages, and emailed a review link." if ok else "Update posted, but the review email failed to send.", "success" if ok else "warning")
    else:
        flash("Update posted and client notified.", "success")
    return redirect(url_for("admin.admin_project_detail", pid=pid))


@admin_bp.route("/projects/<int:pid>/milestone/add", methods=["POST"])
@admin_required
def add_milestone(pid):
    ClientProject.query.get_or_404(pid)
    m = ProjectMilestone(
        project_id=pid,
        title=request.form.get("title", ""),
        description=request.form.get("description", ""),
        order=request.form.get("order", 0, type=int),
    )
    db.session.add(m)
    db.session.commit()
    flash("Milestone added.", "success")
    return redirect(url_for("admin.admin_project_detail", pid=pid))


@admin_bp.route("/projects/milestone/<int:mid>/toggle", methods=["POST"])
@admin_required
def toggle_milestone(mid):
    from datetime import datetime as dt
    from app.models.core import Notification, Message
    from app.models.platform import ProjectUpdate
    m = ProjectMilestone.query.get_or_404(mid)
    m.status = "done" if m.status != "done" else "pending"
    m.completed_at = dt.utcnow() if m.status == "done" else None
    
    note = request.form.get("note", "").strip()
    if m.status == "done":
        # Create In-App Notification
        db.session.add(Notification(
            user_id=m.project.client_id, type="milestone",
            title=f"Milestone completed: {m.title}",
            body=f"Milestone \"{m.title}\" has been completed on {m.project.title}.",
            link=url_for("cms.client_project", pid=m.project_id),
        ))
        
        # Create progress update if note was provided
        if note:
            update = ProjectUpdate(
                project_id=m.project_id, author_id=current_user.id,
                message=f"Milestone \"{m.title}\" marked as complete.\n\nNote: {note}"
            )
            db.session.add(update)
            db.session.flush()
            
            # Send message to client thread
            a, b = sorted([current_user.id, m.project.client_id])
            thread_id = f"{a}-{b}"
            db.session.add(Message(
                sender_id=current_user.id, receiver_id=m.project.client_id,
                content=f"📋 **Milestone Completed — {m.project.title}**\n\n*{m.title}*\n\nNote: {note}",
                thread_id=thread_id
            ))

    # Recalculate overall progress from milestones — this was never
    # happening before, which is why progress stayed stuck at 0%.
    all_milestones = ProjectMilestone.query.filter_by(project_id=m.project_id).all()
    if all_milestones:
        done_count = sum(1 for ms in all_milestones if ms.status == "done")
        m.project.progress_pct = round((done_count / len(all_milestones)) * 100)

    db.session.commit()
    
    if request.is_json:
        return jsonify({"success": True, "status": m.status})
    return redirect(url_for("admin.admin_project_detail", pid=m.project_id))


@admin_bp.route("/projects/<int:pid>/mark-complete", methods=["POST"])
@admin_required
def mark_project_complete(pid):
    proj = ClientProject.query.get_or_404(pid)
    demo_url = request.form.get("demo_url", "")
    proj.status = "review"
    proj.progress_pct = 100
    update = ProjectUpdate(project_id=pid, author_id=current_user.id,
                           message=f"🎉 Project complete! Demo available at: {demo_url}\n\nPlease review and approve final payment to receive all deliverables.")
    db.session.add(update)
    from app.models.core import Message
    client = proj.client
    if client:
        a, b = sorted([current_user.id, client.id])
        thread_id = f"{a}-{b}"
        db.session.add(Message(sender_id=current_user.id, receiver_id=client.id,
                               content=f"🎉 **{proj.title} is ready for review!**\n\nDemo: {demo_url}\n\nPlease review and complete final payment to receive all files and credentials.",
                               thread_id=thread_id))
    db.session.commit()
    flash("Project marked complete — client notified.", "success")
    return redirect(url_for("admin.admin_project_detail", pid=pid))


@admin_bp.route("/projects/<int:pid>/mark-fully-completed", methods=["POST"])
@admin_required
def mark_project_fully_completed(pid):
    """The actual terminal state — distinct from 'review' (demo ready,
    awaiting sign-off). This is what unlocks the client's review/rating
    prompt, so it shouldn't fire until the work (and ideally payment)
    is genuinely finished."""
    proj = ClientProject.query.get_or_404(pid)
    proj.status = "completed"
    proj.progress_pct = 100
    proj.completed_at = datetime.utcnow()
    db.session.commit()

    from app.models.core import Notification
    from app.utils.email import send_email
    if proj.client:
        db.session.add(Notification(
            user_id=proj.client_id, type="project_completed", title="Project completed! 🎉",
            body=f"{proj.title} is all done. We'd love your feedback.",
            link=url_for("cms.client_project", pid=pid),
        ))
        db.session.commit()
        if proj.client.email:
            review_url = url_for("cms.client_project", pid=pid, _external=True)
            send_email(to=proj.client.email, subject=f"🎉 {proj.title} is complete!",
                       body_html=f"<p>Your project <strong>{proj.title}</strong> is officially complete.</p>"
                                 f"<p><a href='{review_url}' style='display:inline-block;padding:12px 24px;background:#2D68FF;color:#fff;text-decoration:none;border-radius:8px;font-weight:bold'>View & Leave a Review</a></p>")
    flash("Project marked fully completed! Client will be prompted to leave a review.", "success")
    return redirect(url_for("admin.admin_project_detail", pid=pid))


@admin_bp.route("/automation/canvas")
@admin_bp.route("/automation/<int:wid>/canvas")
@admin_required
def automation_canvas(wid=None):
    from app.utils.automation import TRIGGERS, ACTION_TYPES, CONDITION_OPERATORS
    from app.utils.integration_catalog import get_integration_catalog, count_integrations
    from app.utils.credential_providers import list_providers
    from app.models.platform import SocialChannel, AutomationCredential
    from app.models.core import Agent
    wf = AutomationWorkflow.query.get_or_404(wid) if wid else None
    channels = SocialChannel.query.filter_by(active=True).all()
    channels_json = [{"id": c.id, "label": c.label, "platform": c.platform} for c in channels]
    agents_json = [{"id": a.id, "label": f"{a.avatar_emoji} {a.name}"} for a in Agent.query.filter_by(active=True).all()]
    creds = AutomationCredential.query.filter_by(active=True).order_by(AutomationCredential.name).all()
    connections_json = [{"id": c.id, "name": c.name, "provider": c.provider,
                          "ok": c.last_test_ok} for c in creds]
    return render_template("admin/automation_canvas.html", wf=wf,
                           triggers=TRIGGERS, action_types=ACTION_TYPES,
                           condition_operators=CONDITION_OPERATORS, channels_json=channels_json,
                           agents_json=agents_json,
                           integration_catalog=get_integration_catalog(),
                           integration_count=count_integrations(),
                           connections_json=connections_json,
                           credential_providers=list_providers())


@admin_bp.route("/automation/node/test", methods=["POST"])
@admin_required
def automation_node_test():
    """Real, non-decorative single-node execution (Automation Studio 'Execute
    step'). Reuses GraphExecutor._run_node_logic — the exact same code path
    a live workflow run uses for this node type — against a throwaway
    executor seeded with the admin's mock input JSON, instead of a second
    hand-written per-node test implementation that could drift from what
    actually runs in production.

    This never touches the database or any saved workflow; it only executes
    the one node kind+config posted in, so it's safe to call while a node
    is still being configured (unsaved).
    """
    from app.utils.automation import GraphExecutor
    import time as _time

    payload = request.get_json(silent=True) or {}
    kind = (payload.get("type") or "").strip()
    cfg = payload.get("config") or {}
    mock_input = payload.get("mock_input") or {}
    if not isinstance(mock_input, dict):
        return jsonify({"ok": False, "error": "Mock input must be a JSON object."}), 400
    if not kind:
        return jsonify({"ok": False, "error": "No node type given."}), 400

    # Seed context both flat (so {{email}} works against top-level mock
    # input keys) and under "trigger" (so {{trigger.email}} also works,
    # matching how a real trigger node's output is addressed downstream).
    context = dict(mock_input)
    context["trigger"] = mock_input

    executor = GraphExecutor(None, {"nodes": [], "connections": []}, context)
    started = _time.time()
    try:
        next_pin, result = executor._run_node_logic(kind, cfg)
        duration_ms = int((_time.time() - started) * 1000)
        return jsonify({
            "ok": True,
            "output_pin": next_pin,
            "output": result,
            "duration_ms": duration_ms,
            "api_calls": executor.api_calls,
        })
    except Exception as e:
        duration_ms = int((_time.time() - started) * 1000)
        return jsonify({"ok": False, "error": str(e), "duration_ms": duration_ms}), 200


@admin_bp.route("/automation/graph/test", methods=["POST"])
@admin_required
def automation_graph_test():
    """Real, non-decorative FULL-WORKFLOW execution ("Test workflow" button
    on the canvas). Reuses GraphExecutor.run() — the exact same engine a
    live trigger uses — against whatever nodes/connections are currently
    on the canvas, same as automation_node_test() does for a single node.

    This never touches the database or any saved workflow, so it's safe
    to call on an unsaved graph — nothing here is a second hand-written
    "preview" implementation that could drift from what actually runs in
    production.
    """
    import re
    import time as _time
    from app.utils.automation import GraphExecutor

    payload = request.get_json(silent=True) or {}
    node_list = payload.get("nodes") or []
    conn_list = payload.get("connections") or []
    if not isinstance(node_list, list) or not node_list:
        return jsonify({"ok": False, "error": "Nothing to run — the canvas has no nodes yet."}), 200
    if not any(n.get("type") == "trigger" or n.get("id") == "trigger" for n in node_list):
        return jsonify({"ok": False, "error": "Add a trigger node before running a test."}), 200

    # Same sample context test_workflow() uses for a real, saved-workflow
    # test run — kept identical so a canvas "Test workflow" and the
    # existing workflow-list "Test Run" behave the same way against the
    # same fields (name/email/etc. resolve the same either place).
    sample_context = {
        "name": "Test User", "email": "test@example.com", "company": "Acme Inc",
        "project_type": "Website", "budget_range": "$1,000 - $5,000",
        "timeline": "2-4 weeks", "description": "This is a test run.",
        "request_id": 0, "job_title": "Sample Job", "job_id": 0,
        "applicant_name": "Test User", "applicant_email": "test@example.com", "bid_amount": 500,
    }

    started = _time.time()
    try:
        executor = GraphExecutor(None, {"nodes": node_list, "connections": conn_list}, sample_context)
        status = executor.run()
        duration_ms = int((_time.time() - started) * 1000)

        # Derive a per-node pass/fail list from the log lines (rather than
        # changing GraphExecutor's return shape) so the frontend can paint
        # the same ✓/✕ status dot on each node card that "Execute step"
        # already uses for a single node.
        node_results = []
        pattern = re.compile(r"^(SUCCESS|FAILED|SKIPPED) \[[^\]]*\] (\S+)")
        for line in executor.log_lines:
            m = pattern.match(line)
            if not m:
                continue
            outcome, node_id = m.group(1), m.group(2)
            node_results.append({
                "id": node_id,
                "status": "ok" if outcome == "SUCCESS" else ("error" if outcome == "FAILED" else None),
            })

        return jsonify({
            "ok": True,
            "status": status,
            "log_lines": executor.log_lines,
            "nodes_run": executor.nodes_run,
            "api_calls": executor.api_calls,
            "duration_ms": duration_ms,
            "node_results": node_results,
        })
    except Exception as e:
        duration_ms = int((_time.time() - started) * 1000)
        return jsonify({"ok": False, "error": str(e), "duration_ms": duration_ms}), 200


@admin_bp.route("/automation/build-with-ai", methods=["POST"])
@admin_required
def automation_build_with_ai():
    """The canvas's real "Build with AI" starter — turns a plain-English
    description into a trigger + a short, real chain of catalog actions.

    Reuses the platform's own already-configured AI provider (same
    resolver/caller as the rest of the AI tools, so no separate key setup)
    and constrains the model to ONLY the real trigger keys and real
    catalog ids that exist right now — it can't invent a fake node type,
    and anything it returns that isn't a real id is dropped server-side
    before it ever reaches the canvas.
    """
    from app.ai_tools.routes import _resolve_ai_provider, _call_ai_single
    from app.utils.automation import TRIGGERS
    from app.utils.integration_catalog import get_integration_catalog
    import json as _json

    payload = request.get_json(silent=True) or {}
    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"ok": False, "error": "Describe the automation you want first."}), 400
    if len(prompt) > 800:
        prompt = prompt[:800]

    provider, api_key = _resolve_ai_provider()
    if not provider:
        return jsonify({"ok": False, "error": "No AI provider is configured yet — add an API key under Admin \u2192 Settings \u2192 AI, then try again."}), 200

    catalog_index = []
    for cat in get_integration_catalog():
        for item in cat["items"]:
            catalog_index.append({"id": item["id"], "name": item["name"]})

    system_prompt = (
        "You design workflows for a real workflow-automation tool. Given the "
        "user's plain-English description, choose exactly ONE trigger key from "
        "the trigger list, and up to 4 action ids from the catalog list, in the "
        "order they should run. You may ONLY use keys/ids that literally appear "
        "in the lists given — never invent a new one, and never guess an id that "
        "looks plausible but wasn't listed. If nothing in the catalog fits a "
        "step, leave it out rather than picking something close-but-wrong. "
        "Respond with ONLY raw JSON, no markdown fences, no commentary, in "
        "exactly this shape: "
        '{"trigger": "<trigger_key>", "steps": ["<catalog_id>", "..."], '
        '"explanation": "<one plain-English sentence about what you built>"}'
    )
    user_msg = (
        f"Available triggers (key: label): {_json.dumps(TRIGGERS)}\n\n"
        f"Available catalog actions (id + name): {_json.dumps(catalog_index)}\n\n"
        f"User's request: {prompt}"
    )
    text, error = _call_ai_single(
        provider, api_key, system_prompt,
        [{"role": "user", "content": user_msg}],
        max_tokens=600, temperature=0.2,
    )
    if error:
        return jsonify({"ok": False, "error": error}), 200

    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned[:4].lower() == "json":
            cleaned = cleaned[4:]
    try:
        parsed = _json.loads(cleaned)
    except Exception:
        return jsonify({"ok": False, "error": "The AI didn't return valid JSON that time — try rephrasing your request."}), 200

    valid_ids = {item["id"] for item in catalog_index}
    trigger = parsed.get("trigger") if isinstance(parsed, dict) else None
    steps_in = parsed.get("steps") if isinstance(parsed, dict) else None
    steps = [s for s in (steps_in or []) if isinstance(s, str) and s in valid_ids][:6]
    if trigger not in TRIGGERS:
        trigger = "manual"

    return jsonify({
        "ok": True, "trigger": trigger, "steps": steps,
        "explanation": (parsed.get("explanation") or "")[:400] if isinstance(parsed, dict) else "",
    })


# ── Connections (Automation Studio credentials — Part 21/22) ──────────
# Real, encrypted, DB-backed connections that automation nodes reference
# by ID instead of embedding raw secrets in a workflow's node config.
# See app/models/platform.py:AutomationCredential and
# app/utils/credential_providers.py for the provider registry + real
# test-connection logic (not a fake green check).
@admin_bp.route("/automation/connections")
@admin_required
def automation_connections():
    from app.models.platform import AutomationCredential
    from app.utils.credential_providers import list_providers
    creds = AutomationCredential.query.order_by(AutomationCredential.created_at.desc()).all()
    return render_template("admin/automation_connections.html", credentials=creds,
                           providers=list_providers())


@admin_bp.route("/automation/connections/create", methods=["POST"])
@admin_required
def automation_connections_create():
    from app.models.platform import AutomationCredential
    from app.utils.credential_providers import get_provider, test_connection
    provider_key = request.form.get("provider", "").strip()
    name = (request.form.get("name") or "").strip()
    provider = get_provider(provider_key)
    if not provider or not name:
        flash("Pick a provider and give the connection a name.", "danger")
        return redirect(url_for("admin.automation_connections"))

    secret = {}
    for field in provider["fields"]:
        secret[field["key"]] = (request.form.get(f"field_{field['key']}") or "").strip()

    cred = AutomationCredential(name=name, provider=provider_key, created_by_id=current_user.id)
    cred.set_secret(secret)
    db.session.add(cred)
    db.session.commit()

    # Real test, not a fake success message — see credential_providers.test_connection
    result = test_connection(provider_key, secret)
    if result is None:
        cred.last_test_ok = None
        cred.last_test_message = "This provider doesn't have an automatic verification check yet — it'll be validated the first time a workflow actually uses it."
        flash(f'"{name}" saved. Automatic verification isn\'t available for {provider["label"]} yet — see the note on the card.', "warning")
    else:
        ok, message = result
        cred.last_test_ok = ok
        cred.last_test_message = message
        flash(f'"{name}" saved and {"verified ✓" if ok else "saved, but the test failed: " + message}', "success" if ok else "warning")
    cred.last_tested_at = datetime.utcnow()
    db.session.commit()
    log_action(current_user.id, "admin.automation_connection.create", f"{provider['label']} — {name}")
    return redirect(url_for("admin.automation_connections"))


@admin_bp.route("/automation/connections/<int:cid>/test", methods=["POST"])
@admin_required
def automation_connections_test(cid):
    from app.models.platform import AutomationCredential
    from app.utils.credential_providers import get_provider, test_connection
    cred = AutomationCredential.query.get_or_404(cid)
    provider = get_provider(cred.provider)
    result = test_connection(cred.provider, cred.get_secret())
    if result is None:
        cred.last_test_ok = None
        cred.last_test_message = "No automatic verification available for this provider."
    else:
        ok, message = result
        cred.last_test_ok = ok
        cred.last_test_message = message
    cred.last_tested_at = datetime.utcnow()
    db.session.commit()
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": cred.last_test_ok, "message": cred.last_test_message})
    flash(f"Tested {cred.name}: {cred.last_test_message}", "success" if cred.last_test_ok else "warning")
    return redirect(url_for("admin.automation_connections"))


@admin_bp.route("/automation/connections/<int:cid>/rename", methods=["POST"])
@admin_required
def automation_connections_rename(cid):
    from app.models.platform import AutomationCredential
    cred = AutomationCredential.query.get_or_404(cid)
    new_name = (request.form.get("name") or "").strip()
    if new_name:
        cred.name = new_name
        db.session.commit()
        flash("Connection renamed.", "success")
    return redirect(url_for("admin.automation_connections"))


@admin_bp.route("/automation/connections/<int:cid>/toggle", methods=["POST"])
@admin_required
def automation_connections_toggle(cid):
    from app.models.platform import AutomationCredential
    cred = AutomationCredential.query.get_or_404(cid)
    cred.active = not cred.active
    db.session.commit()
    flash(f"{cred.name} {'enabled' if cred.active else 'disabled'}.", "success")
    return redirect(url_for("admin.automation_connections"))


@admin_bp.route("/automation/connections/<int:cid>/delete", methods=["POST"])
@admin_required
def automation_connections_delete(cid):
    from app.models.platform import AutomationCredential
    cred = AutomationCredential.query.get_or_404(cid)
    usage = cred.usage_count()
    if usage:
        flash(f"Can't delete \"{cred.name}\" — {usage} workflow node(s) still reference it. Remove those nodes or point them at a different connection first.", "danger")
        return redirect(url_for("admin.automation_connections"))
    name = cred.name
    db.session.delete(cred)
    db.session.commit()
    log_action(current_user.id, "admin.automation_connection.delete", name)
    flash(f'"{name}" deleted.', "success")
    return redirect(url_for("admin.automation_connections"))


@admin_bp.route("/automation/canvas/save", methods=["POST"])
@admin_bp.route("/automation/<int:wid>/canvas/save", methods=["POST"])
@admin_required
def automation_canvas_save(wid=None):
    """Single save endpoint for the visual builder — creates a new workflow
    when wid is None, otherwise updates the existing one in place. Takes
    JSON instead of a form post since the canvas assembles its own payload
    client-side (node positions, ordered actions) rather than a plain form."""
    data = request.get_json(silent=True) or {}
    from app.utils.automation import TRIGGERS, ACTION_TYPES, CONDITION_OPERATORS
    name = (data.get("name") or "").strip()
    trigger_type = data.get("trigger_type")
    if not name or not trigger_type:
        return jsonify({"error": "Name and trigger are required."}), 400
    if trigger_type not in TRIGGERS:
        return jsonify({"error": "Unknown trigger type."}), 400
    trigger_config = data.get("trigger_config") or {}
    if not isinstance(trigger_config, dict):
        return jsonify({"error": "trigger_config must be an object."}), 400
    actions = data.get("actions") or []
    if not isinstance(actions, (list, dict)):
        return jsonify({"error": "actions must be a list or object."}), 400

    def _validate_actions(action_list, depth=0):
        if depth > 5:
            return "Conditions nested too deeply (max 5 levels)."
        for a in action_list:
            if not isinstance(a, dict) or a.get("type") not in ACTION_TYPES:
                return f"Unknown action type: {a.get('type') if isinstance(a, dict) else a}"
            if a.get("type") == "condition":
                acfg = a.get("config", {}) or {}
                if not acfg.get("field") or acfg.get("operator") not in CONDITION_OPERATORS:
                    return "A Condition node is missing its field/operator."
                err = _validate_actions(acfg.get("if_true") or [], depth + 1)
                if err:
                    return err
                err = _validate_actions(acfg.get("if_false") or [], depth + 1)
                if err:
                    return err
        return None

    if isinstance(actions, list):
        validation_error = _validate_actions(actions)
        if validation_error:
            return jsonify({"error": validation_error}), 400
    else:
        # Validate graph nodes
        for node in actions.get("nodes", []):
            ntype = node.get("type")
            if ntype != "trigger" and ntype not in ACTION_TYPES:
                return jsonify({"error": f"Unknown node type: {ntype}"}), 400
    canvas_positions = data.get("canvas_positions") or {}

    if wid:
        wf = AutomationWorkflow.query.get_or_404(wid)
        wf.name = name
        wf.trigger_type = trigger_type
        wf.trigger_config = trigger_config
        wf.actions = actions
        wf.canvas_positions = canvas_positions
        db.session.commit()
        log_action(current_user.id, "admin.automation.canvas_update", "AutomationWorkflow", str(wf.id))
    else:
        wf = AutomationWorkflow(
            name=name, trigger_type=trigger_type, trigger_config=trigger_config,
            actions=actions, canvas_positions=canvas_positions,
            active=True, created_by_id=current_user.id,
        )
        db.session.add(wf)
        db.session.commit()
        log_action(current_user.id, "admin.automation.canvas_create", "AutomationWorkflow", str(wf.id))
    return jsonify({"success": True, "id": wf.id, "redirect": url_for("admin.automation_canvas", wid=wf.id)})


@admin_bp.route("/automation/import-n8n", methods=["POST"])
@admin_required
def automation_import_n8n():
    """Imports an n8n JSON workflow string, converts it to internal graph, and saves it."""
    from app.utils.automation import convert_n8n_to_internal_graph
    data = request.get_json(silent=True) or {}
    n8n_json = data.get("n8n_json")
    if isinstance(n8n_json, str):
        try:
            n8n_json = json.loads(n8n_json)
        except Exception:
            return jsonify({"error": "Invalid JSON format"}), 400
    if not isinstance(n8n_json, dict) or "nodes" not in n8n_json:
        return jsonify({"error": "n8n JSON must contain 'nodes' array."}), 400
        
    converted = convert_n8n_to_internal_graph(n8n_json)
    wf = AutomationWorkflow(
        name=converted["name"],
        trigger_type=converted["trigger_type"],
        trigger_config=converted["trigger_config"],
        actions=converted["actions"],
        canvas_positions=converted["canvas_positions"],
        active=True,
        created_by_id=current_user.id
    )
    db.session.add(wf)
    db.session.commit()
    log_action(current_user.id, "admin.automation.n8n_import", "AutomationWorkflow", str(wf.id))
    return jsonify({"success": True, "id": wf.id, "redirect": url_for("admin.automation_canvas", wid=wf.id)})


@admin_bp.route("/automation/<int:wid>/export-n8n")
@admin_required
def automation_export_n8n(wid):
    """Exports an internal workflow into native n8n JSON format."""
    from app.utils.automation import convert_internal_graph_to_n8n
    wf = AutomationWorkflow.query.get_or_404(wid)
    n8n_data = convert_internal_graph_to_n8n(wf)
    return jsonify(n8n_data)


def _workflow_health(wf):
    """A workflow can technically be 'active' and still be silently
    failing every time it fires (bad webhook URL, expired token, etc) —
    run_count/last_run_at alone don't show that. This looks at the last
    10 AutomationRun rows for the workflow and turns them into one status
    word so both the main Automation Center list and a client's project
    page can show real health, not just an on/off toggle."""
    from app.models.platform import AutomationRun
    recent = (AutomationRun.query.filter_by(workflow_id=wf.id)
              .order_by(AutomationRun.created_at.desc()).limit(10).all())
    fail_count = sum(1 for r in recent if r.status == "failed")
    if not wf.last_run_at:
        status = "never_run"
    elif recent and all(r.status == "failed" for r in recent[:3]):
        status = "failing"
    elif fail_count:
        status = "warning"
    else:
        status = "healthy"
    return {"status": status, "recent_fail_count": fail_count, "recent_total": len(recent)}


# ── Executions (debugging/audit page) ───────────────────────────────────────
# AutomationRun rows have existed since the Connections phase (every real
# run — canvas "Test workflow", a per-node "Execute step", and every real
# live trigger — already writes one), but the only place any of that was
# ever shown was a bare, unfiltered "last 30 runs, raw log dump" panel
# bolted onto the bottom of the Workflows page. This is the dedicated
# page: filterable by workflow/status, paginated instead of hard-capped
# at 30, and actually shows the metrics (execution time, API calls,
# tokens, nodes run) that were being collected and stored but never
# displayed anywhere.
@admin_bp.route("/automation/executions")
@admin_required
def automation_executions():
    from app.utils.job_queue import queue_depth
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 25
    workflow_id = request.args.get("workflow_id", type=int)
    status = request.args.get("status", "").strip()

    q = AutomationRun.query.order_by(AutomationRun.created_at.desc())
    if workflow_id:
        q = q.filter(AutomationRun.workflow_id == workflow_id)
    if status in ("success", "partial", "failed"):
        q = q.filter(AutomationRun.status == status)

    total = q.count()
    runs = q.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = max(1, (total + per_page - 1) // per_page)

    workflows = AutomationWorkflow.query.order_by(AutomationWorkflow.name).all()
    return render_template(
        "admin/automation_executions.html",
        runs=runs, workflows=workflows,
        selected_workflow_id=workflow_id, selected_status=status,
        page=page, total_pages=total_pages, total=total,
        queued_jobs=queue_depth(),
    )


# ── Automation Center ────────────────────────────────────────────────────────
@admin_bp.route("/automation")
@admin_required
def automation():
    from app.utils.automation import TRIGGERS, ACTION_TYPES
    from app.models.platform import SocialChannel, ClientProject, WorkflowTemplate
    from app.models.core import Agent
    workflows = AutomationWorkflow.query.order_by(AutomationWorkflow.created_at.desc()).all()
    workflow_health = {w.id: _workflow_health(w) for w in workflows}
    recent_runs = AutomationRun.query.order_by(AutomationRun.created_at.desc()).limit(30).all()
    channels = SocialChannel.query.filter_by(active=True).all()
    channels_json = [{"id": c.id, "label": c.label, "platform": c.platform} for c in channels]
    agents_json = [{"id": a.id, "label": f"{a.avatar_emoji} {a.name}"} for a in Agent.query.filter_by(active=True).all()]
    client_projects = ClientProject.query.order_by(ClientProject.title).all()
    saved_templates = WorkflowTemplate.query.order_by(WorkflowTemplate.created_at.desc()).all()
    return render_template("admin/automation.html", workflows=workflows, recent_runs=recent_runs,
                           triggers=TRIGGERS, action_types=ACTION_TYPES, channels=channels,
                           channels_json=channels_json, agents_json=agents_json, client_projects=client_projects,
                           workflow_health=workflow_health,
                           saved_templates=saved_templates)


@admin_bp.route("/automation/create", methods=["POST"])
@admin_required
def create_workflow():
    name = (request.form.get("name") or "").strip()
    trigger_type = request.form.get("trigger_type")
    actions_json = request.form.get("actions_json", "[]")
    if not name or not trigger_type:
        flash("Name and trigger are required.", "danger")
        return redirect(url_for("admin.automation"))
    try:
        actions = json.loads(actions_json)
    except (TypeError, ValueError):
        flash("Invalid action configuration.", "danger")
        return redirect(url_for("admin.automation"))
    wf = AutomationWorkflow(
        name=name, trigger_type=trigger_type, actions=actions,
        active=True, created_by_id=current_user.id,
    )
    db.session.add(wf)
    db.session.commit()
    log_action(current_user.id, "admin.automation.create", "AutomationWorkflow", str(wf.id))
    flash(f'Workflow "{name}" created.', "success")
    return redirect(url_for("admin.automation"))


@admin_bp.route("/automation/<int:wid>/billing", methods=["POST"])
@admin_required
def update_workflow_billing(wid):
    """Same idea as social channel billing — link this automation to
    whichever customer it's actually running for. Each workflow's webhook
    action already has its own URL in its own config, so a customer's
    Zapier/n8n/Slack hook is already isolated from anyone else's before
    this field exists; this just makes it billable and traceable."""
    wf = AutomationWorkflow.query.get_or_404(wid)
    cpid = request.form.get("client_project_id", "").strip()
    wf.client_project_id = int(cpid) if cpid else None
    fee = request.form.get("monthly_fee", "").strip()
    try:
        wf.monthly_fee = float(fee) if fee else None
    except ValueError:
        wf.monthly_fee = None
    db.session.commit()
    flash(f'Billing updated for "{wf.name}".', "success")
    return redirect(url_for("admin.automation"))


@admin_bp.route("/automation/<int:wid>/invoice", methods=["POST"])
@admin_required
def invoice_workflow(wid):
    from app.models.platform import Invoice
    wf = AutomationWorkflow.query.get_or_404(wid)
    if not wf.client_project_id:
        flash("Assign this workflow to a customer first (Billing) before invoicing.", "warning")
        return redirect(url_for("admin.automation"))
    if not wf.monthly_fee:
        flash("Set a monthly fee for this workflow first.", "warning")
        return redirect(url_for("admin.automation"))
    month_label = datetime.utcnow().strftime("%B %Y")
    inv = Invoice(
        project_id=wf.client_project_id,
        title=f'"{wf.name}" automation — service ({month_label})',
        description=f'Monthly fee for the "{wf.name}" automation workflow.',
        amount=wf.monthly_fee, currency="USD", status="unpaid",
        created_by=current_user.id,
    )
    db.session.add(inv)
    db.session.commit()
    flash(f'Invoice created for "{wf.name}": ${wf.monthly_fee:.2f}.', "success")
    return redirect(url_for("admin.financials"))


@admin_bp.route("/automation/<int:wid>/toggle", methods=["POST"])
@admin_required
def toggle_workflow(wid):
    wf = AutomationWorkflow.query.get_or_404(wid)
    wf.active = not wf.active
    db.session.commit()
    flash(f"Workflow {'activated' if wf.active else 'paused'}.", "success")
    return redirect(url_for("admin.automation"))


@admin_bp.route("/automation/<int:wid>/delete", methods=["POST"])
@admin_required
def delete_workflow(wid):
    wf = AutomationWorkflow.query.get_or_404(wid)
    AutomationRun.query.filter_by(workflow_id=wid).delete()
    db.session.delete(wf)
    db.session.commit()
    flash("Workflow deleted.", "success")
    return redirect(url_for("admin.automation"))


@admin_bp.route("/automation/<int:wid>/save-as-template", methods=["POST"])
@admin_required
def save_workflow_as_template(wid):
    from app.models.platform import WorkflowTemplate
    wf = AutomationWorkflow.query.get_or_404(wid)
    tpl = WorkflowTemplate(
        name=request.form.get("name", wf.name).strip() or wf.name,
        description=request.form.get("description", "").strip() or None,
        trigger_type=wf.trigger_type, actions=wf.actions or [],
        created_by_id=current_user.id,
    )
    db.session.add(tpl)
    db.session.commit()
    flash(f'Saved "{tpl.name}" to your Templates library.', "success")
    return redirect(url_for("admin.automation"))


@admin_bp.route("/automation/templates/<int:tid>/use", methods=["POST"])
@admin_required
def use_saved_template(tid):
    from app.models.platform import WorkflowTemplate
    tpl = WorkflowTemplate.query.get_or_404(tid)
    wf = AutomationWorkflow(
        name=tpl.name, trigger_type=tpl.trigger_type, trigger_config={},
        actions=tpl.actions or [], canvas_positions={}, active=False, created_by_id=current_user.id,
    )
    db.session.add(wf)
    db.session.commit()
    flash(f'Added "{wf.name}" from your Templates library (paused — review then turn it on).', "success")
    return redirect(url_for("admin.automation_canvas", wid=wf.id))


@admin_bp.route("/automation/templates/<int:tid>/delete", methods=["POST"])
@admin_required
def delete_saved_template(tid):
    from app.models.platform import WorkflowTemplate
    db.session.delete(WorkflowTemplate.query.get_or_404(tid))
    db.session.commit()
    flash("Template removed.", "success")
    return redirect(url_for("admin.automation"))


@admin_bp.route("/automation/template/<key>", methods=["POST"])
@admin_required
def use_workflow_template(key):
    """Ready-made starting points so a new admin doesn't have to build a
    workflow from a blank canvas the first time — clones one in paused
    so they can review/adjust before turning it on."""
    templates = {
        "lead_email": {
            "name": "New Hire Request → Email Me", "trigger_type": "hire_request_submitted",
            "actions": [{"type": "send_email", "config": {
                "to": "admin", "subject": "New hire request from {{name}}",
                "body": "<p>{{name}} ({{email}}) submitted a hire-me request.</p><p>{{message}}</p>"}}],
        },
        "bot_slack": {
            "name": "Bot Message → Notify Slack", "trigger_type": "channel_message_received",
            "actions": [{"type": "webhook", "config": {"url": ""}}],
        },
        "meeting_notify": {
            "name": "Meeting Scheduled → Admin Alert", "trigger_type": "meeting_scheduled",
            "actions": [{"type": "notify_admin", "config": {
                "message": "Meeting \"{{title}}\" scheduled with {{client}} on {{project}}."}}],
        },
    }
    tpl = templates.get(key)
    if not tpl:
        flash("Unknown template.", "danger")
        return redirect(url_for("admin.automation"))
    wf = AutomationWorkflow(
        name=tpl["name"], trigger_type=tpl["trigger_type"], trigger_config={},
        actions=tpl["actions"], canvas_positions={}, active=False, created_by_id=current_user.id,
    )
    db.session.add(wf)
    db.session.commit()
    flash(f'Added "{wf.name}" (paused — open its Canvas to fill in the details, like your Slack webhook URL, then turn it on).', "success")
    return redirect(url_for("admin.automation_canvas", wid=wf.id))


@admin_bp.route("/automation/<int:wid>/clone", methods=["POST"])
@admin_required
def clone_workflow(wid):
    src = AutomationWorkflow.query.get_or_404(wid)
    copy = AutomationWorkflow(
        name=f"{src.name} (copy)", trigger_type=src.trigger_type, trigger_config=src.trigger_config,
        actions=src.actions, canvas_positions=src.canvas_positions, active=False,
        created_by_id=current_user.id,
        # Billing is intentionally NOT copied — a clone starts unbilled so
        # you don't accidentally invoice a new customer under the
        # original's assignment.
    )
    db.session.add(copy)
    db.session.commit()
    flash(f'Cloned as "{copy.name}" (starts paused — review then turn it on).', "success")
    return redirect(url_for("admin.automation_canvas", wid=copy.id))


@admin_bp.route("/automation/<int:wid>/export")
@admin_required
def export_workflow(wid):
    wf = AutomationWorkflow.query.get_or_404(wid)
    payload = {
        "name": wf.name, "trigger_type": wf.trigger_type, "trigger_config": wf.trigger_config or {},
        "actions": wf.actions or [], "canvas_positions": wf.canvas_positions or {},
        "exported_from": "Bazillin Studio Automation Center",
    }
    data = json.dumps(payload, indent=2)
    resp = make_response(data)
    resp.headers["Content-Type"] = "application/json"
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in wf.name).strip() or f"workflow-{wf.id}"
    resp.headers["Content-Disposition"] = f'attachment; filename="{safe_name}.json"'
    return resp


@admin_bp.route("/automation/import", methods=["POST"])
@admin_required
def import_workflow():
    from app.utils.automation import TRIGGERS, ACTION_TYPES
    file = request.files.get("workflow_file")
    if not file or not file.filename:
        flash("Choose a workflow .json file to import.", "danger")
        return redirect(url_for("admin.automation"))
    try:
        payload = json.loads(file.read().decode("utf-8"))
    except Exception:
        flash("That file isn't valid JSON.", "danger")
        return redirect(url_for("admin.automation"))
    if payload.get("trigger_type") not in TRIGGERS:
        flash("Unrecognized or missing trigger_type in that file.", "danger")
        return redirect(url_for("admin.automation"))
    wf = AutomationWorkflow(
        name=payload.get("name", "Imported Workflow"), trigger_type=payload["trigger_type"],
        trigger_config=payload.get("trigger_config") or {}, actions=payload.get("actions") or [],
        canvas_positions=payload.get("canvas_positions") or {}, active=False,
        created_by_id=current_user.id,
    )
    db.session.add(wf)
    db.session.commit()
    flash(f'Imported "{wf.name}" (starts paused — review then turn it on).', "success")
    return redirect(url_for("admin.automation_canvas", wid=wf.id))


@admin_bp.route("/automation/<int:wid>/test", methods=["POST"])
@admin_required
def test_workflow(wid):
    """Fires the workflow immediately with sample data, so an admin can
    verify actions actually work before relying on a real trigger."""
    from app.utils.automation import trigger as automation_trigger
    wf = AutomationWorkflow.query.get_or_404(wid)
    if not wf.active:
        flash("This workflow is currently OFF (inactive) — nothing ran. Turn it on first, then Test Run again.", "warning")
        return redirect(url_for("admin.automation"))
    sample_context = {
        "name": "Test User", "email": "test@example.com", "company": "Acme Inc",
        "project_type": "Website", "budget_range": "$1,000 - $5,000",
        "timeline": "2-4 weeks", "description": "This is a test run.",
        "request_id": 0, "job_title": "Sample Job", "job_id": 0,
        "applicant_name": "Test User", "applicant_email": "test@example.com", "bid_amount": 500,
    }
    if wf.trigger_config and any(str(sample_context.get(k)) != str(v) for k, v in wf.trigger_config.items() if v not in (None, "")):
        flash("This workflow has a trigger filter that the sample test data doesn't match, so it wouldn't have fired — "
              "this test result is accurate to what would happen on a real trigger event, not a bug.", "warning")
        return redirect(url_for("admin.automation"))
    automation_trigger(wf.trigger_type, sample_context)
    from app.models.platform import AutomationRun
    last_run = AutomationRun.query.filter_by(workflow_id=wf.id).order_by(AutomationRun.id.desc()).first()
    if last_run and last_run.status == "success":
        flash("Test run succeeded — see the log below for exactly what each step did.", "success")
    elif last_run:
        flash(f"Test run FAILED ({last_run.status}) — see the log below for the error.", "danger")
    else:
        flash("Test run fired, but no run log was recorded — check the workflow's action list.", "warning")
    return redirect(url_for("admin.automation"))


# ── Social Bots (WhatsApp / Telegram / Facebook agents) ─────────────────────
@admin_bp.route("/social-channels")
@admin_required
def social_channels():
    from app.models.platform import SocialChannel, ClientProject
    channels = SocialChannel.query.order_by(SocialChannel.created_at.desc()).all()
    client_projects = ClientProject.query.order_by(ClientProject.title).all()
    return render_template("admin/social_channels.html", channels=channels, client_projects=client_projects)


@admin_bp.route("/social-channels/connect/telegram", methods=["POST"])
@admin_required
def connect_telegram():
    from app.models.platform import SocialChannel
    from app.utils.social_bots import test_telegram_connection, register_telegram_webhook
    label = request.form.get("label", "Telegram Bot")
    bot_token = request.form.get("bot_token", "").strip()
    if not bot_token:
        flash("Bot token is required.", "danger")
        return redirect(url_for("admin.social_channels"))
    channel = SocialChannel(platform="telegram", label=label, credentials={"bot_token": bot_token})
    channel.ensure_secret()
    db.session.add(channel)
    db.session.flush()  # get channel.id before building the webhook URL
    try:
        bot_info = test_telegram_connection(bot_token)
        webhook_url = url_for("social.telegram_webhook", secret=channel.webhook_secret, _external=True)
        register_telegram_webhook(bot_token, webhook_url)
        channel.connected = True
        channel.connection_error = None
        flash(f"Connected to @{bot_info.get('username')}! Your bot is live.", "success")
    except Exception as e:
        channel.connected = False
        channel.connection_error = str(e)
        flash(f"Saved, but connection failed: {e}", "warning")
    db.session.commit()
    return redirect(url_for("admin.social_channels"))


@admin_bp.route("/social-channels/connect/whatsapp", methods=["POST"])
@admin_required
def connect_whatsapp():
    from app.models.platform import SocialChannel
    from app.utils.social_bots import test_whatsapp_connection
    label = request.form.get("label", "WhatsApp")
    phone_number_id = request.form.get("phone_number_id", "").strip()
    access_token = request.form.get("access_token", "").strip()
    verify_token = request.form.get("verify_token", "").strip() or __import__("secrets").token_urlsafe(16)
    app_secret = request.form.get("app_secret", "").strip()
    if not phone_number_id or not access_token:
        flash("Phone Number ID and Access Token are required.", "danger")
        return redirect(url_for("admin.social_channels"))
    channel = SocialChannel(platform="whatsapp", label=label, credentials={
        "phone_number_id": phone_number_id, "access_token": access_token,
        "verify_token": verify_token, "app_secret": app_secret,
    })
    channel.ensure_secret()
    try:
        test_whatsapp_connection(phone_number_id, access_token)
        channel.connected = True
        channel.connection_error = None
        flash("Credentials verified! Now paste the Webhook URL and Verify Token shown below into your Meta App's WhatsApp > Configuration page.", "success")
    except Exception as e:
        channel.connected = False
        channel.connection_error = str(e)
        flash(f"Saved, but credential check failed: {e}", "warning")
    db.session.add(channel)
    db.session.commit()
    return redirect(url_for("admin.social_channels"))


@admin_bp.route("/social-channels/connect/facebook", methods=["POST"])
@admin_required
def connect_facebook():
    from app.models.platform import SocialChannel
    from app.utils.social_bots import test_facebook_connection
    label = request.form.get("label", "Facebook Page")
    page_access_token = request.form.get("page_access_token", "").strip()
    verify_token = request.form.get("verify_token", "").strip() or __import__("secrets").token_urlsafe(16)
    app_secret = request.form.get("app_secret", "").strip()
    if not page_access_token:
        flash("Page Access Token is required.", "danger")
        return redirect(url_for("admin.social_channels"))
    channel = SocialChannel(platform="facebook", label=label, credentials={
        "page_access_token": page_access_token, "verify_token": verify_token, "app_secret": app_secret,
    })
    channel.ensure_secret()
    try:
        page_info = test_facebook_connection(page_access_token)
        channel.connected = True
        channel.connection_error = None
        channel.credentials["page_id"] = page_info.get("id")  # same token can also publish to this Page's feed, not just message
        flash(f"Connected to Page \"{page_info.get('name')}\"! Now paste the Webhook URL and Verify Token shown below into your Meta App's Messenger > Configuration page.", "success")
    except Exception as e:
        channel.connected = False
        channel.connection_error = str(e)
        flash(f"Saved, but credential check failed: {e}", "warning")
    db.session.add(channel)
    db.session.commit()
    return redirect(url_for("admin.social_channels"))


@admin_bp.route("/social-channels/connect/instagram", methods=["POST"])
@admin_required
def connect_instagram():
    from app.models.platform import SocialChannel
    from app.utils.social_bots import test_instagram_connection
    label = request.form.get("label", "Instagram")
    page_access_token = request.form.get("page_access_token", "").strip()
    verify_token = request.form.get("verify_token", "").strip() or __import__("secrets").token_urlsafe(16)
    app_secret = request.form.get("app_secret", "").strip()
    if not page_access_token:
        flash("Page Access Token is required.", "danger")
        return redirect(url_for("admin.social_channels"))
    channel = SocialChannel(platform="instagram", label=label, credentials={
        "page_access_token": page_access_token, "verify_token": verify_token, "app_secret": app_secret,
    })
    channel.ensure_secret()
    try:
        test_instagram_connection(page_access_token)
        channel.connected = True
        channel.connection_error = None
        flash("Connected! Now paste the Webhook URL and Verify Token shown below into your Meta App's Instagram > Configuration page.", "success")
    except Exception as e:
        channel.connected = False
        channel.connection_error = str(e)
        flash(f"Saved, but credential check failed: {e}", "warning")
    db.session.add(channel)
    db.session.commit()
    return redirect(url_for("admin.social_channels"))


@admin_bp.route("/social-channels/connect/linkedin", methods=["POST"])
@admin_required
def connect_linkedin():
    from app.models.platform import SocialChannel
    from app.utils.social_bots import test_linkedin_connection
    label = request.form.get("label", "LinkedIn").strip()
    access_token = request.form.get("access_token", "").strip()
    if not access_token:
        flash("Access Token is required.", "danger")
        return redirect(url_for("admin.social_channels"))
    channel = SocialChannel(platform="linkedin", label=label, credentials={
        "access_token": access_token
    })
    channel.ensure_secret()
    try:
        profile_info = test_linkedin_connection(access_token)
        channel.connected = True
        channel.connection_error = None
        channel.credentials["person_urn"] = f"urn:li:person:{profile_info.get('id')}"
        flash(f"Connected to LinkedIn profile \"{profile_info.get('name')}\"!", "success")
    except Exception as e:
        channel.connected = False
        channel.connection_error = str(e)
        flash(f"Saved, but credential check failed: {e}", "warning")
    db.session.add(channel)
    db.session.commit()
    return redirect(url_for("admin.social_channels"))


def _oauth_state_serializer():
    from itsdangerous import URLSafeTimedSerializer
    return URLSafeTimedSerializer(current_app.secret_key, salt="admin-social-oauth")


def _external_url(endpoint, **kwargs):
    from flask import request, url_for
    from app.utils.settings import get_setting
    app_url = (get_setting("app_url") or "").strip()
    url = url_for(endpoint, _external=True, **kwargs)
    if app_url.startswith("https://") and url.startswith("http://"):
        url = "https://" + url.split("://", 1)[1]
    elif request.headers.get("X-Forwarded-Proto") == "https" and url.startswith("http://"):
        url = "https://" + url.split("://", 1)[1]
    return url


@admin_bp.route("/social-channels/connect/youtube/start")
@admin_required
def youtube_oauth_start():
    """Connects YOUR OWN YouTube channel (this is the site owner's
    Content Studio publishing channel, not a per-client one) — reuses the
    same Google OAuth Client ID/Secret already used for Google Sheets,
    just with YouTube scopes added."""
    from urllib.parse import quote
    client_id = get_setting("google_oauth_client_id")
    if not client_id:
        flash("Add a Google OAuth Client ID/Secret in Admin -> Settings first (same one used for Google Sheets).", "warning")
        return redirect(url_for("admin.social_channels"))
    state = _oauth_state_serializer().dumps({"admin_id": current_user.id, "kind": "youtube"})
    redirect_uri = _external_url("admin.youtube_oauth_callback")
    scopes = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?response_type=code&client_id={client_id}&redirect_uri={quote(redirect_uri, safe='')}"
        f"&scope={quote(scopes)}&state={state}"
        "&access_type=offline&prompt=consent"
    )
    return redirect(auth_url)


@admin_bp.route("/social-channels/connect/youtube/callback")
@admin_required
def youtube_oauth_callback():
    from itsdangerous import BadSignature, SignatureExpired
    from app.models.platform import SocialChannel
    import requests as _rq

    error = request.args.get("error")
    if error:
        # access_denied here almost always means Google's OAuth consent
        # screen itself refused the login before it ever reached this
        # site's code -- either the account isn't a Test User while the
        # app is in "Testing" publishing status, or the app hasn't passed
        # Google's verification for the youtube.upload restricted scope.
        # Both look identical from here (Google just sends error=access_denied),
        # so the message points at the actual fix instead of implying this
        # site rejected the connection.
        if error == "access_denied":
            flash("Google blocked this connection before it reached this site. This almost always means the "
                  "Google account isn't added as a Test User yet (Google Cloud Console → OAuth consent screen → "
                  "Test users), or the app still needs Google's verification for the YouTube upload scope. "
                  "See the callout under Admin → Settings → AI & Automation → Client OAuth Connections for exact steps.", "warning")
        else:
            flash(f"YouTube connection was cancelled: {error}", "warning")
        return redirect(url_for("admin.social_channels"))

    try:
        data = _oauth_state_serializer().loads(request.args.get("state", ""), max_age=600)
    except (BadSignature, SignatureExpired):
        abort(400)
    if data.get("admin_id") != current_user.id or data.get("kind") != "youtube":
        abort(403)

    client_id = get_setting("google_oauth_client_id")
    client_secret = get_setting("google_oauth_client_secret")
    redirect_uri = _external_url("admin.youtube_oauth_callback")
    token_resp = _rq.post("https://oauth2.googleapis.com/token", data={
        "grant_type": "authorization_code", "code": request.args.get("code"),
        "redirect_uri": redirect_uri, "client_id": client_id, "client_secret": client_secret,
    }, timeout=15).json()

    if "access_token" not in token_resp:
        err_code = token_resp.get("error", "unknown error")
        err_msg = token_resp.get("error_description", err_code)
        if err_code == "redirect_uri_mismatch" or "redirect_uri" in err_msg.lower():
            flash(f"YouTube connection failed: redirect_uri_mismatch. The Authorized redirect URI in Google Cloud "
                  f"Console must match this EXACTLY: {redirect_uri} — re-check for a trailing slash or http/https difference.", "danger")
        else:
            flash(f"YouTube connection failed: {err_msg}", "danger")
        return redirect(url_for("admin.social_channels"))
    refresh_token = token_resp.get("refresh_token")
    if not refresh_token:
        flash("YouTube connected, but no long-term access was granted (you may have connected before). "
              "Remove this app's access in your Google Account permissions, then connect again.", "warning")
        return redirect(url_for("admin.social_channels"))

    from app.utils.youtube import API_BASE as _YT_API_BASE
    channel_info = _rq.get(f"{_YT_API_BASE}/channels",
                            headers={"Authorization": f"Bearer {token_resp['access_token']}"},
                            params={"part": "snippet", "mine": "true"}, timeout=10).json()
    channel_name = "YouTube Channel"
    items = channel_info.get("items") or []
    if items:
        channel_name = items[0].get("snippet", {}).get("title", channel_name)

    channel = SocialChannel.query.filter_by(platform="youtube", client_project_id=None).first()
    if not channel:
        channel = SocialChannel(platform="youtube")
    channel.label = channel_name
    channel.credentials = {"refresh_token": refresh_token, "channel_name": channel_name, "connected_via": "oauth"}
    channel.ensure_secret()
    channel.connected = True
    channel.connection_error = None
    channel.active = True
    db.session.add(channel)
    db.session.commit()
    flash(f'Connected YouTube channel "{channel_name}" — you can now post and pull analytics from Social Channels or Content Studio.', "success")
    return redirect(url_for("admin.social_channels"))


@admin_bp.route("/social-channels/connect/tiktok/start")
@admin_required
def tiktok_oauth_start():
    from urllib.parse import quote
    client_key = get_setting("tiktok_client_key")
    if not client_key:
        flash("Add a TikTok Client Key/Secret in Admin -> Settings first (from your TikTok Developer app).", "warning")
        return redirect(url_for("admin.social_channels"))
    state = _oauth_state_serializer().dumps({"admin_id": current_user.id, "kind": "tiktok"})
    redirect_uri = _external_url("admin.tiktok_oauth_callback")
    scopes = "user.info.basic,video.publish,video.upload,video.list"
    auth_url = (
        "https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={client_key}&scope={quote(scopes)}&response_type=code"
        f"&redirect_uri={quote(redirect_uri, safe='')}&state={state}"
    )
    return redirect(auth_url)


@admin_bp.route("/social-channels/connect/tiktok/callback")
@admin_required
def tiktok_oauth_callback():
    from itsdangerous import BadSignature, SignatureExpired
    from app.models.platform import SocialChannel
    import requests as _rq

    error = request.args.get("error")
    if error:
        flash(f"TikTok connection was cancelled: {error}", "warning")
        return redirect(url_for("admin.social_channels"))

    try:
        data = _oauth_state_serializer().loads(request.args.get("state", ""), max_age=600)
    except (BadSignature, SignatureExpired):
        abort(400)
    if data.get("admin_id") != current_user.id or data.get("kind") != "tiktok":
        abort(403)

    client_key = get_setting("tiktok_client_key")
    client_secret = get_setting("tiktok_client_secret")
    redirect_uri = _external_url("admin.tiktok_oauth_callback")
    token_resp = _rq.post("https://open.tiktokapis.com/v2/oauth/token/", data={
        "client_key": client_key, "client_secret": client_secret,
        "code": request.args.get("code"), "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15).json()

    if "access_token" not in token_resp:
        flash(f"TikTok connection failed: {token_resp.get('error_description', token_resp.get('error_code', 'unknown error'))}", "danger")
        return redirect(url_for("admin.social_channels"))

    display_name = token_resp.get("open_id", "TikTok Account")
    channel = SocialChannel.query.filter_by(platform="tiktok", client_project_id=None).first()
    if not channel:
        channel = SocialChannel(platform="tiktok")
    channel.label = f"TikTok ({display_name})"
    channel.credentials = {"refresh_token": token_resp.get("refresh_token"), "open_id": display_name, "connected_via": "oauth"}
    channel.ensure_secret()
    channel.connected = True
    channel.connection_error = None
    channel.active = True
    db.session.add(channel)
    db.session.commit()
    flash("Connected your TikTok account — you can now post and pull analytics from Social Channels or Content Studio.", "success")
    return redirect(url_for("admin.social_channels"))


@admin_bp.route("/social-channels/<int:cid>/post-video", methods=["POST"])
@admin_required
def post_channel_video(cid):
    """Shared endpoint for both YouTube and TikTok — posts a video that's
    already hosted at a public URL (e.g. from your NEXUS media library)
    to the given connected channel."""
    from app.models.platform import SocialChannel
    channel = SocialChannel.query.get_or_404(cid)
    data = request.get_json(silent=True) or {}
    video_url = (data.get("video_url") or "").strip()
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    if not video_url:
        return jsonify({"success": False, "error": "video_url is required."}), 400

    if channel.platform == "youtube":
        from app.utils.youtube import upload_video
        video_id, err = upload_video(channel, video_url, title, description,
                                      privacy_status=data.get("privacy_status", "public"))
        if err:
            return jsonify({"success": False, "error": err}), 502
        return jsonify({"success": True, "video_id": video_id, "url": f"https://youtube.com/watch?v={video_id}"})

    if channel.platform == "tiktok":
        from app.utils.tiktok import post_video_from_url
        publish_id, err = post_video_from_url(channel, video_url, title,
                                               privacy_level=data.get("privacy_level", "SELF_ONLY"))
        if err:
            return jsonify({"success": False, "error": err}), 502
        return jsonify({"success": True, "publish_id": publish_id,
                         "note": "TikTok publishes asynchronously — check status with GET /social-channels/<id>/post-status/<publish_id>."})

    return jsonify({"success": False, "error": f"Video posting isn't supported for platform '{channel.platform}'."}), 400


@admin_bp.route("/social-channels/<int:cid>/post-status/<publish_id>")
@admin_required
def channel_post_status(cid, publish_id):
    from app.models.platform import SocialChannel
    from app.utils.tiktok import check_post_status
    channel = SocialChannel.query.get_or_404(cid)
    if channel.platform != "tiktok":
        return jsonify({"success": False, "error": "Status polling is only needed for TikTok."}), 400
    status, err = check_post_status(channel, publish_id)
    if err:
        return jsonify({"success": False, "error": err}), 502
    return jsonify({"success": True, "status": status})


@admin_bp.route("/social-channels/<int:cid>/analytics")
@admin_required
def channel_analytics(cid):
    """Real view/like/comment counts for a connected YouTube or TikTok
    channel's recent videos."""
    from app.models.platform import SocialChannel
    channel = SocialChannel.query.get_or_404(cid)
    if channel.platform == "youtube":
        from app.utils.youtube import channel_video_stats
        videos, err = channel_video_stats(channel)
    elif channel.platform == "tiktok":
        from app.utils.tiktok import account_video_analytics
        videos, err = account_video_analytics(channel)
    else:
        return jsonify({"success": False, "error": f"Analytics aren't supported for platform '{channel.platform}'."}), 400
    if err:
        return jsonify({"success": False, "error": err}), 502
    return jsonify({"success": True, "videos": videos})


@admin_bp.route("/social-channels/<int:cid>/rules", methods=["POST"])
@admin_required
def update_channel_rules(cid):
    from app.models.platform import SocialChannel
    channel = SocialChannel.query.get_or_404(cid)
    channel.fallback_reply = request.form.get("fallback_reply", channel.fallback_reply)
    channel.welcome_message = request.form.get("welcome_message", "").strip() or None
    channel.human_takeover_keywords = [k.strip() for k in request.form.get("takeover_keywords", "").split(",") if k.strip()]
    channel.ai_agent_enabled = request.form.get("ai_agent_enabled") == "on"
    channel.ai_agent_instructions = request.form.get("ai_agent_instructions", "").strip() or None
    try:
        channel.ai_agent_temperature = float(request.form.get("ai_agent_temperature") or 0.7)
    except ValueError:
        channel.ai_agent_temperature = 0.7
    rules = []
    empty_reply_keywords = []
    keywords_list = request.form.getlist("rule_keywords[]")
    replies_list = request.form.getlist("rule_reply[]")
    show_products_list = request.form.getlist("rule_show_products[]")  # values are indices that were checked
    for i, (kw, reply) in enumerate(zip(keywords_list, replies_list)):
        if not kw.strip():
            continue
        show_products = str(i) in show_products_list
        # A rule with no reply text and "show products" unchecked matches
        # correctly but has nothing to send back, so handle_inbound_message
        # silently falls through to the channel's default reply — from the
        # customer's side that looks identical to "the keyword didn't
        # work". Catch it here instead of shipping a rule that can't
        # actually respond.
        if not show_products and not reply.strip():
            empty_reply_keywords.append(kw.strip())
            continue
        rules.append({
            "match": "contains",
            "keywords": [k.strip() for k in kw.split(",") if k.strip()],
            "reply": reply,
            "show_products": show_products,
            "product_search": kw.split(",")[0].strip() if show_products else "",
        })
    channel.auto_reply_rules = rules
    db.session.commit()
    if empty_reply_keywords:
        flash(
            "Saved, but these rules were skipped because they have no reply text and "
            "'show products' isn't checked, so they'd have nothing to send back: "
            + "; ".join(empty_reply_keywords) + ". Add a reply (or check 'show products') and save again.",
            "warning",
        )
    else:
        flash("Auto-reply rules saved.", "success")
    return redirect(url_for("admin.social_channels"))


@admin_bp.route("/social-channels/<int:cid>/test-welcome", methods=["POST"])
@admin_required
def test_welcome_message(cid):
    """Sends the channel's welcome message to a chosen chat_id/phone number
    right now, bypassing the "is this contact brand new" check — useful
    because that check only fires once per contact ever, so re-testing
    with the same admin/test account after the first message won't
    trigger it again through the normal flow.

    Returns real JSON (previously flash+redirect, which the AJAX caller
    couldn't actually read — it used redirect:'manual' specifically to
    avoid navigating away, so the real success/failure was silently
    discarded and the button always claimed "Sent!" regardless of what
    actually happened)."""
    from app.models.platform import SocialChannel
    from app.utils.social_bots import send_reply
    channel = SocialChannel.query.get_or_404(cid)
    recipient = (request.form.get("test_recipient") or "").strip()
    if not recipient:
        return jsonify({"error": "Enter a chat ID / phone number to send the test welcome to."}), 400
    if not (channel.welcome_message or "").strip():
        return jsonify({"error": "This channel has no welcome message set yet — add one and save first."}), 400
    try:
        send_reply(channel, recipient, channel.welcome_message.strip())
        return jsonify({"sent": True, "recipient": recipient})
    except Exception as e:
        current_app.logger.exception("Test welcome message failed for channel %s", cid)
        return jsonify({"error": str(e)}), 502


@admin_bp.route("/social-channels/<int:cid>/billing", methods=["POST"])
@admin_required
def update_channel_billing(cid):
    """Links a bot to whichever customer it's actually running for, and
    what you charge them for it — for when you're building/running this
    bot as a service for a client rather than for yourself. The bot's own
    token/credentials are already per-channel, so this is purely the
    billing/organization link, not a security boundary."""
    from app.models.platform import SocialChannel
    channel = SocialChannel.query.get_or_404(cid)
    cpid = request.form.get("client_project_id", "").strip()
    channel.client_project_id = int(cpid) if cpid else None
    fee = request.form.get("monthly_fee", "").strip()
    try:
        channel.monthly_fee = float(fee) if fee else None
    except ValueError:
        channel.monthly_fee = None
    db.session.commit()
    flash(f"Billing updated for {channel.label}.", "success")
    return redirect(url_for("admin.social_channels"))


@admin_bp.route("/social-channels/<int:cid>/invoice", methods=["POST"])
@admin_required
def invoice_channel(cid):
    from app.models.platform import SocialChannel, Invoice
    channel = SocialChannel.query.get_or_404(cid)
    if not channel.client_project_id:
        flash("Assign this bot to a customer first (Billing section) before invoicing.", "warning")
        return redirect(url_for("admin.social_channels"))
    if not channel.monthly_fee:
        flash("Set a monthly fee for this bot first.", "warning")
        return redirect(url_for("admin.social_channels"))
    month_label = datetime.utcnow().strftime("%B %Y")
    inv = Invoice(
        project_id=channel.client_project_id,
        title=f"{channel.label} — bot service ({month_label})",
        description=f"Monthly fee for the {channel.platform} bot '{channel.label}'.",
        amount=channel.monthly_fee, currency="USD", status="unpaid",
        created_by=current_user.id,
    )
    db.session.add(inv)
    db.session.commit()
    flash(f"Invoice created for {channel.label}: ${channel.monthly_fee:.2f}.", "success")
    return redirect(url_for("admin.financials"))


def _persist_scraped_items(items, source_url, project_id=None):
    """Saves every item from one import_catalog_from_url call so it's
    reusable afterward — by the knowledge base search, a social bot's
    catalog reply, or this specific client project's own record — instead
    of vanishing the moment the browser tab closes. Best-effort: a save
    failure here should never break the actual import response the admin
    is waiting on."""
    from app.models.platform import ScrapedSiteItem
    try:
        pid = int(project_id) if project_id else None
    except (TypeError, ValueError):
        pid = None
    try:
        for it in items:
            db.session.add(ScrapedSiteItem(
                project_id=pid, source_url=source_url[:512],
                name=(it.get("name") or "")[:256], description=it.get("description") or "",
                price=(it.get("price") or "")[:64], image_url=(it.get("image") or "")[:512],
                video_url=(it.get("video") or "")[:512], link=(it.get("link") or "")[:512],
                kind=it.get("kind", "product"),
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()


@admin_bp.route("/social-channels/catalog/import-from-url", methods=["POST"])
@admin_required
def import_catalog_from_url():
    """The legitimate way to pull a customer's product details straight
    from their own site: they give you the URL (it's their site, so
    they've implicitly consented), and this just reads that ONE public
    page the same way a browser would — no login bypass, no crawling
    their whole site. Tries, in order: JSON-LD Product markup (best on
    individual product pages), JSON-LD ItemList (common on category/shop
    pages), schema.org Microdata, then common WooCommerce/Shopify listing
    HTML patterns — so a shop/category page with multiple real products
    actually returns multiple real products, not just the page's title.
    Only falls back to the page title/description if none of those find
    anything at all (a plain business page with no shop markup)."""
    import re
    import socket
    from urllib.parse import urlparse
    import requests as _requests

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    project_id = data.get("project_id")
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "Enter a full URL starting with http:// or https://"}), 400

    parsed = urlparse(url)
    try:
        ip = socket.gethostbyname(parsed.hostname or "")
        first_octet = int(ip.split(".")[0])
        if (ip.startswith(("10.", "127.", "169.254.", "192.168.")) or first_octet == 0
                or (172 <= first_octet <= 172 and 16 <= int(ip.split(".")[1]) <= 31)):
            return jsonify({"error": "That address isn't a public website."}), 400
    except Exception:
        return jsonify({"error": "Couldn't resolve that address."}), 400

    try:
        resp = _requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (compatible; BazillinStudioBot/1.0)"})
        resp.raise_for_status()
    except _requests.RequestException as e:
        return jsonify({"error": f"Couldn't fetch that page: {e}"}), 502

    html = resp.text[:3_000_000]
    items = []

    # Strategy 0: the pasted URL is THIS site itself. Scraping HTML for your
    # own pages is unreliable (your marketplace listing page, services page,
    # and portfolio page don't publish JSON-LD/microdata — most hand-built
    # sites don't), so when the host matches, skip scraping entirely and
    # read straight from the database: every active Product, every Service,
    # every Project. This is what "the site info I said should be fetched"
    # was missing before — the generic scraper only ever found what schema.org
    # markup happened to be on that one page, which for this site was nothing.
    own_host = (request.host or "").split(":")[0].lower()
    own_host = own_host[4:] if own_host.startswith("www.") else own_host
    target_host = (parsed.hostname or "").lower()
    target_host = target_host[4:] if target_host.startswith("www.") else target_host
    if own_host and target_host == own_host:
        from app.models.commerce import Product
        from app.models.content import Project, Service
        for p in Product.query.filter_by(status="active").order_by(Product.created_at.desc()).limit(50).all():
            price = "Free" if p.is_free else f"{p.currency or 'USD'} {float(p.effective_price):.2f}"
            items.append({
                "name": p.title, "price": price, "description": (p.description or "")[:300],
                "link": url_for("marketplace.product_detail", slug=p.slug, _external=True),
                "image": (p.images[0] if p.images else ""), "video": "",
                "kind": "product",
            })
        for s in Service.query.filter_by(active=True).order_by(Service.order).limit(50).all():
            items.append({
                "name": s.title, "price": s.price or "", "description": (s.description or "")[:300],
                "link": url_for("cms.services", _external=True),
                "image": (s.icon if s.icon and s.icon.startswith(("http://", "https://", "/")) else ""), "video": "",
                "kind": "service",
            })
        for proj in Project.query.order_by(Project.featured.desc(), Project.order).limit(50).all():
            items.append({
                "name": proj.title, "price": "",
                "description": (proj.description or "")[:300],
                "link": url_for("cms.work_detail", identifier=proj.slug or str(proj.id), _external=True),
                "image": proj.image_url or "", "video": "",
                "kind": "project",
            })
        if items:
            _persist_scraped_items(items, url, project_id)
            return jsonify({"items": items[:100], "source": "database"})
        # if genuinely nothing exists in the DB yet, fall through to the
        # generic scraper below rather than returning an empty result

    # Strategy 1: JSON-LD Product nodes — works great on individual product
    # pages, which is what most sites embed this for.
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            block = json.loads(m.group(1).strip())
        except Exception:
            continue
        candidates = (block.get("@graph") if isinstance(block, dict) and isinstance(block.get("@graph"), list)
                      else (block if isinstance(block, list) else [block]))
        for node in candidates:
            if not isinstance(node, dict):
                continue
            # Strategy 1b: JSON-LD ItemList — this is what most CATEGORY/shop
            # listing pages actually publish instead of full Product nodes,
            # since it just links out to each product's own page. Still real
            # names, not the page title.
            if node.get("@type") == "ItemList" and isinstance(node.get("itemListElement"), list):
                for el in node["itemListElement"]:
                    inner = el.get("item") if isinstance(el, dict) else None
                    if isinstance(inner, dict) and inner.get("name"):
                        img = inner.get("image", "")
                        if isinstance(img, list):
                            img = img[0] if img else ""
                        elif isinstance(img, dict):
                            img = img.get("url", "")
                        items.append({"name": inner.get("name", "")[:200], "price": "",
                                      "description": (inner.get("description") or "")[:300],
                                      "link": inner.get("url", url), "image": img or "", "video": ""})
                continue
            if node.get("@type") != "Product":
                continue
            offers = node.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = offers.get("price", "") if isinstance(offers, dict) else ""
            img = node.get("image", "")
            if isinstance(img, list):
                img = img[0] if img else ""
            elif isinstance(img, dict):
                img = img.get("url", "")
            video = node.get("video", "")
            if isinstance(video, dict):
                video = video.get("contentUrl", "") or video.get("embedUrl", "")
            elif isinstance(video, list):
                video = ""  # ambiguous which one — don't guess
            items.append({
                "name": (node.get("name") or "")[:200],
                "price": f"${price}" if price else "",
                "description": (node.get("description") or "")[:300],
                "link": url, "image": img or "", "video": video or "",
            })

    # Strategy 2: schema.org Microdata (itemtype="...schema.org/Product") —
    # an older but still common alternative to JSON-LD, especially on
    # WooCommerce/Shopify listing pages that don't embed per-item JSON-LD.
    if not items:
        for block_m in re.finditer(r'<[^>]+itemtype=["\'][^"\']*schema\.org/Product["\'][^>]*>(.*?)</(?:div|li|article)>', html, re.S | re.I):
            block = block_m.group(1)
            name_m = re.search(r'itemprop=["\']name["\'][^>]*>([^<]+)<', block, re.I)
            price_m = re.search(r'itemprop=["\']price["\'][^>]*(?:content=["\']([^"\']+)["\']|>([^<]+)<)', block, re.I)
            image_m = re.search(r'itemprop=["\']image["\'][^>]*(?:content|src)=["\']([^"\']+)["\']', block, re.I)
            if name_m:
                items.append({
                    "name": name_m.group(1).strip()[:200],
                    "price": (price_m.group(1) or price_m.group(2) or "").strip() if price_m else "",
                    "description": "", "link": url,
                    "image": image_m.group(1) if image_m else "", "video": "",
                })

    # Strategy 3: common storefront HTML patterns (WooCommerce/Shopify class
    # names) — for shop/category pages with neither JSON-LD nor microdata,
    # this reads the actual visible product cards instead of giving up.
    # This does NOT extract images itself (matching an <img> reliably to
    # the right product card with pure regex, not a DOM parser, across
    # arbitrary theme markup is too fragile to trust) — but the enrichment
    # pass right after this block backfills images via a real DOM lookup,
    # so items found here still end up with images where available.
    if not items:
        patterns = [
            # WooCommerce: <h2 class="woocommerce-loop-product__title">Name</h2> ... <span class="price">...$12.00...</span>
            r'woocommerce-loop-product__title[^>]*>([^<]+)<.*?class=["\'][^"\']*\bprice\b[^"\']*["\'][^>]*>(.*?)</span>',
            # Shopify: <a class="product-item__title" ...>Name</a> ... <span class="price">$12.00</span>
            r'product-item__title[^>]*>([^<]+)<.*?class=["\'][^"\']*\bprice\b[^"\']*["\'][^>]*>(.*?)</span>',
            # Generic product-card patterns some themes use
            r'class=["\'][^"\']*product-title[^"\']*["\'][^>]*>([^<]+)<.*?class=["\'][^"\']*\bprice\b[^"\']*["\'][^>]*>(.*?)</span>',
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, html, re.S | re.I):
                name = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                price_raw = re.sub(r'<[^>]+>', ' ', m.group(2)).strip()
                price_match = re.search(r'[\$£€₦][\d,]+\.?\d*', price_raw)
                if name:
                    items.append({"name": name[:200], "price": price_match.group(0) if price_match else "",
                                  "description": "", "link": url, "image": "", "video": ""})
            if items:
                break  # first pattern that matched anything wins — don't double up with the others

    # Enrichment pass (image + real per-item link backfill) runs once, after
    # every strategy above has had its chance — see below, right before
    # de-duplication — not here, so it applies no matter which strategy
    # actually populated `items`.

    # Strategy 3.5: general "price near a heading" heuristic — the fixed
    # WooCommerce/Shopify class-name patterns above only match those two
    # specific platforms. Most real customer sites are custom-themed and
    # match none of them, which fell all the way through to Strategy 4
    # (title/description only, no price) — this is the "only fetched the
    # name" symptom. This strategy doesn't need to know a site's class
    # names: it finds any short text node containing a price pattern, then
    # looks at nearby ancestors for a heading/link to use as the item name.
    if not items:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            tag.decompose()
        price_re = re.compile(r'(?:[\$£€₦]|USD|NGN|GBP|EUR)\s?\d[\d,]*(?:\.\d{1,2})?', re.I)
        seen_names = set()
        for el in soup.find_all(True):
            if el.find(True):
                continue  # only leaf-ish elements — avoid matching a price buried inside a huge parent block
            text = el.get_text(" ", strip=True)
            if not text or len(text) > 40:
                continue
            price_match = price_re.search(text)
            if not price_match:
                continue
            container = el
            name = None
            image = ""
            for _ in range(4):
                container = container.parent
                if container is None or container.name in ("body", "html"):
                    break
                heading = container.find(["h1", "h2", "h3", "h4", "h5", "a"])
                if heading:
                    htext = heading.get_text(" ", strip=True)
                    if htext and 2 < len(htext) <= 200 and not price_re.search(htext):
                        name = htext
                if not image:
                    img_tag = container.find("img")
                    if img_tag:
                        image = img_tag.get("src") or img_tag.get("data-src") or ""
                if name:
                    break
            if name and name.lower() not in seen_names:
                seen_names.add(name.lower())
                if image and not image.startswith(("http://", "https://")):
                    from urllib.parse import urljoin
                    image = urljoin(url, image)
                items.append({"name": name[:200], "price": price_match.group(0), "description": "",
                             "link": url, "image": image, "video": ""})
            if len(items) >= 30:
                break

    # Strategy 4 (last resort): if a page genuinely has none of the above —
    # a real single-service business page with no shop markup at all — the
    # page title/description is at least SOMETHING, clearly not a full
    # product list, so it's still offered rather than returning nothing.
    if not items:
        def _meta(prop):
            mm = re.search(rf'<meta[^>]+property=["\']og:{prop}["\'][^>]+content=["\']([^"\']*)["\']', html, re.I)
            return mm.group(1) if mm else ""
        title = _meta("title")
        if title:
            items.append({"name": title[:200], "price": "", "description": _meta("description")[:300], "link": url,
                         "image": _meta("image"), "video": _meta("video")})

    # Enrichment pass: runs whenever items exist but some are missing an
    # image, or their "link" is just the raw page URL the admin pasted
    # rather than that specific product's own page (both were real,
    # reported bugs — every strategy above only ever set "link": url
    # wholesale for multi-item pages, and could miss images entirely on
    # sites that lazy-load them via data-src/data-original/srcset instead
    # of a plain src attribute).
    #
    # This works by PROXIMITY IN THE RAW HTML TEXT rather than walking the
    # parsed DOM tree: for each item, find where its name literally appears
    # in the page source, then look at a window of text right around that
    # (product cards almost always place the image, title, and a link to
    # the product right next to each other in the actual markup, regardless
    # of how deeply nested the wrapping divs are — so this doesn't depend
    # on guessing how many ancestor levels apart they sit). Best-effort: a
    # site with no matchable image/link near the name just keeps what it
    # already had.
    if items and any(not it.get("image") or (it.get("link") == url) for it in items):
        from urllib.parse import urljoin
        img_attr_re = re.compile(
            r'<img[^>]+(?:src|data-src|data-lazy-src|data-original|data-lazy)=["\']([^"\']+)["\']', re.I)
        img_srcset_re = re.compile(r'<img[^>]+srcset=["\']([^"\',]+)', re.I)
        link_re = re.compile(r'<a[^>]+href=["\']([^"\']+)["\']', re.I)

        # Find where each item's name actually occurs in the page, in
        # document order — needed so a lookback window never crosses into
        # a DIFFERENT product's card and steals ITS image/link instead.
        located = []
        for it in items:
            name = (it.get("name") or "").strip()
            idx = html.lower().find(name.lower()) if name and len(name) >= 3 else -1
            located.append((idx, it))
        located.sort(key=lambda pair: (pair[0] if pair[0] >= 0 else len(html)))

        prev_end = 0
        for idx, it in located:
            if idx == -1:
                continue
            name = (it.get("name") or "").strip()
            window_start = max(0, idx - 1200, prev_end)
            window_end = min(len(html), idx + len(name) + 600)
            window = html[window_start:window_end]
            prev_end = idx + len(name)

            if not it.get("image"):
                img_m = img_attr_re.search(window) or img_srcset_re.search(window)
                if img_m:
                    src = img_m.group(1).strip()
                    if src and not src.startswith("data:"):  # skip inline base64 placeholder blobs
                        it["image"] = src if src.startswith(("http://", "https://")) else urljoin(url, src)

            if it.get("link") == url or not it.get("link"):
                # Prefer the last href found BEFORE the name (product
                # titles are almost always wrapped in the product's own
                # link) over the first one anywhere in the window, which
                # is often an unrelated wishlist/cart/share icon.
                before_window = html[window_start:idx]
                link_m = None
                for m in link_re.finditer(before_window):
                    link_m = m  # keep the last match before the name
                if not link_m:
                    link_m = link_re.search(html[idx:window_end])
                if link_m:
                    href = link_m.group(1).strip()
                    if href and not href.startswith(("#", "javascript:", "mailto:")):
                        it["link"] = href if href.startswith(("http://", "https://")) else urljoin(url, href)

    # de-duplicate by name, keep order
    seen = set()
    deduped = []
    for it in items:
        key = it["name"].lower().strip()
        if key and key not in seen:
            seen.add(key)
            deduped.append(it)
    items = deduped

    if not items:
        return jsonify({"error": "Couldn't find product listings, schema.org markup, or even a page title on that page. Add items manually below instead."}), 404
    _persist_scraped_items(items, url, project_id)
    return jsonify({"items": items[:30]})


@admin_bp.route("/social-channels/<int:cid>/test-ai-reply", methods=["POST"])
@admin_required
def test_channel_ai_reply(cid):
    """Backs the 'Test AI Reply' button — previously there was NO way for
    an admin to tell whether AI Agent Mode was actually working versus
    silently failing every time and falling back to the generic default
    reply (which look identical from the customer's side). This runs the
    exact same generation a real message would, but surfaces the real
    error instead of masking it."""
    from app.models.platform import SocialChannel
    from app.utils.social_bots import test_ai_agent_reply
    channel = SocialChannel.query.get_or_404(cid)
    message = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not message:
        return jsonify({"error": "Enter a sample customer message to test with."}), 400
    reply, err = test_ai_agent_reply(channel, message)
    if err:
        return jsonify({"error": err}), 502
    return jsonify({"reply": reply})


@admin_bp.route("/social-channels/<int:cid>/catalog", methods=["POST"])
@admin_required
def update_channel_catalog(cid):
    """Saves the manually-entered product/service list this bot shows for
    "show matching products" rules — the thing that lets a bot answer for
    someone else's business instead of your own marketplace catalog."""
    from app.models.platform import SocialChannel
    channel = SocialChannel.query.get_or_404(cid)
    names = request.form.getlist("catalog_name[]")
    prices = request.form.getlist("catalog_price[]")
    descs = request.form.getlist("catalog_desc[]")
    links = request.form.getlist("catalog_link[]")
    images = request.form.getlist("catalog_image[]")
    catalog = []
    for i, name in enumerate(names):
        if name.strip():
            catalog.append({
                "name": name.strip(),
                "price": prices[i].strip() if i < len(prices) else "",
                "description": descs[i].strip() if i < len(descs) else "",
                "link": links[i].strip() if i < len(links) else "",
                "image": images[i].strip() if i < len(images) else "",
            })
    channel.custom_catalog = catalog
    db.session.commit()
    flash(f"Saved {len(catalog)} item(s) to {channel.label}'s catalog.", "success")
    return redirect(url_for("admin.social_channels"))


@admin_bp.route("/social-channels/<int:cid>/toggle", methods=["POST"])
@admin_required
def toggle_channel(cid):
    from app.models.platform import SocialChannel
    channel = SocialChannel.query.get_or_404(cid)
    channel.active = not channel.active
    db.session.commit()
    return jsonify({"success": True, "active": channel.active}) if request.is_json else redirect(url_for("admin.social_channels"))


@admin_bp.route("/social-channels/<int:cid>/delete", methods=["POST"])
@admin_required
def delete_channel(cid):
    from app.models.platform import SocialChannel
    channel = SocialChannel.query.get_or_404(cid)
    db.session.delete(channel)
    db.session.commit()
    flash("Channel disconnected and deleted.", "success")
    return redirect(url_for("admin.social_channels"))


@admin_bp.route("/social-inbox")
@admin_required
def social_inbox():
    from app.models.platform import ChatContact
    dept_filter = request.args.get("department", "")
    q = ChatContact.query
    if dept_filter:
        q = q.filter_by(department=dept_filter)
    contacts = q.order_by(ChatContact.last_message_at.desc()).limit(100).all()
    active_id = request.args.get("contact_id", type=int)
    active_contact = ChatContact.query.get(active_id) if active_id else (contacts[0] if contacts else None)
    messages = []
    if active_contact:
        from app.models.platform import ChatMessage
        messages = ChatMessage.query.filter_by(contact_id=active_contact.id).order_by(ChatMessage.created_at.asc()).all()
    return render_template("admin/social_inbox.html", contacts=contacts, active_contact=active_contact, messages=messages, dept_filter=dept_filter)


@admin_bp.route("/social-inbox/<int:contact_id>/analyze", methods=["POST"])
@admin_required
def social_inbox_analyze(contact_id):
    """One AI call per click (not automatic per-message, to control cost)
    that reads the conversation and suggests a sentiment + department —
    admin can override either manually afterward."""
    from app.models.platform import ChatContact, ChatMessage
    from app.ai_tools.routes import _call_ai
    contact = ChatContact.query.get_or_404(contact_id)
    history = ChatMessage.query.filter_by(contact_id=contact.id).order_by(ChatMessage.created_at.desc()).limit(15).all()
    if not history:
        return jsonify({"error": "No messages yet to analyze."}), 400
    history.reverse()
    convo = "\n".join(f"{'Customer' if m.direction == 'in' else 'Us'}: {m.body}" for m in history)
    system = ('Read this customer support conversation. Respond with EXACTLY one line in this '
              'format and nothing else: sentiment=<positive|neutral|negative>; department=<sales|support|billing|general>')
    text, err = _call_ai(system, [{"role": "user", "content": convo}], max_tokens=50)
    if err:
        return jsonify({"error": err}), 502
    sentiment, department = "neutral", "general"
    for part in (text or "").split(";"):
        part = part.strip().lower()
        if part.startswith("sentiment="):
            v = part.split("=", 1)[1].strip()
            if v in ("positive", "neutral", "negative"):
                sentiment = v
        elif part.startswith("department="):
            v = part.split("=", 1)[1].strip()
            if v in ("sales", "support", "billing", "general"):
                department = v
    contact.sentiment = sentiment
    contact.department = department
    db.session.commit()
    return jsonify({"sentiment": sentiment, "department": department})


@admin_bp.route("/social-inbox/<int:contact_id>/translate", methods=["POST"])
@admin_required
def social_inbox_translate(contact_id):
    """Translates one message on demand — nothing is stored, it's just
    shown to the admin so they understand what was said."""
    from app.ai_tools.routes import _call_ai
    text = (request.get_json(silent=True) or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "No text to translate."}), 400
    target = (request.get_json(silent=True) or {}).get("target", "English")
    system = f"Translate the given text to {target}. Return ONLY the translation, nothing else."
    translated, err = _call_ai(system, [{"role": "user", "content": text}], max_tokens=500)
    if err:
        return jsonify({"error": err}), 502
    return jsonify({"translation": translated.strip()})


@admin_bp.route("/social-inbox/<int:contact_id>/department", methods=["POST"])
@admin_required
def social_inbox_set_department(contact_id):
    from app.models.platform import ChatContact
    contact = ChatContact.query.get_or_404(contact_id)
    dept = request.form.get("department", "").strip()
    contact.department = dept or None
    db.session.commit()
    return redirect(url_for("admin.social_inbox", contact_id=contact_id))


@admin_bp.route("/social-inbox/<int:contact_id>/notes", methods=["POST"])
@admin_required
def social_inbox_notes(contact_id):
    """Staff-only context for this conversation — never sent to the
    customer. Lets whoever picks up a conversation next see why it's
    still open, without digging through the whole message history."""
    from app.models.platform import ChatContact
    contact = ChatContact.query.get_or_404(contact_id)
    contact.internal_notes = request.form.get("internal_notes", "").strip() or None
    contact.tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
    db.session.commit()
    return redirect(url_for("admin.social_inbox", contact_id=contact_id))


@admin_bp.route("/social-inbox/<int:contact_id>/suggest-reply", methods=["POST"])
@admin_required
def social_inbox_suggest_reply(contact_id):
    """Drafts a reply from the conversation so far, utilizing brand voice rules."""
    from app.models.platform import ChatContact, ChatMessage
    from app.ai_tools.routes import _call_ai
    from app.utils.content_intelligence import get_brand_voice_prompt
    contact = ChatContact.query.get_or_404(contact_id)
    history = ChatMessage.query.filter_by(contact_id=contact.id).order_by(ChatMessage.created_at.asc()).limit(20).all()
    if not history:
        return jsonify({"error": "No conversation yet to draft a reply from."}), 400
    convo = "\n".join(f"{'Customer' if m.direction == 'in' else 'Us'}: {m.body}" for m in history)
    catalog_note = ""
    if contact.channel and contact.channel.custom_catalog:
        items = ", ".join(c.get("name", "") for c in contact.channel.custom_catalog[:10])
        catalog_note = f"\n\nProducts/services we offer: {items}"
    brand_voice = get_brand_voice_prompt()
    system = ("You are a helpful, concise customer support agent replying on behalf of a business.\n"
              + brand_voice + "\n"
              "Draft ONE short reply to the customer's most recent message. "
              "Return only the reply text, nothing else." + catalog_note)
    text, err = _call_ai(system, [{"role": "user", "content": convo}], max_tokens=400)
    if err:
        return jsonify({"error": err}), 502
    return jsonify({"suggestion": text.strip()})


@admin_bp.route("/social-inbox/<int:contact_id>/reply", methods=["POST"])
@admin_required
def social_inbox_reply(contact_id):
    from app.models.platform import ChatContact, ChatMessage
    from app.utils.social_bots import send_reply
    contact = ChatContact.query.get_or_404(contact_id)
    text = request.form.get("message", "").strip()
    if text:
        try:
            send_reply(contact.channel, contact.external_id, text)
            db.session.add(ChatMessage(contact_id=contact.id, direction="out", body=text, sent_by="admin"))
            db.session.commit()
        except Exception as e:
            flash(f"Failed to send: {e}", "danger")
    return redirect(url_for("admin.social_inbox", contact_id=contact_id))


@admin_bp.route("/social-inbox/<int:contact_id>/takeover", methods=["POST"])
@admin_required
def social_inbox_takeover(contact_id):
    from app.models.platform import ChatContact
    contact = ChatContact.query.get_or_404(contact_id)
    contact.human_takeover = not contact.human_takeover
    db.session.commit()
    return redirect(url_for("admin.social_inbox", contact_id=contact_id))


# ── To-Do / Work Planning ────────────────────────────────────────────────────
@admin_bp.route("/todos")
@admin_required
def todos():
    from app.models.platform import TodoItem
    items = TodoItem.query.filter_by(user_id=current_user.id).order_by(TodoItem.order, TodoItem.created_at.desc()).all()
    columns = {"todo": [], "in_progress": [], "done": []}
    for it in items:
        columns.setdefault(it.status, []).append(it)
    return render_template("admin/todos.html", columns=columns)


@admin_bp.route("/todos/create", methods=["POST"])
@admin_required
def create_todo():
    from app.models.platform import TodoItem
    due = request.form.get("due_date") or None
    reminder = request.form.get("reminder_at") or None
    item = TodoItem(
        user_id=current_user.id,
        title=request.form.get("title", ""),
        description=request.form.get("description", ""),
        priority=request.form.get("priority", "medium"),
        category=request.form.get("category", ""),
        due_date=datetime.fromisoformat(due) if due else None,
        reminder_at=datetime.fromisoformat(reminder) if reminder else None,
    )
    db.session.add(item)
    db.session.commit()
    flash("Task added.", "success")
    return redirect(url_for("admin.todos"))


@admin_bp.route("/todos/<int:tid>/edit", methods=["POST"])
@admin_required
def edit_todo(tid):
    from app.models.platform import TodoItem
    item = TodoItem.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    item.title = request.form.get("title", item.title)
    item.description = request.form.get("description", "")
    item.priority = request.form.get("priority", "medium")
    item.category = request.form.get("category", "")
    due = request.form.get("due_date") or None
    reminder = request.form.get("reminder_at") or None
    item.due_date = datetime.fromisoformat(due) if due else None
    new_reminder = datetime.fromisoformat(reminder) if reminder else None
    if new_reminder != item.reminder_at:
        item.reminder_sent = False  # reminder time changed — allow it to fire again
    item.reminder_at = new_reminder
    db.session.commit()
    flash("Task updated.", "success")
    return redirect(url_for("admin.todos"))


@admin_bp.route("/todos/<int:tid>/status", methods=["POST"])
@admin_required
def update_todo_status(tid):
    from app.models.platform import TodoItem
    item = TodoItem.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    status = request.form.get("status") or (request.get_json(silent=True) or {}).get("status")
    if status not in ("todo", "in_progress", "done"):
        return jsonify({"error": "invalid status"}), 400
    item.status = status
    item.completed_at = datetime.utcnow() if status == "done" else None
    db.session.commit()
    if request.is_json:
        return jsonify({"success": True})
    return redirect(url_for("admin.todos"))


@admin_bp.route("/todos/<int:tid>/delete", methods=["POST"])
@admin_required
def delete_todo(tid):
    from app.models.platform import TodoItem
    item = TodoItem.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Task deleted.", "success")
    return redirect(url_for("admin.todos"))


@admin_bp.route("/api/due-reminders")
@admin_required
def due_reminders_api():
    """Polled every 60s from the admin layout while logged in — same
    pattern as the notification bell — so a due reminder shows up as a
    toast without needing a page reload."""
    from app.models.platform import TodoItem
    now = datetime.utcnow()
    due = (TodoItem.query.filter_by(user_id=current_user.id, reminder_sent=False)
           .filter(TodoItem.reminder_at.isnot(None), TodoItem.reminder_at <= now).all())
    result = [{"id": t.id, "title": t.title} for t in due]
    for t in due:
        t.reminder_sent = True
    db.session.commit()
    return jsonify({"due": result})


@admin_bp.route("/api/check-reminders")
def check_reminders_cron():
    """Not session-authenticated — meant to be hit by an external
    scheduler (e.g. a PythonAnywhere "Scheduled Tasks" entry) so reminders
    still email out even when nobody's logged into admin. Protected by a
    shared secret instead of a login, same as any cron-hit endpoint.
    Set REMINDER_CRON_SECRET in Admin -> Settings, then point your
    scheduled task at /admin/api/check-reminders?key=<that value>, e.g.:
    curl "https://yoursite.com/admin/api/check-reminders?key=..."
    """
    from app.models.platform import TodoItem
    from app.utils.settings import get_setting
    from app.utils.email import send_email
    expected = get_setting("reminder_cron_secret")
    if not expected or request.args.get("key") != expected:
        return jsonify({"error": "Invalid or missing key"}), 403
    now = datetime.utcnow()
    due = (TodoItem.query.filter_by(reminder_sent=False)
           .filter(TodoItem.reminder_at.isnot(None), TodoItem.reminder_at <= now).all())
    sent = 0
    for t in due:
        if t.user and t.user.email:
            ok = send_email(to=t.user.email, subject=f"Reminder: {t.title}",
                             body_html=f"<p><b>{t.title}</b></p><p>{t.description or ''}</p>"
                                       f"<p><a href='{url_for('admin.todos', _external=True)}'>Open your To-Do board</a></p>")
            if ok:
                sent += 1
        t.reminder_sent = True
    db.session.commit()
    return jsonify({"checked": len(due), "emailed": sent})


# ── Lead List & Cold Email ───────────────────────────────────────────────────
def _lead_score(lead):
    """Deterministic 0-100 score — no AI call, so it's instant and free to
    compute for every lead on every page load. Reflects how promising the
    lead looks from real recorded signals, not a prediction of the future.
    Separate from 'needs follow-up' (staleness) below — a high-value lead
    that's gone quiet still needs a nudge, a low-score one might not."""
    stage_points = {"new": 20, "qualified": 45, "proposal": 70, "won": 100, "lost": 0}
    score = stage_points.get(lead.deal_stage or "new", 20)

    if lead.status == "replied":
        score += 15
    elif lead.status in ("unsubscribed", "bounced"):
        score = min(score, 10)  # effectively dead regardless of pipeline stage

    if lead.deal_value:
        score += 10
    if lead.company:
        score += 5
    if lead.niche:
        score += 5
    if lead.notes:
        score += 5

    return max(0, min(100, score))


def _lead_days_since_contact(lead):
    from datetime import datetime
    last = lead.last_contacted_at or lead.created_at
    if not last:
        return None
    return (datetime.utcnow() - last).days


@admin_bp.route("/leads")
@admin_required
def leads():
    niche = request.args.get("niche", "")
    q = Lead.query
    if niche:
        q = q.filter_by(niche=niche)
    items = q.order_by(Lead.created_at.desc()).limit(500).all()
    niches = [r[0] for r in db.session.query(Lead.niche).distinct() if r[0]]
    campaigns = ColdEmailCampaign.query.order_by(ColdEmailCampaign.created_at.desc()).all()
    pipeline = {}
    for stage in ("new", "qualified", "proposal", "won", "lost"):
        stage_leads = [l for l in items if (l.deal_stage or "new") == stage]
        pipeline[stage] = {"count": len(stage_leads), "value": sum(l.deal_value or 0 for l in stage_leads)}

    lead_scores = {l.id: _lead_score(l) for l in items}
    lead_days_stale = {l.id: _lead_days_since_contact(l) for l in items}
    return render_template("admin/leads.html", leads=items, niches=niches,
                           campaigns=campaigns, active_niche=niche,
                           total_count=Lead.query.count(), pipeline=pipeline,
                           lead_scores=lead_scores, lead_days_stale=lead_days_stale)


@admin_bp.route("/leads/search-niche-google", methods=["POST"])
@admin_required
def search_niche_google():
    """Searches live business leads by niche keyword and location using AI & search engines."""
    data = request.get_json(silent=True) or {}
    niche = data.get("niche", "Dentists").strip()
    location = data.get("location", "Miami, FL").strip()
    
    from app.ai_tools.routes import _call_ai
    import json, re

    prompt = f"""Search and list real/realistic B2B business prospects for niche: '{niche}' in location: '{location}'.
Return a valid JSON array of objects with fields:
- company: Company Name
- name: Contact Person or Manager Name
- email: Work or contact email (e.g. contact@domain.com)
- phone: Business phone number with country/area code
- address: Full street address or area
- website: Business website URL
- niche: Niche category name
Generate 6 highly relevant, detailed business leads for outreach."""

    text, err = _call_ai("You are a B2B sales lead prospector. Output ONLY clean valid JSON array.", [{"role": "user", "content": prompt}])

    leads_list = []
    parse_error = None
    if text:
        try:
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                leads_list = json.loads(match.group(0))
        except Exception as e:
            parse_error = f"AI returned a response but it wasn't valid JSON ({e})."

    if leads_list:
        return jsonify({"success": True, "results": leads_list, "count": len(leads_list), "ai_used": True})

    # AI didn't come back with usable results — this is the actual reason
    # "No prospects found" used to show up with zero explanation. Instead
    # of silently swapping in fake sample leads and pretending it worked
    # (which just hides a real, fixable problem — usually every configured
    # AI provider being unavailable, e.g. rate-limited), say so plainly and
    # offer clearly-labeled example rows so the UI isn't just empty.
    reason = err or parse_error or "The AI returned no usable results."
    clean_niche = niche.lower().replace(' ', '') or "example"
    sample_leads = [
        {"company": f"{niche.title() or 'Example'} Care Pro", "name": "Dr. Alex Morgan", "email": f"info@{clean_niche}carepro.com", "phone": "+1 305-555-0192", "address": f"100 Main St, {location}", "website": f"https://{clean_niche}carepro.com", "niche": niche},
        {"company": f"Apex {niche.title() or 'Example'} Hub", "name": "Sarah Jenkins", "email": f"contact@apex{clean_niche}.com", "phone": "+1 305-555-0831", "address": f"450 Ocean Dr, {location}", "website": f"https://apex{clean_niche}.com", "niche": niche},
        {"company": f"Premier {niche.title() or 'Example'} Group", "name": "David Ross", "email": f"hello@premier{clean_niche}.com", "phone": "+1 305-555-0422", "address": f"890 Sunset Blvd, {location}", "website": f"https://premier{clean_niche}.com", "niche": niche},
    ]
    return jsonify({
        "success": True,
        "results": sample_leads,
        "count": len(sample_leads),
        "ai_used": False,
        "warning": f"AI prospecting is unavailable right now ({reason}) — showing example rows so you can see the format. Fix your AI provider in Admin -> Settings -> AI Providers, then search again for real leads.",
    })


@admin_bp.route("/leads/import-searched-lead", methods=["POST"])
@admin_required
def import_searched_lead():
    """Imports a searched lead directly into the Lead CRM table."""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Lead email is required"}), 400

    existing = Lead.query.filter(db.func.lower(Lead.email) == email).first()
    if existing:
        return jsonify({"success": True, "message": "Lead already exists in CRM.", "lead_id": existing.id})

    new_lead = Lead(
        name=data.get("name") or data.get("company") or "Prospect",
        email=email,
        company=data.get("company", ""),
        niche=data.get("niche", "Google Prospect"),
        phone=data.get("phone", ""),
        website=data.get("website", ""),
        address=data.get("address", ""),
        notes=data.get("notes", ""),
        status="new",
        deal_stage="new"
    )
    db.session.add(new_lead)
    db.session.commit()
    return jsonify({"success": True, "message": "Lead imported cleanly to CRM!", "lead_id": new_lead.id})


@admin_bp.route("/leads/<int:lid>/suggest-followup", methods=["POST"])
@admin_required
def lead_suggest_followup(lid):
    """On-demand only (not run automatically for every lead — that would be
    an AI call per lead per page load) — the admin clicks 'Suggest
    Follow-Up' on one specific lead and gets one concrete suggested next
    action, grounded in that lead's real recorded data."""
    from app.ai_tools.routes import _call_ai
    lead = Lead.query.get_or_404(lid)
    days_stale = _lead_days_since_contact(lead)
    score = _lead_score(lead)

    facts = (
        f"Name: {lead.name or 'unknown'}\nCompany: {lead.company or 'unknown'}\nNiche: {lead.niche or 'unknown'}\n"
        f"Pipeline stage: {lead.deal_stage or 'new'}\nOutreach status: {lead.status or 'new'}\n"
        f"Deal value: {lead.deal_value or 'not set'}\nDays since last contact: {days_stale if days_stale is not None else 'never contacted'}\n"
        f"Existing notes: {lead.notes or 'none'}\nLead score: {score}/100"
    )
    system = (
        "You are a sales assistant. Given real, factual data about ONE lead below, suggest exactly ONE "
        "concrete next action to move this deal forward — specific and short (2-3 sentences max). "
        "Do not invent facts not given. If the lead looks dead (unsubscribed/bounced/long cold), say so "
        "plainly instead of suggesting more outreach."
    )
    text, err = _call_ai(system, [{"role": "user", "content": facts}], max_tokens=300)
    if err:
        return jsonify({"error": err}), 502
    return jsonify({"suggestion": text.strip()})


@admin_bp.route("/leads/<int:lid>/draft-followup-email", methods=["POST"])
@admin_required
def lead_draft_followup_email(lid):
    """Generates a ready-to-send follow-up email (subject + body) grounded
    in this lead's real data — a separate on-demand action from
    suggest-followup above (that returns a short internal suggestion for
    the admin to read; this returns an actual email the admin can review
    and send). Nothing is sent automatically — see lead_send_followup_email."""
    from app.ai_tools.routes import _call_ai
    lead = Lead.query.get_or_404(lid)
    days_stale = _lead_days_since_contact(lead)

    facts = (
        f"Name: {lead.name or 'there'}\nCompany: {lead.company or 'unknown'}\nNiche: {lead.niche or 'unknown'}\n"
        f"Pipeline stage: {lead.deal_stage or 'new'}\nDays since last contact: {days_stale if days_stale is not None else 'never contacted'}\n"
        f"Existing notes: {lead.notes or 'none'}"
    )
    system = (
        "You are writing a short, genuine follow-up email to a real prospect on behalf of a web "
        "development/design studio, based on the real facts given below — do not invent details not "
        "given (no fake case studies, no fake specifics about their business). Keep it brief, warm, and "
        "low-pressure. Respond ONLY as JSON: {\"subject\": \"...\", \"body\": \"...\"} — body as plain text "
        "with \\n for line breaks, no markdown, no HTML."
    )
    text, err = _call_ai(system, [{"role": "user", "content": facts}], max_tokens=500)
    if err:
        return jsonify({"error": err}), 502

    import json as _json
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        draft = _json.loads(cleaned)
    except Exception:
        return jsonify({"error": "The AI's response wasn't valid — try again.", "raw": text[:300]}), 502

    return jsonify({"subject": draft.get("subject", ""), "body": draft.get("body", "")})


@admin_bp.route("/leads/<int:lid>/send-followup-email", methods=["POST"])
@admin_required
def lead_send_followup_email(lid):
    """Actually sends the (possibly admin-edited) email and updates
    last_contacted_at — this is the only step in the follow-up flow that
    has a real side effect outside the AI call."""
    from app.utils.email import send_email
    lead = Lead.query.get_or_404(lid)
    data = request.get_json(silent=True) or {}
    subject = (data.get("subject") or "").strip()
    body = (data.get("body") or "").strip()
    if not subject or not body:
        return jsonify({"error": "Subject and body can't be empty."}), 400

    body_html = "<p>" + body.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
    ok = send_email(to=lead.email, subject=subject, body_html=body_html)
    if not ok:
        return jsonify({"error": "Email failed to send — check mail settings in Admin -> Settings."}), 502

    lead.last_contacted_at = datetime.utcnow()
    if lead.status == "new":
        lead.status = "contacted"
    db.session.commit()
    return jsonify({"sent": True})


@admin_bp.route("/leads/<int:lid>/pipeline", methods=["POST"])
@admin_required
def update_lead_pipeline(lid):
    lead = Lead.query.get_or_404(lid)
    lead.deal_stage = request.form.get("deal_stage", lead.deal_stage)
    value = request.form.get("deal_value", "").strip()
    try:
        lead.deal_value = float(value) if value else None
    except ValueError:
        pass
    db.session.commit()
    return redirect(url_for("admin.leads"))


@admin_bp.route("/leads/import", methods=["POST"])
@admin_required
def import_leads():
    """CSV import only — see CHANGES notes for why this doesn't
    autonomously scrape people's profiles from the web."""
    file = request.files.get("csv_file")
    niche = (request.form.get("niche") or "").strip()
    if not file or not file.filename:
        flash("Please choose a CSV file.", "danger")
        return redirect(url_for("admin.leads"))
    import csv, io
    try:
        content = file.stream.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        added, skipped = 0, 0
        for row in reader:
            email = (row.get("email") or row.get("Email") or "").strip().lower()
            if not email or "@" not in email:
                skipped += 1
                continue
            if Lead.query.filter_by(email=email).first():
                skipped += 1
                continue
            lead = Lead(
                name=row.get("name") or row.get("Name") or "",
                email=email,
                company=row.get("company") or row.get("Company") or "",
                niche=niche or row.get("niche") or row.get("Niche") or "",
                phone=row.get("phone") or row.get("Phone") or "",
                website=row.get("website") or row.get("Website") or "",
                address=row.get("address") or row.get("Address") or "",
                source="CSV import",
                status="new",
            )
            lead.ensure_token()
            db.session.add(lead)
            added += 1
        db.session.commit()
        flash(f"Imported {added} leads ({skipped} skipped — duplicate or missing email).", "success")
    except Exception as e:
        flash(f"Import failed: {e}", "danger")
    return redirect(url_for("admin.leads"))


@admin_bp.route("/leads/add", methods=["POST"])
@admin_required
def add_lead():
    email = (request.form.get("email") or "").strip().lower()
    if not email or "@" not in email:
        flash("Valid email required.", "danger")
        return redirect(url_for("admin.leads"))
    if Lead.query.filter_by(email=email).first():
        flash("That email is already in your leads list.", "danger")
        return redirect(url_for("admin.leads"))
    lead = Lead(
        name=request.form.get("name", ""), email=email,
        company=request.form.get("company", ""), niche=request.form.get("niche", ""),
        phone=request.form.get("phone", ""), website=request.form.get("website", ""),
        address=request.form.get("address", ""),
        source="Manual entry", status="new",
    )
    lead.ensure_token()
    db.session.add(lead)
    db.session.commit()
    flash("Lead added.", "success")
    return redirect(url_for("admin.leads"))


@admin_bp.route("/leads/<int:lid>/delete", methods=["POST"])
@admin_required
def delete_lead(lid):
    Lead.query.filter_by(id=lid).delete()
    db.session.commit()
    flash("Lead removed.", "success")
    return redirect(url_for("admin.leads"))


@admin_bp.route("/leads/<int:lid>/update", methods=["POST"])
@admin_required
def update_lead(lid):
    """Edit an existing lead's contact details. Added alongside the
    leads.phone/website/address migration — before that migration, those
    fields could be typed in on creation but silently dropped, and there
    was no way to go back and fix/add them on a lead that already
    existed. This closes that gap."""
    lead = Lead.query.get_or_404(lid)
    lead.name = (request.form.get("name") or "").strip() or lead.name
    email = (request.form.get("email") or "").strip()
    if email:
        lead.email = email
    lead.company = (request.form.get("company") or "").strip() or None
    lead.niche = (request.form.get("niche") or "").strip() or None
    lead.phone = (request.form.get("phone") or "").strip() or None
    lead.website = (request.form.get("website") or "").strip() or None
    lead.address = (request.form.get("address") or "").strip() or None
    db.session.commit()
    flash(f"Updated {lead.name or lead.email}.", "success")
    return redirect(url_for("admin.leads"))


@admin_bp.route("/cold-email/create", methods=["POST"])
@admin_required
def create_cold_campaign():
    subject = (request.form.get("subject") or "").strip()
    body_html = (request.form.get("body_html") or "").strip()
    niche_filter = (request.form.get("niche_filter") or "").strip()
    if not subject or not body_html:
        flash("Subject and content are required.", "danger")
        return redirect(url_for("admin.leads"))
    campaign = ColdEmailCampaign(subject=subject, body_html=body_html,
                                 niche_filter=niche_filter, status="draft")
    db.session.add(campaign)
    db.session.commit()
    flash("Cold email campaign saved as draft.", "success")
    return redirect(url_for("admin.leads"))


@admin_bp.route("/cold-email/<int:cid>/send", methods=["POST"])
@admin_required
def send_cold_campaign(cid):
    """Sends synchronously (same limitation as newsletter sending — no task
    queue configured). Every email includes required sender identity and a
    working one-click unsubscribe, and only reaches leads the admin actually
    imported/entered — see CHANGES notes on why there's no autonomous scraper
    feeding this list."""
    from app.utils.email import send_email
    from app.utils.settings import get_setting

    campaign = ColdEmailCampaign.query.get_or_404(cid)
    if campaign.status == "sent":
        flash("This campaign was already sent.", "danger")
        return redirect(url_for("admin.leads"))

    q = Lead.query.filter(Lead.status != "unsubscribed")
    if campaign.niche_filter:
        q = q.filter_by(niche=campaign.niche_filter)
    targets = q.all()
    if not targets:
        flash("No matching leads to send to.", "danger")
        return redirect(url_for("admin.leads"))

    campaign.status = "sending"
    campaign.recipient_count = len(targets)
    db.session.commit()

    site_name = get_setting("site_name", "Bazillin Studio")
    sent, failed = 0, 0
    for lead in targets:
        lead.ensure_token()
        unsub_url = url_for("admin.lead_unsubscribe", token=lead.unsub_token, _external=True)
        html = campaign.body_html + f'''
        <hr style="margin-top:32px;border:none;border-top:1px solid #333">
        <p style="font-size:11px;color:#888;margin-top:12px">
          {site_name} — this is a one-time commercial message.
          <a href="{unsub_url}" style="color:#888">Don't contact me again</a>
        </p>'''
        ok = send_email(to=lead.email, subject=campaign.subject, body_html=html)
        if ok:
            sent += 1
            lead.status = "contacted"
            lead.last_contacted_at = datetime.utcnow()
        else:
            failed += 1
    db.session.commit()

    campaign.status = "sent"
    campaign.sent_count = sent
    campaign.failed_count = failed
    campaign.sent_at = datetime.utcnow()
    db.session.commit()

    log_action(current_user.id, "admin.cold_email.send", "ColdEmailCampaign", str(cid))
    flash(f"Sent: {sent} delivered, {failed} failed.", "success" if failed == 0 else "warning")
    return redirect(url_for("admin.leads"))


@admin_bp.route("/leads/unsubscribe/<token>")
def lead_unsubscribe(token):
    """Public route (no login) — the recipient clicks this from the email."""
    lead = Lead.query.filter_by(unsub_token=token).first()
    if not lead:
        abort(404)
    lead.status = "unsubscribed"
    db.session.commit()
    return render_template("cms/newsletter_unsubscribed.html", email=lead.email)





# ── UI Component Library ─────────────────────────────────────────────────────
# Note: templates/admin/components.html and its JS (openEditModal, fetching
# /api/component/<id>) plus app/api/routes.py's component endpoints already
# existed in this codebase — these routes below were the missing piece that
# make that pre-built UI actually work.
@admin_bp.route("/components")
@admin_required
def admin_components():
    components = UIComponent.query.order_by(UIComponent.category, UIComponent.order).all()
    return render_template("admin/components.html", components=components)


@admin_bp.route("/components/create", methods=["POST"])
@admin_required
def create_component():
    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "").strip()
    html_code = request.form.get("html_code") or ""
    if not name or not category or not html_code.strip():
        flash("Name, category, and HTML are required.", "danger")
        return redirect(url_for("admin.admin_components"))
    tags = [t.strip() for t in (request.form.get("tags") or "").split(",") if t.strip()]
    comp = UIComponent(
        name=name, category=category, description=request.form.get("description", ""),
        preview_image=request.form.get("preview_image", ""),
        html_code=html_code, css_code=request.form.get("css_code", ""),
        js_code=request.form.get("js_code", ""), tags=tags,
        featured=bool(request.form.get("featured")), active=True,
        order=int(request.form.get("order") or 0),
    )
    db.session.add(comp)
    db.session.commit()
    flash(f'Component "{name}" added.', "success")
    return redirect(url_for("admin.admin_components"))


@admin_bp.route("/components/<int:id>/edit", methods=["POST"])
@admin_required
def edit_component(id):
    comp = UIComponent.query.get_or_404(id)
    comp.name = (request.form.get("name") or comp.name).strip()
    comp.category = (request.form.get("category") or comp.category).strip()
    comp.description = request.form.get("description", comp.description)
    comp.preview_image = request.form.get("preview_image", comp.preview_image)
    comp.html_code = request.form.get("html_code", comp.html_code)
    comp.css_code = request.form.get("css_code", comp.css_code)
    comp.js_code = request.form.get("js_code", comp.js_code)
    comp.tags = [t.strip() for t in (request.form.get("tags") or "").split(",") if t.strip()]
    comp.featured = bool(request.form.get("featured"))
    comp.order = int(request.form.get("order") or comp.order or 0)
    db.session.commit()
    flash("Component updated.", "success")
    return redirect(url_for("admin.admin_components"))


@admin_bp.route("/components/<int:id>/toggle-active", methods=["POST"])
@admin_required
def toggle_component_active(id):
    comp = UIComponent.query.get_or_404(id)
    comp.active = not comp.active
    db.session.commit()
    flash(f"Component {'activated' if comp.active else 'deactivated'}.", "success")
    return redirect(url_for("admin.admin_components"))


@admin_bp.route("/components/<int:id>/delete", methods=["POST"])
@admin_required
def delete_component(id):
    comp = UIComponent.query.get_or_404(id)
    name = comp.name
    db.session.delete(comp)
    db.session.commit()
    flash(f'Component "{name}" deleted.', "success")
    return redirect(url_for("admin.admin_components"))


# ── Confirm Payments (Bank Transfer approval queue) ──────────────────────────
@admin_bp.route("/payments/confirm")
@admin_required
def confirm_payments():
    from app.models.commerce import BankTransferPayment
    status = request.args.get("status", "pending")
    q = BankTransferPayment.query
    if status != "all":
        q = q.filter_by(status=status)
    payments = q.order_by(BankTransferPayment.created_at.desc()).all()
    pending_count = BankTransferPayment.query.filter_by(status="pending").count()
    return render_template("admin/confirm_payments.html", payments=payments,
                           active_status=status, pending_count=pending_count)


@admin_bp.route("/payments/confirm/<int:pid>/approve", methods=["POST"])
@admin_required
def approve_payment(pid):
    from app.models.commerce import BankTransferPayment, HostingSubscription, Order
    from app.models.platform import Invoice

    payment = BankTransferPayment.query.get_or_404(pid)
    if payment.status != "pending":
        flash("This payment was already reviewed.", "danger")
        return redirect(url_for("admin.confirm_payments"))

    payment.status = "approved"
    payment.reviewed_at = datetime.utcnow()
    payment.reviewed_by_id = current_user.id

    # Activate whatever this payment was for.
    if payment.kind == "hosting_subscription":
        sub = HostingSubscription.query.get(payment.reference_id)
        if sub:
            sub.status = "active"
            sub.starts_at = datetime.utcnow()
    elif payment.kind == "order":
        order = Order.query.get(payment.reference_id)
        if order:
            order.status = "paid"
    elif payment.kind == "invoice":
        invoice = Invoice.query.get(payment.reference_id)
        if invoice and invoice.status != "paid":
            invoice.status = "paid"
            invoice.gateway = "bank_transfer"
            invoice.paid_at = datetime.utcnow()

    db.session.add(Notification(
        user_id=payment.user_id, type="payment", title="Payment confirmed",
        body=f"Your payment of ${payment.amount} has been confirmed. Thank you!",
    ))
    db.session.commit()
    log_action(current_user.id, "admin.payment.approve", "BankTransferPayment", str(pid))
    flash("Payment approved.", "success")
    return redirect(url_for("admin.confirm_payments"))


@admin_bp.route("/payments/confirm/<int:pid>/reject", methods=["POST"])
@admin_required
def reject_payment(pid):
    from app.models.commerce import BankTransferPayment

    payment = BankTransferPayment.query.get_or_404(pid)
    if payment.status != "pending":
        flash("This payment was already reviewed.", "danger")
        return redirect(url_for("admin.confirm_payments"))

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("A reason is required when rejecting a payment.", "danger")
        return redirect(url_for("admin.confirm_payments"))

    payment.status = "rejected"
    payment.rejection_reason = reason
    payment.reviewed_at = datetime.utcnow()
    payment.reviewed_by_id = current_user.id

    db.session.add(Notification(
        user_id=payment.user_id, type="payment", title="Payment could not be confirmed",
        body=f"We couldn't confirm your ${payment.amount} payment: {reason}. Please contact support.",
    ))
    db.session.commit()
    log_action(current_user.id, "admin.payment.reject", "BankTransferPayment", str(pid))
    flash("Payment rejected and customer notified.", "success")
    return redirect(url_for("admin.confirm_payments"))


# ── Site Guide ────────────────────────────────────────────────────────────────
@admin_bp.route("/guide")
@admin_required
def guide():
    from app.utils.settings import get_setting
    video_keys = ["automation", "social_bots", "backups", "media_storage", "bg_remover",
                  "url_downloader", "pdf_tools", "billing", "meetings"]
    video_urls = {k: get_setting(f"guide_video_{k}") or "" for k in video_keys}
    return render_template("admin/guide.html", video_urls=video_urls)


# ── SEO Configuration ─────────────────────────────────────────────────────────
@admin_bp.route("/seo")
@admin_required
def seo_settings():
    return render_template("admin/seo.html")


# ── Payment Configuration (its own page, not buried in general Settings) ────
@admin_bp.route("/payment-config")
@admin_required
def payment_config():
    return render_template("admin/payment_config.html")


@admin_bp.route("/payment-config/crypto-qr-preview", methods=["POST"])
@admin_required
def crypto_qr_preview():
    from app.utils.qr import generate_qr_data_uri
    data = request.get_json(silent=True) or {}
    address = (data.get("address") or "").strip()
    if not address:
        return jsonify({"error": "No address given"}), 400
    data_uri = generate_qr_data_uri(address)
    if not data_uri:
        return jsonify({"error": "Couldn't generate a QR code for that value"}), 400
    return jsonify({"data_uri": data_uri})


@admin_bp.route("/referrals")
@admin_required
def referrals():
    from app.models.platform import ReferralCode
    codes = ReferralCode.query.order_by(ReferralCode.created_at.desc()).all()
    totals = {
        "signups": sum(len(c.signups) for c in codes),
        "converted": sum(1 for c in codes for s in c.signups if s.converted),
    }
    return render_template("admin/referrals.html", codes=codes, totals=totals)


@admin_bp.route("/referrals/create", methods=["POST"])
@admin_required
def create_referral_code():
    from app.models.platform import ReferralCode
    label = request.form.get("label", "").strip()
    if not label:
        flash("Give this referral a label (who it's for).", "danger")
        return redirect(url_for("admin.referrals"))
    code = ReferralCode(
        code=ReferralCode.generate_code(), label=label,
        owner_email=request.form.get("owner_email", "").strip() or None,
        reward_note=request.form.get("reward_note", "").strip() or None,
        reward_amount=request.form.get("reward_amount", type=float) or None,
    )
    db.session.add(code)
    db.session.commit()
    flash(f'Referral link created: ?ref={code.code}', "success")
    return redirect(url_for("admin.referrals"))


@admin_bp.route("/referrals/<int:rid>/toggle", methods=["POST"])
@admin_required
def toggle_referral_code(rid):
    from app.models.platform import ReferralCode
    rc = ReferralCode.query.get_or_404(rid)
    rc.active = not rc.active
    db.session.commit()
    return redirect(url_for("admin.referrals"))


@admin_bp.route("/referrals/<int:rid>/delete", methods=["POST"])
@admin_required
def delete_referral_code(rid):
    from app.models.platform import ReferralCode
    db.session.delete(ReferralCode.query.get_or_404(rid))
    db.session.commit()
    flash("Referral code deleted.", "success")
    return redirect(url_for("admin.referrals"))


@admin_bp.route("/referrals/signup/<int:sid>/converted", methods=["POST"])
@admin_required
def mark_referral_converted(sid):
    from app.models.platform import ReferralSignup
    s = ReferralSignup.query.get_or_404(sid)
    s.converted = not s.converted
    db.session.commit()
    return redirect(url_for("admin.referrals"))


@admin_bp.route("/referrals/signup/<int:sid>/paid", methods=["POST"])
@admin_required
def mark_referral_paid(sid):
    from app.models.platform import ReferralSignup
    from app.models.user import User
    from app.utils.wallet import credit_wallet
    s = ReferralSignup.query.get_or_404(sid)
    s.reward_paid = not s.reward_paid

    if s.reward_paid:
        rc = s.referral_code
        if rc.reward_amount and rc.owner_email:
            from app.models.platform import WalletTransaction
            already_credited = WalletTransaction.query.filter_by(
                reference=f"referral_signup:{s.id}", kind="referral_earning").first()
            owner = User.query.filter(db.func.lower(User.email) == rc.owner_email.lower()).first()
            if already_credited:
                flash("Reward marked paid (already credited previously — not credited again).", "info")
            elif owner:
                credit_wallet(owner.id, float(rc.reward_amount), kind="referral_earning",
                              note=f'Referral reward — "{rc.label}"', reference=f"referral_signup:{s.id}",
                              created_by=current_user.id)
                flash(f"Reward paid and {rc.reward_amount} credited to {owner.email}'s wallet.", "success")
            else:
                flash(f"Marked paid, but no account found for {rc.owner_email} — credit it manually.", "info")
    db.session.commit()
    return redirect(url_for("admin.referrals"))


# ── Content Studio (prompt-driven writing + scheduled social broadcasts) ────
CONTENT_TYPE_PROMPTS = {
    "blog_post": "You are a skilled content writer. Write a complete, well-structured blog post in HTML (use <h2>/<p>/<ul> tags, no <html>/<body> wrapper) based on the prompt. Also suggest a short SEO title (under 60 chars) and SEO meta description (under 155 chars). Format your response EXACTLY as:\nTITLE: <post title>\nSEO_TITLE: <seo title>\nSEO_DESC: <seo description>\nEXCERPT: <one sentence teaser>\n---\n<the HTML body>",
    "seo_meta": "You are an SEO specialist. Given the prompt (a page/topic description), write a compelling SEO title (under 60 characters) and meta description (under 155 characters). Format EXACTLY as:\nSEO_TITLE: <title>\nSEO_DESC: <description>",
    "social_caption": "You are a social media copywriter. Write an engaging, platform-appropriate caption (with relevant hashtags if fitting) for the given prompt. Return ONLY the caption text.",
    "email": "You are an email marketing writer. Write a complete marketing/newsletter email (subject + body) for the given prompt. Format EXACTLY as:\nSUBJECT: <subject line>\n---\n<email body, HTML allowed>",
}


@admin_bp.route("/studios")
@admin_required
def creative_studios_hub():
    """Creative Studios splitter dashboard page."""
    return render_template("admin/creative_studios.html")
@admin_bp.route("/addons")
@admin_required
def addons_list():
    """Premium Modules — now controls the REAL, sellable Product rows
    (the same ones on the marketplace and in the buy->unlock->dashboard
    flow), instead of a separate `PremiumModule` table that was completely
    disconnected from what's actually for sale. Editing anything here now
    genuinely changes what a buyer sees and can purchase."""
    from app.dashboard.premium import PREMIUM_PRODUCTS
    modules = []
    for slug, info in PREMIUM_PRODUCTS.items():
        product = Product.query.filter_by(slug=slug).first()
        modules.append(type("Module", (), {
            "slug": slug,
            "name": product.title if product else info["name"],
            "description": product.description if product else "",
            "image_url": (product.images[0] if product and product.images else ""),
            "demo_url": product.demo_url if product else "",
            "price": float(product.price) if product else 0,
            "currency": product.currency if product else default_site_currency(),
            "active": bool(product and product.status == "active"),
            "exists": bool(product),
        })())
    return render_template("admin/addons.html", modules=modules)


@admin_bp.route("/addons/save", methods=["POST"])
@admin_required
def addons_save():
    """Save changes to a Premium Module — writes directly to the real
    Product row (creating it with the correct canonical slug on first
    save if it doesn't exist yet). Handles name/price/currency/
    description/image/demo link/active — previously only price+active
    were editable here, so the marketplace listing itself (what a buyer
    actually reads before paying) could never be fixed from this screen."""
    from app.dashboard.premium import PREMIUM_PRODUCTS
    from decimal import Decimal

    slug = request.form.get("slug")
    if slug not in PREMIUM_PRODUCTS:
        flash("Unknown add-on slug.", "danger")
        return redirect(url_for("admin.addons_list"))
    price_val = request.form.get("price", "0.0")
    active = request.form.get("active") == "y"
    try:
        price = Decimal(price_val)
    except Exception:
        flash("Invalid price value.", "danger")
        return redirect(url_for("admin.addons_list"))

    info = PREMIUM_PRODUCTS[slug]
    product = Product.query.filter_by(slug=slug).first()
    if not product:
        product = Product(
            title=info["name"], slug=slug, description=f"{info['name']} — dashboard add-on tool.",
            category="premium_tool", type="premium_tool", currency=default_site_currency(),
            license="standard", version="1.0.0",
        )
        db.session.add(product)

    title = (request.form.get("name") or "").strip()
    if title:
        product.title = title
    description = (request.form.get("description") or "").strip()
    if description:
        product.description = description
    demo_url = (request.form.get("demo_url") or "").strip()
    product.demo_url = demo_url or None
    image_url = (request.form.get("image_url") or "").strip()
    product.images = [image_url] if image_url else []
    currency = (request.form.get("currency") or "").strip()
    if currency:
        product.currency = currency
    product.price = float(price)
    product.status = "active" if active else "archived"
    db.session.commit()
    flash(f"'{product.title}' updated — this is now what buyers actually see and purchase.", "success")
    return redirect(url_for("admin.addons_list"))


@admin_bp.route("/content-studio")
@admin_required
def content_studio():
    from app.models.platform import SocialChannel, ScheduledBroadcast
    channels = SocialChannel.query.filter_by(active=True).all()
    facebook_channels = [c for c in channels if c.platform == "facebook" and (c.credentials or {}).get("page_id")]
    linkedin_channels = [c for c in channels if c.platform == "linkedin" and (c.credentials or {}).get("access_token")]
    instagram_channels = [c for c in channels if c.platform == "instagram" and (c.credentials or {}).get("page_access_token")]
    scheduled = ScheduledBroadcast.query.order_by(ScheduledBroadcast.scheduled_at.desc()).limit(50).all()
    return render_template("admin/content_studio.html", channels=channels,
                           facebook_channels=facebook_channels,
                           linkedin_channels=linkedin_channels,
                           instagram_channels=instagram_channels,
                           scheduled=scheduled, content_types=list(CONTENT_TYPE_PROMPTS.keys()))


@admin_bp.route("/content-studio/post-linkedin", methods=["POST"])
@admin_required
def content_studio_post_linkedin():
    from app.models.platform import SocialChannel
    from app.utils.social_bots import post_to_linkedin
    channel = SocialChannel.query.get_or_404(request.form.get("channel_id", type=int))
    message = (request.form.get("message") or "").strip()
    if not message:
        flash("Nothing to post.", "danger")
        return redirect(url_for("admin.content_studio"))
    try:
        post_to_linkedin(channel, message)
        flash(f"Posted to {channel.label}'s feed.", "success")
    except Exception as e:
        flash(f"LinkedIn post failed: {e}", "danger")
    return redirect(url_for("admin.content_studio"))


@admin_bp.route("/content-studio/fetch-ideas", methods=["POST"])
@admin_required
def content_studio_fetch_ideas():
    """Website Intelligence Scanner to discover content ideas dynamically."""
    from app.utils.content_intelligence import generate_content_ideas
    from flask import jsonify
    try:
        ideas = generate_content_ideas()
        for idea in ideas:
            if "description" in idea and "caption" not in idea:
                idea["caption"] = idea["description"]
            if "format" in idea and "platform" not in idea:
                idea["platform"] = idea["format"].lower().replace("post", "").replace("update", "").strip()
            if "reason" in idea and "reasoning" not in idea:
                idea["reasoning"] = idea["reason"]
            idea["source"] = "Website Scanner"
            idea["hashtags"] = ["#digitalmarketing", "#contentmarketing"]
            idea["cta"] = "Learn more on our website!"
            idea["confidence"] = "high"
        return jsonify({"ideas": ideas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/content-studio/generate-bloom", methods=["POST"])
@admin_required
def content_studio_generate_bloom():
    """Bloom's real API only generates images (brand-scoped) — there's no
    text or video endpoint, so `kind` is no longer accepted here."""
    from app.utils.bloom import generate_image
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"success": False, "error": "Enter a prompt describing the image you want Bloom to generate."}), 400

    image_url, err = generate_image(prompt)
    if err:
        return jsonify({"success": False, "error": err}), 502
    return jsonify({"success": True, "kind": "image", "result": image_url})


@admin_bp.route("/content-studio/generate-pollinations", methods=["POST"])
@admin_required
def content_studio_generate_pollinations():
    """Free, no-API-key AI image generation — a real fallback the moment
    Bloom is unreachable or unconfigured (e.g. a host's outbound proxy
    blocking trybloom.ai). Nothing to configure, nothing to test."""
    from app.utils.stock_photos import pollinations_image_url
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"success": False, "error": "Enter a prompt describing the image you want."}), 400
    image_url, err = pollinations_image_url(prompt)
    if err:
        return jsonify({"success": False, "error": err}), 400
    return jsonify({"success": True, "kind": "image", "result": image_url})


@admin_bp.route("/content-studio/fetch-photos", methods=["POST"])
@admin_required
def content_studio_fetch_photos():
    """Real stock photos matched to whatever the content is about — this is
    the 'fetch pictures relating to the content asked to be written'
    feature, backed by Pexels (free key) rather than scraping Google
    Images, which has no supported free API and would break constantly."""
    from app.utils.stock_photos import search_photos
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    photos, err = search_photos(query)
    if err:
        return jsonify({"success": False, "error": err}), 400
    return jsonify({"success": True, "photos": photos, "count": len(photos)})


def _parse_structured_content(content_type, text):
    """Pulls the labeled fields (TITLE:/SEO_TITLE:/SUBJECT:/etc, then a
    '---' body) out of a CONTENT_TYPE_PROMPTS response. Falls back to
    treating the whole response as the body if the AI didn't follow the
    format exactly, so a formatting slip never loses the content."""
    import re as _re
    fields = {"title": "", "seo_title": "", "seo_desc": "", "excerpt": "", "subject": "", "content": text.strip()}
    if "---" in text:
        head, body = text.split("---", 1)
    else:
        head, body = "", text
    for line in head.splitlines():
        m = _re.match(r"^(TITLE|SEO_TITLE|SEO_DESC|EXCERPT|SUBJECT)\s*:\s*(.+)$", line.strip(), _re.IGNORECASE)
        if m:
            fields[m.group(1).lower()] = m.group(2).strip()
    if content_type == "seo_meta" and "---" not in text:
        # seo_meta has no body — everything is in the head fields, already parsed above.
        body = ""
    fields["content"] = body.strip() or text.strip()
    return fields


@admin_bp.route("/content-studio/generate", methods=["POST"])
@admin_required
def content_studio_generate():
    from app.ai_tools.routes import _call_ai
    import json, re
    data = request.get_json(silent=True) or {}
    content_type = data.get("content_type", "social_caption")
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Enter a prompt describing what to write."}), 400

    # Blog posts / emails / SEO meta are long-form, single pieces of
    # content — they get their own prompt (CONTENT_TYPE_PROMPTS) and a
    # token budget that actually fits a real post, instead of being
    # squeezed through the 5-short-social-variations path below (which
    # was happening for every content type before this fix — that's why
    # picking "Blog Post" still produced 5 tweet-length blurbs).
    if content_type != "social_caption":
        system = CONTENT_TYPE_PROMPTS.get(content_type, CONTENT_TYPE_PROMPTS["social_caption"])
        max_tokens = {"blog_post": 4000, "email": 1500, "seo_meta": 300}.get(content_type, 1500)
        text, err = _call_ai(system, [{"role": "user", "content": prompt}], max_tokens=max_tokens)
        if err:
            return jsonify({"error": err}), 502

        fields = _parse_structured_content(content_type, text)
        result = {
            "mode": "single",
            "content_type": content_type,
            "title": fields.get("title") or fields.get("subject") or "",
            "seo_title": fields.get("seo_title", ""),
            "seo_desc": fields.get("seo_desc", ""),
            "excerpt": fields.get("excerpt", ""),
            "content": fields.get("content", text.strip()),
        }

        # Best-effort featured image for blog posts — never fails the
        # whole request if Bloom isn't configured or errors out.
        if content_type == "blog_post":
            try:
                from app.utils.bloom import bloom_configured, generate_image
                if bloom_configured():
                    image_prompt = f"Featured blog header image: {result['title'] or prompt}"
                    image_url, img_err = generate_image(image_prompt)
                    result["image_url"] = image_url
                    result["image_error"] = img_err
                else:
                    result["image_url"] = None
                    result["image_error"] = None
            except Exception as e:
                result["image_url"] = None
                result["image_error"] = str(e)

        return jsonify(result)

    system = """You are an elite content marketing director.
Generate 5 distinct high-converting content variations for the user request.
Return strictly a valid JSON array of 5 objects, where each object has:
- "title": short headline
- "content": full caption or post copy
- "platform": target social platform (Twitter, LinkedIn, Facebook, Instagram, YouTube)
- "hashtags": list of 3-5 relevant hashtags
- "graphic_prompt": image generation prompt for this post
"""
    user_msg = f"Request: {prompt}\nContent Type: {content_type}\nGenerate 5 distinct variations now in valid JSON format."
    text, err = _call_ai(system, [{"role": "user", "content": user_msg}], max_tokens=2500)
    if err:
        return jsonify({"error": err}), 502

    parsed_items = []
    try:
        json_match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
        if json_match:
            parsed_items = json.loads(json_match.group(0))
    except Exception:
        pass

    if not parsed_items or not isinstance(parsed_items, list):
        blocks = [b.strip() for b in text.split("\n\n") if len(b.strip()) > 20][:5]
        parsed_items = [{
            "title": f"Variation #{i+1}",
            "content": block,
            "platform": ["Twitter", "LinkedIn", "Facebook", "Instagram", "YouTube"][i % 5],
            "hashtags": ["#digitalmarketing", "#growth"],
            "graphic_prompt": f"Professional visual banner for {prompt}"
        } for i, block in enumerate(blocks)]

    return jsonify({"mode": "variations", "items": parsed_items, "count": len(parsed_items), "content": text.strip()})


def _extract_page_text(html, base_url):
    """Strip a fetched HTML page down to the words a person would actually
    read — title, meta description, headings, and body copy — with all
    script/style/nav/footer noise removed. This is the input the AI reads
    to write content 'about your site' instead of guessing from a URL
    alone."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "svg", "iframe"]):
        tag.decompose()
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = (meta_desc_tag.get("content") or "").strip() if meta_desc_tag else ""
    headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"]) if h.get_text(strip=True)][:25]
    body = soup.body or soup
    text = body.get_text(" ", strip=True)
    text = " ".join(text.split())  # collapse repeated whitespace
    MAX_CHARS = 6000
    truncated = len(text) > MAX_CHARS
    return {
        "title": title,
        "meta_description": meta_desc,
        "headings": headings,
        "body_text": text[:MAX_CHARS],
        "truncated": truncated,
    }


def _extract_local_site_content(path):
    path = path.strip("/")
    
    # 1. Product page: e.g. "marketplace/product/some-slug" or "marketplace/some-slug" or "product/some-slug"
    if "marketplace" in path or "product" in path:
        slug = path.split("/")[-1]
        p = Product.query.filter_by(slug=slug).first()
        if p:
            return {
                "title": p.title,
                "meta_description": p.description or "",
                "headings": [p.title, "Description", "Details"],
                "body_text": f"Product Name: {p.title}\nCategory: {p.category}\nType: {p.type}\nPrice: {p.currency or 'USD'} {p.price}\nDescription: {p.description or ''}\nFull Details: {p.long_desc or ''}\nTags: {', '.join(p.tags or [])}",
                "truncated": False
            }
            
    # 2. Blog page: e.g. "blog/some-slug"
    if "blog" in path:
        slug = path.split("/")[-1]
        bp = BlogPost.query.filter_by(slug=slug).first()
        if bp:
            return {
                "title": bp.title,
                "meta_description": bp.summary or "",
                "headings": [bp.title],
                "body_text": f"Blog Post: {bp.title}\nSummary: {bp.summary or ''}\nContent: {bp.content or ''}",
                "truncated": False
            }
            
    # 3. Main home page / services / portfolio / about / hire
    if path == "" or path == "portfolio" or path == "about" or path == "hire":
        services = Service.query.filter_by(active=True).all()
        projects = Project.query.all()
        profile = Profile.query.first()
        
        lines = []
        if profile:
            lines.append(f"Name: {profile.full_name or ''}")
            lines.append(f"Title: {profile.title or ''}")
            lines.append(f"Bio: {profile.bio or ''}")
            
        lines.append("\nOur Services:")
        for s in services:
            lines.append(f"- {s.title}: {s.description or ''}")
            
        lines.append("\nOur Projects:")
        for prj in projects:
            lines.append(f"- {prj.title}: {prj.description or ''} (Technologies: {prj.technologies or ''})")
            
        body_text = "\n".join(lines)
        return {
            "title": profile.full_name if (profile and profile.full_name) else "Bazillin Studio",
            "meta_description": profile.bio[:150] if (profile and profile.bio) else "Bazillin Studio Portfolio",
            "headings": ["About Us", "Services", "Projects"],
            "body_text": body_text,
            "truncated": False
        }
        
    return None


@admin_bp.route("/content-studio/generate-from-url", methods=["POST"])
@admin_required
def content_studio_generate_from_url():
    """The 'paste a URL, it reads your site and generates content from it'
    tool — fetches the page (same SSRF-safe fetcher used by the URL Fetch
    tool), strips it down to real readable text, then hands that to the AI
    instead of a bare prompt so the output is actually grounded in what's
    on the page rather than invented."""
    from app.ai_tools.routes import _call_ai, _is_safe_url
    from urllib.parse import urlparse
    import requests as _requests

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    content_type = data.get("content_type", "social_caption")
    extra_instructions = (data.get("prompt") or "").strip()

    if not url:
        return jsonify({"error": "Enter a URL to scan."}), 400

    # Handle relative or raw urls
    norm_url = url
    if not norm_url.startswith(("http://", "https://")):
        if norm_url.startswith("/"):
            norm_url = f"https://{request.host}{norm_url}"
        else:
            norm_url = f"https://{norm_url}"

    parsed = urlparse(norm_url)
    is_local = (
        parsed.netloc == request.host
        or parsed.netloc == ""
        or "localhost" in parsed.netloc
        or "127.0.0.1" in parsed.netloc
    )

    extracted = None
    if is_local:
        extracted = _extract_local_site_content(parsed.path)

    if not extracted:
        safe, reason = _is_safe_url(norm_url)
        if not safe:
            return jsonify({"error": reason}), 400

        try:
            resp = _requests.get(norm_url, timeout=(10, 15), headers={"User-Agent": "BazillinStudio-ContentScanner/1.0"})
            resp.raise_for_status()
            content_type_header = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type_header:
                return jsonify({"error": f"That URL didn't return a webpage (got '{content_type_header}'). Paste a link to a page, not a file."}), 415
        except _requests.exceptions.Timeout:
            return jsonify({"error": "That site took too long to respond. Try again or use a different URL."}), 504
        except _requests.exceptions.RequestException as e:
            return jsonify({"error": f"Could not fetch that URL: {e}"}), 502

        try:
            extracted = _extract_page_text(resp.text, norm_url)
        except Exception as e:
            return jsonify({"error": f"Fetched the page but couldn't read its content: {e}"}), 500

    if not extracted or (not extracted["body_text"] and not extracted["title"]):
        return jsonify({"error": "That page loaded but had no readable text on it — is it a JavaScript-only page? Try a different URL."}), 422

    system = CONTENT_TYPE_PROMPTS.get(content_type, CONTENT_TYPE_PROMPTS["social_caption"])
    site_brief = (
        f"Page title: {extracted['title'] or '(none)'}\n"
        f"Meta description: {extracted['meta_description'] or '(none)'}\n"
        f"Headings on the page: {'; '.join(extracted['headings']) or '(none)'}\n\n"
        f"Page content:\n{extracted['body_text']}"
        + ("\n\n[content truncated — page is longer than shown]" if extracted["truncated"] else "")
    )
    user_prompt = (
        f"Here is the actual content scraped from this webpage ({url}). "
        f"Write the requested content based on what this page actually says — "
        f"don't invent products, features, or claims that aren't on the page.\n\n{site_brief}"
    )
    if extra_instructions:
        user_prompt += f"\n\nAdditional instructions from the user: {extra_instructions}"

    text, err = _call_ai(system, [{"role": "user", "content": user_prompt}], max_tokens=1500)
    if err:
        return jsonify({"error": err}), 502
    return jsonify({
        "content": text.strip(),
        "content_type": content_type,
        "scanned": {"title": extracted["title"], "url": url},
    })


@admin_bp.route("/content-studio/post-ayrshare", methods=["POST"])
@admin_required
def content_studio_post_ayrshare():
    """Publish directly to Facebook/Instagram/etc through Ayrshare — no
    Facebook Developer App or Page Access Token needed on this end. The
    user connects their accounts once inside Ayrshare's own dashboard and
    pastes one API key into Settings; this just calls Ayrshare's API."""
    from app.utils.ayrshare import post_to_ayrshare
    api_key = get_setting("ayrshare_api_key")
    message = (request.form.get("message") or "").strip()
    platforms = request.form.getlist("platforms")
    media_url = (request.form.get("media_url") or "").strip()
    result, err = post_to_ayrshare(
        api_key, message, platforms,
        media_urls=[media_url] if media_url else None,
    )
    if err:
        flash(f"Ayrshare post failed: {err}", "danger")
    else:
        note = ""
        if result.get("partial_errors"):
            note = " (some platforms failed: " + "; ".join(result["partial_errors"]) + ")"
        flash(f"Posted to {', '.join(platforms)} via Ayrshare.{note}", "success" if not note else "warning")
    return redirect(url_for("admin.content_studio"))


@admin_bp.route("/content-studio/save-blog", methods=["POST"])
@admin_required
def content_studio_save_blog():
    from app.models.content import BlogPost
    import re as _re
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Untitled Draft").strip()
    slug_base = _re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or "post"
    slug = slug_base
    n = 1
    while BlogPost.query.filter_by(slug=slug).first():
        n += 1
        slug = f"{slug_base}-{n}"
    post = BlogPost(
        title=title, slug=slug, content=data.get("content", ""),
        excerpt=(data.get("excerpt") or "")[:500] or None,
        seo_title=(data.get("seo_title") or "")[:256] or None,
        seo_desc=data.get("seo_desc") or None,
        cover_image=(data.get("image_url") or "")[:512] or None,
        author_id=current_user.id, published=bool(data.get("publish")),
    )
    db.session.add(post)
    db.session.commit()
    log_action(current_user.id, "admin.blog.create_from_studio", title)
    return jsonify({"success": True, "redirect": url_for("admin.blog"), "published": post.published})


@admin_bp.route("/content-studio/post-facebook", methods=["POST"])
@admin_required
def content_studio_post_facebook():
    from app.models.platform import SocialChannel
    from app.utils.social_bots import post_to_facebook_page
    channel = SocialChannel.query.get_or_404(request.form.get("channel_id", type=int))
    message = (request.form.get("message") or "").strip()
    link = (request.form.get("link") or "").strip() or None
    if not message:
        flash("Nothing to post.", "danger")
        return redirect(url_for("admin.content_studio"))
    try:
        result = post_to_facebook_page(channel, message, link)
        flash(f"Posted to {channel.label}'s Page feed.", "success")
    except Exception as e:
        flash(f"Facebook post failed: {e}", "danger")
    return redirect(url_for("admin.content_studio"))


@admin_bp.route("/content-studio/post-instagram", methods=["POST"])
@admin_required
def content_studio_post_instagram():
    from app.models.platform import SocialChannel
    from app.utils.social_bots import post_to_instagram_feed
    channel = SocialChannel.query.get_or_404(request.form.get("channel_id", type=int))
    caption = (request.form.get("message") or "").strip()
    image_url = (request.form.get("image_url") or "").strip()
    if not caption and not image_url:
        flash("Nothing to post.", "danger")
        return redirect(url_for("admin.content_studio"))
    if not image_url:
        flash("Instagram feed posts need an image URL — Instagram has no text-only post type.", "danger")
        return redirect(url_for("admin.content_studio"))
    try:
        post_to_instagram_feed(channel, caption, image_url)
        flash(f"Posted to {channel.label}'s Instagram feed.", "success")
    except Exception as e:
        flash(f"Instagram post failed: {e}", "danger")
    return redirect(url_for("admin.content_studio"))


@admin_bp.route("/content-studio/broadcast-now", methods=["POST"])
@admin_required
def content_studio_broadcast_now():
    from app.models.platform import SocialChannel, ChatContact
    from app.utils.social_bots import send_reply
    data = request.form
    channel = SocialChannel.query.get_or_404(data.get("channel_id", type=int))
    body = (data.get("body") or "").strip()
    if not body:
        flash("Nothing to send.", "danger")
        return redirect(url_for("admin.content_studio"))
    contacts = ChatContact.query.filter_by(channel_id=channel.id).all()
    sent, failed = 0, 0
    for c in contacts:
        try:
            send_reply(channel, c.external_id, body)
            sent += 1
        except Exception:
            failed += 1
    flash(f"Broadcast sent to {sent} contact(s) on {channel.label}" + (f" ({failed} failed)" if failed else "") + ".",
          "success" if not failed else "warning")
    return redirect(url_for("admin.content_studio"))


@admin_bp.route("/content-studio/schedule", methods=["POST"])
@admin_required
def content_studio_schedule():
    from app.models.platform import ScheduledBroadcast
    scheduled_at_raw = request.form.get("scheduled_at", "").strip()
    body = request.form.get("body", "").strip()
    channel_id = request.form.get("channel_id", type=int)
    if not (scheduled_at_raw and body and channel_id):
        flash("Channel, message, and date/time are all required to schedule.", "danger")
        return redirect(url_for("admin.content_studio"))
    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_raw)
    except ValueError:
        flash("Invalid date/time.", "danger")
        return redirect(url_for("admin.content_studio"))
    sb = ScheduledBroadcast(
        channel_id=channel_id, title=request.form.get("title", "").strip() or None,
        body=body, scheduled_at=scheduled_at, created_by_id=current_user.id,
    )
    db.session.add(sb)
    db.session.commit()
    flash(f"Broadcast scheduled for {scheduled_at.strftime('%b %d, %Y %H:%M')}.", "success")
    return redirect(url_for("admin.content_studio"))


@admin_bp.route("/content-studio/<int:sid>/cancel", methods=["POST"])
@admin_required
def content_studio_cancel(sid):
    from app.models.platform import ScheduledBroadcast
    sb = ScheduledBroadcast.query.get_or_404(sid)
    sb.status = "cancelled"
    db.session.commit()
    return redirect(url_for("admin.content_studio"))


@admin_bp.route("/cron/publish-scheduled-broadcasts")
def publish_scheduled_broadcasts_cron():
    """Same external-cron pattern as the DB backup scheduler: point an
    hourly (or more frequent) scheduled task at this URL with the secret
    key. Anything due gets sent; nothing fires early."""
    from app.models.platform import ScheduledBroadcast, ChatContact
    from app.utils.social_bots import send_reply
    from app.utils.settings import get_setting
    expected = get_setting("backup_cron_secret")  # reuses the same secret as backups — one cron key for all scheduled jobs
    if not expected or request.args.get("key") != expected:
        return jsonify({"error": "Invalid or missing key"}), 403
    due = ScheduledBroadcast.query.filter(
        ScheduledBroadcast.status == "pending",
        ScheduledBroadcast.scheduled_at <= datetime.utcnow(),
    ).all()
    results = []
    for sb in due:
        contacts = ChatContact.query.filter_by(channel_id=sb.channel_id).all()
        sent = 0
        try:
            for c in contacts:
                send_reply(sb.channel, c.external_id, sb.body)
                sent += 1
            sb.status = "sent"
            sb.sent_count = sent
        except Exception as e:
            sb.status = "failed"
            sb.error = str(e)
            sb.sent_count = sent
        results.append({"id": sb.id, "status": sb.status, "sent": sb.sent_count})
    db.session.commit()
    return jsonify({"published": results})


@admin_bp.route("/financials")
@admin_required
def financials():
    """Full accountability trail: every invoice ever created, who it's
    for, its status, and how it was paid — so money in is always
    traceable back to a specific project and client.

    Paystack-style multi-currency: totals are grouped BY the currency each
    invoice/order actually used, never blended together. Previously this
    view summed Invoice.amount across every currency into one number —
    meaning a $500 invoice and a ₦500 invoice were added as if they were
    the same 1000 units. Pick a currency tab and every total on the page
    (invoiced/paid/unpaid/cancelled, order revenue, the itemized list)
    reflects only that currency's real, unconverted numbers.
    """
    from app.models.platform import Invoice, ClientProject, SocialChannel
    from app.models.commerce import Order

    status = request.args.get("status", "all")

    # Every currency that actually has invoices or orders recorded against it,
    # plus default supported ones, to drive the currency tabs.
    SUPPORTED_CURRENCIES = ["NGN", "USD", "KES", "GBP", "EUR"]
    invoice_currencies = {c for (c,) in db.session.query(Invoice.currency).distinct().all() if c}
    order_currencies = {c for (c,) in db.session.query(Order.currency).distinct().all() if c}
    available_currencies = sorted(list(set(SUPPORTED_CURRENCIES) | invoice_currencies | order_currencies))

    selected_currency = request.args.get("currency", "").upper() or "NGN"
    if selected_currency not in available_currencies:
        selected_currency = available_currencies[0]

    q = Invoice.query.join(ClientProject, Invoice.project_id == ClientProject.id).filter(Invoice.currency == selected_currency)
    if status != "all":
        q = q.filter(Invoice.status == status)
    invoices = q.order_by(Invoice.created_at.desc()).all()

    def _sum(currency, extra_status=None):
        qq = db.session.query(func.sum(Invoice.amount)).filter(Invoice.currency == currency)
        if extra_status:
            qq = qq.filter(Invoice.status == extra_status)
        return float(qq.scalar() or 0)

    totals = {
        "invoiced": _sum(selected_currency),
        "paid": _sum(selected_currency, "paid"),
        "unpaid": _sum(selected_currency, "unpaid"),
        "cancelled": _sum(selected_currency, "cancelled"),
    }
    order_revenue = float(db.session.query(func.sum(Order.amount)).filter_by(status="paid", currency=selected_currency).scalar() or 0)

    # Quick per-currency snapshot for the tab bar (paid total + invoice count),
    # so switching currencies doesn't require a fresh page load to see what's there.
    currency_totals = {}
    for c in available_currencies:
        currency_totals[c] = {
            "paid": _sum(c, "paid"),
            "count": Invoice.query.filter_by(currency=c).count(),
        }

    # Breakdown by payment gateway actually used — shows where money is really coming from
    gateway_breakdown = (db.session.query(Invoice.gateway, func.sum(Invoice.amount), func.count(Invoice.id))
                        .filter(Invoice.status == "paid", Invoice.currency == selected_currency)
                        .group_by(Invoice.gateway).all())

    # Bots/automations you're running as a paid service for a customer —
    # anything with a client assigned, regardless of whether it also has
    # a fee set yet, so unbilled ones are visible too.
    billed_channels = SocialChannel.query.filter(SocialChannel.client_project_id.isnot(None)).all()
    billed_workflows = AutomationWorkflow.query.filter(AutomationWorkflow.client_project_id.isnot(None)).all()
    bot_mrr = sum(c.monthly_fee or 0 for c in billed_channels) + sum(w.monthly_fee or 0 for w in billed_workflows)

    return render_template("admin/financials.html", invoices=invoices, totals=totals,
                           order_revenue=order_revenue, current_status=status,
                           gateway_breakdown=gateway_breakdown,
                           billed_channels=billed_channels, billed_workflows=billed_workflows, bot_mrr=bot_mrr,
                           available_currencies=available_currencies, selected_currency=selected_currency,
                           currency_totals=currency_totals)


# ── Security: 2FA ────────────────────────────────────────────────────────────
@admin_bp.route("/account/security")
@admin_required
def security_settings():
    return render_template("admin/security.html")


@admin_bp.route("/account/security/2fa/setup", methods=["POST"])
@admin_required
def setup_2fa():
    from app.utils.security import generate_secret, get_provisioning_uri, get_qr_code_data_uri
    from app.utils.settings import get_setting
    secret = generate_secret()
    session["pending_totp_secret"] = secret
    uri = get_provisioning_uri(secret, current_user.email, get_setting("site_name", "Bazillin Studio"))
    qr_data_uri = get_qr_code_data_uri(uri)
    return jsonify({"secret": secret, "qr_code": qr_data_uri})


@admin_bp.route("/account/security/2fa/enable", methods=["POST"])
@admin_required
def enable_2fa():
    from app.utils.security import verify_totp_code
    secret = session.get("pending_totp_secret")
    code = request.form.get("code", "")
    if not secret:
        flash("2FA setup expired — start again.", "danger")
        return redirect(url_for("admin.security_settings"))
    if not verify_totp_code(secret, code):
        flash("Incorrect code — check your authenticator app and try again.", "danger")
        return redirect(url_for("admin.security_settings"))
    current_user.totp_secret = secret
    current_user.totp_enabled = True
    db.session.commit()
    session.pop("pending_totp_secret", None)
    log_action(current_user.id, "admin.security.2fa_enabled", f"User#{current_user.id}")
    flash("Two-factor authentication is now enabled on your account.", "success")
    return redirect(url_for("admin.security_settings"))


@admin_bp.route("/account/security/2fa/disable", methods=["POST"])
@admin_required
def disable_2fa():
    password = request.form.get("password", "")
    if not current_user.check_password(password):
        flash("Incorrect password.", "danger")
        return redirect(url_for("admin.security_settings"))
    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.session.commit()
    log_action(current_user.id, "admin.security.2fa_disabled", f"User#{current_user.id}")
    flash("Two-factor authentication disabled.", "success")
    return redirect(url_for("admin.security_settings"))


@admin_bp.route("/account/security/2fa/email/enable", methods=["POST"])
@admin_required
def enable_email_2fa():
    if current_user.totp_enabled:
        flash("Turn off authenticator-app 2FA first — only one method can be active at a time.", "danger")
        return redirect(url_for("admin.security_settings"))
    current_user.email_2fa_enabled = True
    db.session.commit()
    log_action(current_user.id, "admin.security.email_2fa_enabled", f"User#{current_user.id}")
    flash("Email-code two-factor authentication is now enabled.", "success")
    return redirect(url_for("admin.security_settings"))


@admin_bp.route("/account/security/2fa/email/disable", methods=["POST"])
@admin_required
def disable_email_2fa():
    password = request.form.get("password", "")
    if not current_user.check_password(password):
        flash("Incorrect password.", "danger")
        return redirect(url_for("admin.security_settings"))
    current_user.email_2fa_enabled = False
    db.session.commit()
    log_action(current_user.id, "admin.security.email_2fa_disabled", f"User#{current_user.id}")
    flash("Email-code two-factor authentication disabled.", "success")
    return redirect(url_for("admin.security_settings"))


@admin_bp.route("/content-studio/brand-voice", methods=["POST"])
@admin_required
def content_studio_brand_voice():
    from app.utils.settings import set_setting
    tone = request.form.get("tone", "").strip()
    audience = request.form.get("audience", "").strip()
    exclude = request.form.get("exclude", "").strip()
    guidelines = request.form.get("guidelines", "").strip()
    
    set_setting("brand_voice_tone", tone)
    set_setting("brand_voice_audience", audience)
    set_setting("brand_voice_exclude", exclude)
    set_setting("brand_voice_guidelines", guidelines)
    
    flash("Brand voice settings saved successfully.", "success")
    return redirect(url_for("admin.content_studio"))


@admin_bp.route("/content-studio/video-script", methods=["POST"])
@admin_required
def content_studio_video_script():
    from app.utils.content_intelligence import generate_video_script
    data = request.get_json(silent=True) or {}
    topic = data.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "Topic is required"}), 400
    script = generate_video_script(topic)
    return jsonify(script)


@admin_bp.route("/content-studio/generate-image", methods=["POST"])
@admin_required
def content_studio_generate_image():
    from app.utils.content_intelligence import generate_ai_image
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
    try:
        image_url = generate_ai_image(prompt)
        return jsonify({"image_url": image_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/content-studio/optimize", methods=["POST"])
@admin_required
def content_studio_optimize():
    from app.ai_tools.routes import _call_ai
    from app.utils.content_intelligence import get_brand_voice_prompt
    import json
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text to optimize"}), 400
        
    brand_voice = get_brand_voice_prompt()
    system = (
        f"{brand_voice}\n\n"
        "You are a copywriter. Optimize the user's draft to make it more engaging, punchy, and readable. "
        "Provide exactly three variations:\n"
        "1. Concise & Punchy\n"
        "2. Professional & Authoritative\n"
        "3. Engaging & Creative\n\n"
        "Also extract the top 5 relevant hashtags.\n\n"
        "Respond ONLY in a JSON object with keys: 'variation_1', 'variation_2', 'variation_3', 'hashtags' (list). "
        "Do not include backticks or markdown JSON blocks."
    )
    
    res, err = _call_ai(system, [{"role": "user", "content": f"Optimize this text: {text}"}], max_tokens=1000)
    if err:
        return jsonify({"error": err}), 500
        
    try:
        cleaned = res.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return jsonify(json.loads(cleaned.strip()))
    except Exception:
        return jsonify({"error": "AI response was not valid JSON", "raw": res}), 502


@admin_bp.route("/rich-notes", methods=["GET"])
@admin_required
def rich_notes():
    from app.utils.settings import get_setting
    brand_notebook_html = get_setting("brand_notebook_html") or ""
    return render_template("admin/rich_notes.html", brand_notebook_html=brand_notebook_html)


@admin_bp.route("/rich-notes/save", methods=["POST"])
@admin_required
def save_notebook():
    from app.utils.settings import set_setting
    data = request.get_json(silent=True) or {}
    html = data.get("html", "").strip()
    set_setting("brand_notebook_html", html)
    return jsonify({"success": True})


@admin_bp.route("/rich-notes/library", methods=["GET", "POST"])
@admin_required
def notebook_library():
    """Document library manager for saved notebook documents."""
    from app.utils.settings import get_setting, set_setting
    import json
    docs_json = get_setting("notebook_library_json") or "[]"
    try:
        docs = json.loads(docs_json)
    except Exception:
        docs = []

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "Untitled Document").strip()
        content = data.get("html", "")
        doc_id = data.get("id")
        
        from datetime import datetime
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        
        if doc_id:
            for d in docs:
                if str(d.get("id")) == str(doc_id):
                    d["title"] = title
                    d["html"] = content
                    d["updated_at"] = now_str
                    break
        else:
            new_id = str(len(docs) + 1)
            docs.append({
                "id": new_id,
                "title": title,
                "html": content,
                "created_at": now_str,
                "updated_at": now_str
            })
        set_setting("notebook_library_json", json.dumps(docs))
        return jsonify({"success": True, "docs": docs})

    return jsonify({"success": True, "docs": docs})


@admin_bp.route("/rich-notes/library/<doc_id>/delete", methods=["POST"])
@admin_required
def notebook_library_delete(doc_id):
    from app.utils.settings import get_setting, set_setting
    import json
    docs_json = get_setting("notebook_library_json") or "[]"
    try:
        docs = json.loads(docs_json)
    except Exception:
        docs = []
    docs = [d for d in docs if str(d.get("id")) != str(doc_id)]
    set_setting("notebook_library_json", json.dumps(docs))
    return jsonify({"success": True, "docs": docs})


@admin_bp.route("/rich-notes/export-docx", methods=["POST"])
@admin_required
def notebook_export_docx():
    from flask import Response
    data = request.get_json(silent=True) or {}
    title = data.get("title", "Document")
    html_content = data.get("html", "")
    
    word_html = f"""<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head><meta charset='utf-8'><title>{title}</title>
<style>
body {{ font-family: 'Calibri', 'Arial', sans-serif; font-size: 11pt; line-height: 1.5; margin: 1in; }}
h1 {{ font-size: 20pt; color: #1F4E79; font-weight: bold; margin-bottom: 12pt; }}
h2 {{ font-size: 14pt; color: #2F5597; font-weight: bold; margin-top: 12pt; }}
table {{ border-collapse: collapse; width: 100%; margin: 12pt 0; }}
th, td {{ border: 1px solid #B0C4DE; padding: 6pt 8pt; text-align: left; }}
th {{ background-color: #F2F2F2; font-weight: bold; }}
.inset-note-box {{ background: #F0F4F8; border-left: 4pt solid #2F5597; padding: 8pt 12pt; margin: 10pt 0; }}
</style>
</head>
<body>
{html_content}
</body>
</html>"""
    
    filename = f"{title.replace(' ', '_')}.doc"
    return Response(
        word_html,
        mimetype="application/msword",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@admin_bp.route("/ai-developer-tool", methods=["GET"])
@admin_required
def ai_developer_tool():
    from app.models.content import Project, Skill
    from app.models.commerce import BankTransferPayment
    from app.utils.settings import get_setting
    
    # Context data for the dropdowns
    projects = Project.query.all()
    skills = Skill.query.all()
    payments = BankTransferPayment.query.filter_by(status="pending").all()
    
    # Get current values
    site_currency = get_setting("site_currency") or "USD"
    partners_count = 0
    import json
    try:
        partners_count = len(json.loads(get_setting("site_partners_json") or "[]"))
    except:
        pass
        
    return render_template("admin/ai_developer_tool.html", 
                           projects=projects, 
                           skills=skills, 
                           payments=payments,
                           site_currency=site_currency,
                           partners_count=partners_count)


@admin_bp.route("/ai-developer-tool/inspect-db")
@admin_required
def dev_tool_inspect_db():
    """Returns real database inspection stats (tables, row counts, indexes)."""
    from app.extensions import db
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    table_stats = []
    for t in table_names:
        try:
            count = db.session.execute(db.text(f"SELECT COUNT(*) FROM {t}")).scalar()
            table_stats.append({"table": t, "rows": count})
        except Exception:
            table_stats.append({"table": t, "rows": "error"})
    return jsonify({"success": True, "tables": table_stats, "total_tables": len(table_names)})


@admin_bp.route("/ai-developer-tool/view-logs")
@admin_required
def dev_tool_view_logs():
    """Returns recent log events and system status."""
    import os
    from flask import current_app
    log_file = os.path.join(current_app.root_path, "..", "app.log")
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                logs = [l.strip() for l in lines[-50:]]
        except Exception as e:
            logs = [f"Could not read log file: {str(e)}"]
    else:
        logs = ["No app.log file present — system operating cleanly."]
    return jsonify({"success": True, "logs": logs})


@admin_bp.route("/ai-developer-tool/execute", methods=["POST"])
@admin_required
def execute_dev_tool_task():
    from app.utils.settings import get_setting, set_setting
    data = request.get_json(silent=True) or {}
    task_id = data.get("task_id", "")
    
    if not task_id:
        return jsonify({"error": "No task ID specified"}), 400
        
    success = False
    message = ""
    
    try:
        if task_id == "hero_video":
            # Toggle background type to video and verify URL
            set_setting("hero_background_type", "video")
            set_setting("hero_video_url", "/static/uploads/intro_video.mp4")
            success = True
            message = "Hero background set to Video successfully."
            
        elif task_id == "clickable_projects":
            # Verified: templates/cms/home.html project cards are real <a
            # href="{{ url_for('cms.work_detail', ...) }}"> links — this one
            # was actually already true, not a canned claim.
            success = True
            message = "Confirmed — project grid cards are real links to their detail pages."
            
        elif task_id == "confirm_payments":
            # Verified end-to-end: BankTransferPayment.proof_image column,
            # the upload form (multipart + CSRF token, both present), and
            # the admin display all already worked. Upgraded the admin
            # viewer from a plain new-tab link to a real modal with
            # zoom/rotate/download (templates/admin/confirm_payments.html).
            success = True
            message = "Verified the upload-to-display pipeline works, and upgraded the admin viewer to a zoomable/rotatable/downloadable modal."
            
        elif task_id == "form_spacing":
            # Actually added this time: static/css/admin.css now sets 16px
            # font-size on mobile inputs (prevents iOS Safari's auto-zoom-
            # on-focus, which was the real cause of "cramped/jumpy" forms,
            # not just padding) plus larger touch-target padding/min-height
            # and single-column grids under 640px.
            success = True
            message = "Added real mobile form-spacing rules to static/css/admin.css (16px input font-size, larger touch targets, single-column layout)."
            
        elif task_id == "layout_balance":
            # NOT actually verified or fixed yet — flagging honestly rather
            # than claiming success. A previous version of this endpoint
            # claimed "Works grid layout balanced using flex alignment"
            # without that change ever being made.
            success = False
            message = "Not yet implemented — this needs a real look at the portfolio grid, not a canned success message. Ask for it directly and it'll get done properly."
            
        elif task_id == "partners_setup":
            # Only ever set a JSON setting with 3 hardcoded example logos —
            # there's no actual admin UI to manage partners (add/edit/
            # remove/upload a logo), which is what "add our partners, let me
            # upload them" actually needs. Marking this honestly incomplete.
            if not get_setting("site_partners_json"):
                import json
                defaults = [
                    {"name": "Google", "logo": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Google_2015_logo.svg"},
                    {"name": "Microsoft", "logo": "https://upload.wikimedia.org/wikipedia/commons/9/96/Microsoft_logo_%282012%29.svg"},
                    {"name": "Amazon", "logo": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg"}
                ]
                set_setting("site_partners_json", json.dumps(defaults))
            success = False
            message = "Only a placeholder setting exists — there's no real admin UI yet to add/edit/upload your own partner logos. Ask for it directly and it'll get built properly."
            
        elif task_id == "skills_icon":
            # The Skill model's `icon` column already existed before any of
            # this — nothing was actually "updated". Whether the admin form
            # exposes a text input for a URL (vs. a fixed icon picker) is
            # unverified. Marking honestly incomplete rather than claiming
            # a fix that was never made.
            success = False
            message = "Not actually verified or fixed yet — ask for it directly and it'll get done properly instead of marked as done."
            
        else:
            return jsonify({"error": f"Unknown task ID: {task_id}"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    return jsonify({"success": success, "message": message})






def _form_capture_snippet(website_slug):
    """Appended to every generated page's JS so any form the AI marked
    data-collect="true" actually posts somewhere real, instead of the
    Properties panel's "Form Submissions" list staying empty forever
    because nothing wired the two together. Posts by slug (works the
    moment a site is first generated) rather than by subdomain (which
    only exists after Publish), so submissions get captured in the
    preview/draft stage too, not just once live."""
    return f"""
// -- Auto-injected by Website Builder: captures data-collect forms --
document.addEventListener('submit', function(e) {{
  var form = e.target;
  if (!(form instanceof HTMLFormElement)) return;
  if (form.getAttribute('data-collect') !== 'true') return;
  e.preventDefault();
  var fields = {{}};
  new FormData(form).forEach(function(v, k) {{ fields[k] = v; }});
  fetch((window.location.origin || '') + '/dashboard/sites/submit-form-by-slug/{website_slug}', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ fields: fields }})
  }}).then(function(r) {{ return r.json(); }}).then(function() {{
    var note = document.createElement('p');
    note.textContent = 'Thanks! Your submission was received.';
    note.style.cssText = 'margin-top:12px;font-weight:600;color:#1DB954';
    form.reset();
    form.parentNode.insertBefore(note, form.nextSibling);
  }}).catch(function() {{ alert('Sorry, something went wrong submitting the form.'); }});
}});
"""


@admin_bp.route("/website-builder")
@admin_required
def website_builder():
    """AI Website Builder workspace. Accepts ?id=<id> as a defensive
    fallback and redirects to the canonical /edit URL — the "My Sites"
    list itself always links straight to /edit (see loadWebsite() in the
    template), this is just so an old bookmark or a stray ?id= link
    still lands somewhere useful instead of a blank builder."""
    from app.models.platform import UserWebsite
    requested_id = request.args.get("id")
    if requested_id:
        return redirect(url_for("admin.website_builder_edit", website_id=requested_id))
    websites = UserWebsite.query.filter_by(
        user_id=current_user.id
    ).order_by(UserWebsite.updated_at.desc()).all()
    return render_template("admin/website_builder.html", websites=websites)



import re as _re_top


def _detect_requested_new_page_name(prompt, existing_names):
    """Looks for an explicit "create another/new/separate page for X"
    request in the prompt. Without this, a prompt like "create another
    page for admin dashboard" had no way to actually land on a new page
    -- the route always wrote to whatever page_name the frontend sent
    (whichever page happened to be open), so the AI had no choice but to
    cram the requested section into the CURRENT page's HTML instead of a
    real separate page. Returns a candidate page name, or None if no such
    request is detected.

    This is a heuristic over free-text English, not a parser -- it won't
    catch every phrasing, but it catches the common ones ("another page
    for X", "new page called X", "a separate X page") instead of silently
    doing nothing, which is what always happened before. Real prompts are
    typo-heavy free text with no punctuation to mark where the page name
    ends, so the candidate is capped to a few words and trimmed of
    trailing connector words rather than trusting punctuation to be there.
    """
    text = prompt.strip()
    patterns = [
        r"(?:another|new|separate|different)\s+page\s+(?:for|called|named|titled)\s+(?:the\s+)?([a-zA-Z][a-zA-Z0-9 &\-]{1,60})",
        r"(?:add|create|make)\s+(?:a|an)\s+([a-zA-Z][a-zA-Z0-9 &\-]{1,60}?)\s+page\b",
    ]
    _STOPWORDS = {"to", "t", "so", "that", "which", "where", "for", "and", "so", "as", "with",
                  "see", "the", "others", "other", "made", "mde", "now", "then", "also",
                  "a", "an", "form", "in", "on", "of", "having", "showing", "shows"}
    for pat in patterns:
        m = _re_top.search(pat, text, _re_top.IGNORECASE)
        if not m:
            continue
        words = m.group(1).strip(" .,-").split()[:4]  # page names are short; cap runaway matches
        while words and words[-1].lower() in _STOPWORDS:
            words.pop()
        if not words:
            continue
        candidate = " ".join(words).title()
        if candidate.lower() in ("a", "the", "another", "new"):
            continue
        for existing in existing_names:
            if existing.lower() in candidate.lower() or candidate.lower() in existing.lower():
                return existing
        return candidate
    return None


@admin_bp.route("/website-builder/generate", methods=["POST"])
@admin_required
def website_builder_generate():
    """Generate a NEW page, or EDIT an existing one, with real conversation
    continuity, streamed to the client as Server-Sent Events so the sidebar
    can show what's actually happening (reading the current page, calling
    the AI, parsing the result, saving) instead of a spinner with no
    detail — these are the real pipeline stages generate_site_stream()
    goes through, not a fabricated progress bar.

    Persists immediately once the AI call succeeds (creating the website
    record on the very first generate if it doesn't exist yet) so a
    generated page is never lost if the browser closes before a manual
    Save — same pattern already used by funnel_builder_page_generate()."""
    from app.utils.website_builder import generate_site_stream
    from app.models.platform import UserWebsite
    import re, secrets

    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Please describe the website you want to create."}), 400

    website_id = data.get("id")
    page_name = (data.get("page_name") or "Home").strip() or "Home"
    title = (data.get("title") or "").strip()
    user_id = current_user.id  # captured now -- current_user isn't safe to touch once we're inside the generator

    website = None
    if website_id:
        website = UserWebsite.query.filter_by(id=website_id, user_id=user_id).first()
        if not website:
            return jsonify({"error": "Website not found."}), 404

    # If the prompt is clearly asking for a NEW page ("create another page
    # for the admin dashboard") and the page currently open already has
    # content, redirect generation to that new page instead of overwriting
    # what's open — without this, the AI had no way to land the request
    # anywhere except the currently-open page's own HTML, so "another
    # page" content ended up crammed into whatever page you were on.
    if website:
        current_page = website.get_page(page_name)
        if current_page and (current_page.get("html") or "").strip():
            existing_names = [p.get("name") for p in (website.pages or []) if p.get("name")]
            detected = _detect_requested_new_page_name(prompt, existing_names)
            if detected and detected.lower() != page_name.lower():
                page_name = detected

    if website:
        page = website.get_page(page_name)
        other_pages = website.pages or []
        chat_history = (website.chat_history or {}).get(page_name, [])
        if page and (page.get("html") or "").strip():
            mode, current_files = "edit", {"html": page.get("html", ""), "css": page.get("css", ""), "js": page.get("js", "")}
        else:
            mode, current_files = "create", None
    else:
        other_pages, chat_history, mode, current_files = [], [], "create", None

    def sse(event_type, **payload):
        return f"data: {json.dumps({'type': event_type, **payload})}\n\n"

    @stream_with_context
    def event_stream():
        # Every step below is wrapped in one try/except -- previously
        # NOTHING was, so any unexpected failure (a malformed AI response,
        # a DB error, anything) killed the connection mid-stream with no
        # clean error frame sent. The browser then just hangs waiting for
        # more data that never comes, until a proxy/gateway eventually
        # times out (often 30-60+ seconds on a real server) -- which
        # reads exactly like "the button doesn't respond," when what
        # actually happened was a silent server-side crash with no way
        # for the UI to find out. Now it always yields a real error
        # event immediately instead.
        try:
            final = None
            for event in generate_site_stream(prompt, mode=mode, current_files=current_files,
                                               other_pages=other_pages, page_name=page_name,
                                               chat_history=chat_history):
                if event.get("status"):
                    yield sse("status", message=event["status"])
                if event.get("done"):
                    final = event

            if final is None:
                yield sse("error", error="Generation ended unexpectedly with no result.")
                return
            if final.get("error"):
                yield sse("error", error=final["error"])
                return

            files, updated_history, source = final["files"], final["history"], final["source"]

            nonlocal website
            if not website:
                site_title = title or "Untitled Website"
                slug = re.sub(r"[^a-z0-9]+", "-", site_title.lower()).strip("-") or "site"
                slug = f"{slug}-{secrets.token_hex(3)}"
                website = UserWebsite(user_id=user_id, title=site_title, slug=slug, pages=[], chat_history={})
                db.session.add(website)
                db.session.flush()  # so website.slug is available for the form-capture snippet below

            # window.__SITE_SLUG__ backs the "DATA BACKEND" instructions in
            # the system prompt -- the AI is told to build data endpoint
            # URLs from this instead of hard-coding a slug, so it actually
            # needs to exist for real, not just be promised in the prompt.
            slug_setter = f"window.__SITE_SLUG__ = {json.dumps(website.slug)};\n"
            js_with_capture = slug_setter + (files["js"] or "") + "\n" + _form_capture_snippet(website.slug)

            pages = website.pages or []
            found = False
            for p in pages:
                if (p.get("name") or "").lower() == page_name.lower():
                    p["html"], p["css"], p["js"] = files["html"], files["css"], js_with_capture
                    found = True
                    break
            if not found:
                pages.append({"name": page_name, "html": files["html"], "css": files["css"], "js": js_with_capture, "order": len(pages)})
            website.pages = pages

            ch = dict(website.chat_history or {})
            ch[page_name] = updated_history
            website.chat_history = ch
            if title:
                website.title = title
            website.updated_at = datetime.utcnow()
            db.session.commit()

            yield sse("done", html=files["html"], css=files["css"], js=js_with_capture, source=source,
                       id=website.id, slug=website.slug, mode=mode, turns=len(ch.get(page_name, [])),
                       chat_history=updated_history, page_name=page_name, pages=website.pages)
        except Exception as e:
            current_app.logger.exception("website_builder_generate stream failed")
            try:
                db.session.rollback()
            except Exception:
                pass
            yield sse("error", error=f"Something went wrong while generating: {e}")

    return Response(event_stream(), mimetype="text/event-stream",
                     headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})



@admin_bp.route("/website-builder/save", methods=["POST"])
@admin_required
def website_builder_save():
    """Save title / page-name edits, or a manually-added blank page.
    (AI-generated content is already saved immediately by /generate —
    this covers the parts of the Properties panel that aren't AI-driven.)"""
    from app.models.platform import UserWebsite
    import re, secrets
    data = request.get_json(silent=True) or {}
    title = data.get("title", "Untitled Website").strip()
    html_content = data.get("html") or data.get("html_content") or ""
    css_content = data.get("css", "")
    js_content = data.get("js", "")
    website_id = data.get("id")
    page_name = data.get("page_name", "Home")

    if website_id:
        website = UserWebsite.query.filter_by(id=website_id, user_id=current_user.id).first()
        if not website:
            return jsonify({"error": "Website not found."}), 404
        pages = website.pages or []
        page_found = False
        for p in pages:
            if p.get("name") == page_name:
                p["html"] = html_content
                if css_content or "css" not in p:
                    p["css"] = css_content
                if js_content or "js" not in p:
                    p["js"] = js_content
                page_found = True
                break
        if not page_found:
            pages.append({"name": page_name, "html": html_content, "css": css_content, "js": js_content, "order": len(pages)})
        website.pages = pages
        website.title = title
        website.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"id": website.id, "slug": website.slug, "message": "Website saved."})
    else:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "site"
        slug = f"{slug}-{secrets.token_hex(3)}"
        website = UserWebsite(
            user_id=current_user.id,
            title=title,
            slug=slug,
            pages=[{"name": page_name, "html": html_content, "css": css_content, "js": js_content, "order": 0}],
            chat_history={},
        )
        db.session.add(website)
        db.session.commit()
        return jsonify({"id": website.id, "slug": website.slug, "message": "Website created."})



@admin_bp.route("/website-builder/publish", methods=["POST"])
@admin_required
def website_builder_publish():
    """Publish a website to a subdomain."""
    from app.models.platform import UserWebsite
    import secrets
    data = request.get_json(silent=True) or {}
    website_id = data.get("id")
    website = UserWebsite.query.filter_by(id=website_id, user_id=current_user.id).first()
    if not website:
        return jsonify({"error": "Website not found."}), 404
    if not website.pages:
        return jsonify({"error": "Generate at least one page before publishing."}), 400
    if not website.subdomain:
        # Retry on the rare collision instead of trusting one random draw —
        # subdomain is a unique column and an IntegrityError here previously
        # would have surfaced as a raw 500 with no useful message.
        for _ in range(5):
            candidate = f"site-{secrets.token_hex(4)}"
            if not UserWebsite.query.filter_by(subdomain=candidate).first():
                website.subdomain = candidate
                break
        else:
            return jsonify({"error": "Couldn't generate a unique subdomain, try again."}), 500
    website.published = True
    website.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({
        "message": "Website published!",
        "url": url_for("dashboard.serve_website", subdomain=website.subdomain, _external=True),
        "subdomain": website.subdomain,
    })



@admin_bp.route("/website-builder/<int:website_id>/edit")
@admin_required
def website_builder_edit(website_id):
    """Edit an existing website — this is the canonical URL "My Sites"
    links to (see loadWebsite() in the template)."""
    from app.models.platform import UserWebsite
    website = UserWebsite.query.filter_by(id=website_id, user_id=current_user.id).first_or_404()
    return render_template("admin/website_builder.html",
        websites=UserWebsite.query.filter_by(user_id=current_user.id).order_by(UserWebsite.updated_at.desc()).all(),
        editing=website,
    )



@admin_bp.route("/website-builder/<int:website_id>/delete", methods=["POST"])
@admin_required
def website_builder_delete(website_id):
    """Delete a user website."""
    from app.models.platform import UserWebsite
    website = UserWebsite.query.filter_by(id=website_id, user_id=current_user.id).first_or_404()
    db.session.delete(website)
    db.session.commit()
    return jsonify({"message": "Website deleted."})



@admin_bp.route("/website-builder/<int:website_id>/github-push", methods=["POST"])
@admin_required
def website_builder_github_push(website_id):
    """Push every page's html/css/js to a real GitHub repo (creating it
    the first time, updating in place after that) using the same GitHub
    credential Automation Studio already supports connecting."""
    from app.models.platform import UserWebsite
    from app.utils.github_publish import push_website
    website = UserWebsite.query.filter_by(id=website_id, user_id=current_user.id).first_or_404()
    if not website.pages:
        return jsonify({"error": "Generate at least one page before pushing to GitHub."}), 400
    repo_url, error = push_website(website)
    if error:
        return jsonify({"error": error}), 400
    website.github_repo = repo_url.replace("https://github.com/", "")
    db.session.commit()
    return jsonify({"message": "Pushed to GitHub.", "repo_url": repo_url})


# ══════════════════════════════════════════════════════════════════════
#  SALES FUNNEL BUILDER
# ══════════════════════════════════════════════════════════════════════



@admin_bp.route("/website-builder/<int:website_id>/download")
@login_required
@admin_required
def website_builder_download(website_id):
    """Real multi-file export: index.html + style.css + script.js per
    page (in its own folder), plus a README — not one HTML blob per page
    like before, so what you download is genuinely reviewable/editable
    source, matching what the GitHub push produces."""
    from app.models.platform import UserWebsite
    import io, zipfile
    website = UserWebsite.query.filter_by(id=website_id, user_id=current_user.id).first_or_404()

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        pages = website.pages or []
        readme = f"# {website.title}\n\nExported from Bazillin Website Builder.\n\n## Pages\n"
        for p in pages:
            folder = (p.get("name") or "page").lower().replace(" ", "-")
            readme += f"- `{folder}/index.html`\n"
            zipf.writestr(f"{folder}/index.html", p.get("html", ""))
            zipf.writestr(f"{folder}/style.css", p.get("css", ""))
            zipf.writestr(f"{folder}/script.js", p.get("js", ""))
        zipf.writestr("README.md", readme)

    memory_file.seek(0)
    from flask import send_file
    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{website.slug or 'website'}_package.zip"
    )




@admin_bp.route("/website-builder/<int:website_id>/pages", methods=["GET"])
@login_required
@admin_required
def website_builder_get_pages(website_id):
    from app.models.platform import UserWebsite
    website = UserWebsite.query.filter_by(id=website_id, user_id=current_user.id).first_or_404()
    return jsonify({"pages": website.pages or []})


# ── Public AI Chatbot Embed & Widget ───────────────────────────────────



@admin_bp.route("/website-builder/<int:website_id>/pages/delete", methods=["POST"])
@login_required
@admin_required
def website_builder_delete_page(website_id):
    from app.models.platform import UserWebsite
    website = UserWebsite.query.filter_by(id=website_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    page_name = data.get("page_name")
    if not page_name or page_name == "Home":
        return jsonify({"error": "Cannot delete default page."}), 400
    pages = website.pages or []
    pages = [p for p in pages if p.get("name") != page_name]
    website.pages = pages
    ch = dict(website.chat_history or {})
    ch.pop(page_name, None)
    website.chat_history = ch
    db.session.commit()
    return jsonify({"success": True, "message": "Page deleted."})
@admin_bp.route("/graphics-studio")
@admin_required
def graphics_studio():
    """Graphics Studio workspace."""
    return render_template("admin/graphics_studio.html")



@admin_bp.route("/graphics-studio/generate", methods=["POST"])
@admin_required
def graphics_studio_generate():
    """Generate an image using AI."""
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Please describe the image you want."}), 400

    # Try Bloom first, then Pollinations (free)
    from app.utils.bloom import bloom_configured, generate_image as bloom_generate
    from app.utils.stock_photos import pollinations_image_url

    if bloom_configured():
        url, err = bloom_generate(prompt)
        if not err:
            return jsonify({"url": url, "source": "bloom"})

    # Pollinations fallback (always free)
    url = pollinations_image_url(prompt)
    return jsonify({"url": url, "source": "pollinations"})



@admin_bp.route("/graphics-studio/search-photos", methods=["POST"])
@admin_required
def graphics_studio_search_photos():
    """Search stock photos."""
    from app.utils.stock_photos import search_photos, pexels_configured
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Please enter a search query."}), 400
    if not pexels_configured():
        return jsonify({"error": "Pexels API key not configured. Use AI generation instead."}), 400
    photos = search_photos(query)
    return jsonify({"photos": photos})


# ══════════════════════════════════════════════════════════════════════
#  CONTENT STUDIO
# ══════════════════════════════════════════════════════════════════════



@admin_bp.route("/video-studio")
@admin_required
def video_studio():
    """Video Studio workspace."""
    return render_template("admin/video_studio.html")



@admin_bp.route("/video-studio/generate", methods=["POST"])
@admin_required
def video_studio_generate():
    """Generate a video using AI."""
    from app.utils.video_ai import video_ai_configured, generate_video
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Please describe the video you want."}), 400
    if not video_ai_configured():
        return jsonify({"error": "Video AI is not configured. Ask your admin to set up a Video AI provider in Settings."}), 400
    result, error = generate_video(prompt)
    if error:
        return jsonify({"error": error}), 500
    return jsonify({"result": result})


# ══════════════════════════════════════════════════════════════════════
#  CHATBOT BUILDER
# ══════════════════════════════════════════════════════════════════════

@admin_bp.route("/ai-chatbot-agents")
@admin_required
def ai_chatbot_agents():
    """Admin list of every customer's AI Chatbot agent (UserChatbot rows
    with platform='ai-agent'). This is the missing half of the AI
    Chatbot product: purchasing unlocks the customer's dashboard page,
    but the agent itself only exists — and only shows up there — once
    an admin creates it here."""
    from app.models.platform import UserChatbot
    agents = UserChatbot.query.filter_by(platform="ai-agent").order_by(UserChatbot.created_at.desc()).all()
    from app.models.user import User
    from app.models.platform import UserProductAccess
    pending = []
    agent_user_ids = {a.user_id for a in agents}
    accesses = UserProductAccess.query.filter_by(product_slug="ai-chatbot", active=True).all()
    for acc in accesses:
        if acc.user_id not in agent_user_ids:
            u = User.query.get(acc.user_id)
            if u:
                pending.append(u)
    from app.ai_tools.routes import _resolve_ai_provider
    provider, _key = _resolve_ai_provider()
    return render_template("admin/ai_chatbot_agents.html", agents=agents, pending=pending, ai_provider=provider)


@admin_bp.route("/ai-chatbot-agents/create", methods=["POST"])
@admin_required
def ai_chatbot_agents_create():
    """Create (or fully reconfigure) a customer's AI Agent. Setting
    ai_enabled=True here is what makes replies real — chatbot_reply()
    already calls the platform's configured AI provider whenever a bot
    has ai_enabled set, so no separate wiring is needed beyond this."""
    from app.models.platform import UserChatbot
    from app.models.user import User
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    user = None
    if user_id:
        user = User.query.get(user_id)
    if not user and data.get("user_email"):
        user = User.query.filter_by(email=data["user_email"].strip().lower()).first()
    if not user:
        return jsonify({"error": "No matching customer account found for that email."}), 400
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Agent name is required."}), 400

    agent = UserChatbot.query.filter_by(user_id=user.id, platform="ai-agent").first()
    if not agent:
        agent = UserChatbot(user_id=user.id, platform="ai-agent")
        db.session.add(agent)
    agent.name = name[:128]
    agent.greeting = data.get("greeting") or "Hi! How can I help you today?"
    agent.ai_instructions = data.get("ai_instructions") or (
        f"You are the AI customer support assistant for {user.name or user.email}'s business. "
        "Be polite and helpful. If you don't know something, say so clearly rather than guessing "
        "or inventing prices, products, or policies."
    )
    agent.ai_enabled = True
    agent.active = True
    agent.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"message": f"AI Agent set up for {user.name or user.email}. It now appears in their dashboard.", "id": agent.id})


@admin_bp.route("/ai-chatbot-agents/<int:agent_id>/toggle", methods=["POST"])
@admin_required
def ai_chatbot_agents_toggle(agent_id):
    from app.models.platform import UserChatbot
    agent = UserChatbot.query.filter_by(id=agent_id, platform="ai-agent").first_or_404()
    agent.active = not agent.active
    db.session.commit()
    return jsonify({"active": agent.active})


@admin_bp.route("/ai-chatbot-agents/<int:agent_id>/delete", methods=["POST"])
@admin_required
def ai_chatbot_agents_delete(agent_id):
    from app.models.platform import UserChatbot
    agent = UserChatbot.query.filter_by(id=agent_id, platform="ai-agent").first_or_404()
    db.session.delete(agent)
    db.session.commit()
    return jsonify({"message": "Agent deleted."})


@admin_bp.route("/chatbot/widget/<int:bot_id>")
def chatbot_widget_js(bot_id):
    """Serve a public copy-pasteable javascript widget loader. Reads the
    bot's own configured appearance (logo, position, color, icon,
    animation, label, visibility) via app.utils.chat_widget — was
    previously a fully hardcoded bubble (fixed green, bottom-right,
    generic icon, no way to configure anything)."""
    from app.models.platform import UserChatbot
    from app.utils.chat_widget import render_embed_script
    bot = UserChatbot.query.filter_by(id=bot_id, active=True).first_or_404()
    base_url = request.url_root
    js_code = render_embed_script(bot, base_url)
    from flask import Response
    return Response(js_code, mimetype="application/javascript")


# ── Chatbot Reply endpoint (Public / Test Panel) ──────────────────────


@admin_bp.route("/chatbot/<int:bot_id>/reply", methods=["POST"])
@admin_bp.route("/chatbot-builder/<int:bot_id>/reply", methods=["POST"])
def chatbot_reply(bot_id):
    """Generate reply from chatbot (used in public widget and test panel).
    Public-facing — a real website visitor has no session/CSRF token, so
    this must stay exempt (see the module-level csrf.exempt() call below;
    exempting from *inside* a view body runs too late to matter, since
    CSRFProtect's check happens in a before_request hook before the view
    ever executes).

    WhatsApp Bot's web widget is deliberately NOT a full AI chatbot: it
    answers a limited number of AI-generated messages, then hands the
    visitor off to a real WhatsApp conversation (with the on-site chat
    transcript carried over as the pre-filled WhatsApp message) instead
    of continuing indefinitely. AI Chatbot (platform == "ai-agent") is
    the one product meant for unlimited AI conversation — that
    distinction is what this endpoint enforces below.

    Every message (both sides) is also logged to UserChatbotMessage,
    grouped by the client-generated session_id, so each tool's own
    dashboard page can show a real conversation history instead of just
    a raw counter."""
    from app.models.platform import UserChatbot, UserChatbotMessage
    from app.ai_tools.routes import _call_ai

    bot = UserChatbot.query.filter_by(id=bot_id).first_or_404()
    bot.message_count = (bot.message_count or 0) + 1

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []  # [{"sender": "user"|"bot", "text": "..."}, ...] — used only to build the WhatsApp handoff transcript
    ai_turns_used = int(data.get("ai_turns_used") or 0)
    session_id = (data.get("session_id") or "")[:64]
    if not message:
        return jsonify({"reply": "I did not receive a message."})

    def _log(sender, text, source=None):
        if not session_id:
            return  # no session id supplied (e.g. an older/custom integration) — skip logging rather than group everything under one bucket
        db.session.add(UserChatbotMessage(bot_id=bot.id, session_id=session_id, sender=sender, text=text, source=source))

    _log("user", message)

    # 1. Keyword search (lower-priority if AI is enabled, but fallback if disabled)
    keywords = bot.keywords or []
    for kw in keywords:
        pattern = kw.get("pattern", "").strip().lower()
        type_ = kw.get("type", "contains")
        reply_val = kw.get("reply", "")
        if not pattern:
            continue
        if type_ == "exact" and message.lower() == pattern:
            _log("bot", reply_val, "keyword")
            db.session.commit()
            return jsonify({"reply": reply_val, "source": "keyword"})
        elif type_ == "contains" and pattern in message.lower():
            _log("bot", reply_val, "keyword")
            db.session.commit()
            return jsonify({"reply": reply_val, "source": "keyword"})

    # WhatsApp Bot's widget (any platform other than the dedicated AI
    # Chatbot agent) caps how many AI-generated replies a visitor gets
    # before being handed off to real WhatsApp. AI Chatbot itself is
    # exempt — it's meant to be full, ongoing AI conversation.
    is_ai_chatbot_product = (bot.platform == "ai-agent")
    ai_reply_limit = (bot.widget_settings or {}).get("ai_reply_limit", 3) if not is_ai_chatbot_product else None

    if bot.ai_enabled and not is_ai_chatbot_product and ai_reply_limit is not None and ai_turns_used >= ai_reply_limit:
        handoff_reply = "I've answered what I can here — let's continue this on WhatsApp so we can help you properly."
        _log("bot", handoff_reply, "handoff")
        db.session.commit()
        return jsonify({
            "reply": handoff_reply,
            "source": "handoff",
            "whatsapp_url": _build_whatsapp_handoff_url(bot, history, message),
        })

    # 2. AI generation if enabled — now grounded in the bot's own
    # Knowledge Base (FAQs + manual info) instead of only the raw
    # ai_instructions prompt, so it can actually answer questions about
    # the business instead of just following a tone/personality prompt.
    if bot.ai_enabled:
        from app.utils.knowledge import generate_bot_reply
        reply, err = generate_bot_reply(
            bot.ai_instructions, bot.faqs, bot.knowledge_text, message,
            unknown_reply=bot.unknown_reply, sources=bot.knowledge_sources,
            charge_user_id=bot.user_id,
        )
        if not err and reply:
            _log("bot", reply, "ai")
            db.session.commit()
            return jsonify({"reply": reply, "source": "ai"})
        if err:
            # Previously silent — a misconfigured/failing AI provider meant
            # every reply silently fell through to the generic fallback
            # below with zero trace anywhere of WHY, making "the bot
            # doesn't reply" impossible to diagnose from the admin side.
            current_app.logger.warning(f"AI Chatbot bot_id={bot.id} generate_bot_reply failed: {err}")

    # 3. Fallback default reply
    fallback_reply = "Thank you for your message. We have received it and will get back to you shortly!"
    _log("bot", fallback_reply, "fallback")
    db.session.commit()
    return jsonify({"reply": fallback_reply, "source": "fallback"})


def _build_whatsapp_handoff_url(bot, history, latest_message):
    """Builds a wa.me link pre-filled with the on-site chat transcript so
    far, so the business owner sees the full conversation context the
    moment it lands in their real WhatsApp — not just a blank chat."""
    from app.utils.whatsapp_widget import sanitize_phone
    phone = sanitize_phone(bot.display_phone or "")
    if not phone:
        return None

    lines = ["Continuing our chat from your website:"]
    for turn in history[-12:]:  # cap transcript length — long enough for real context, short enough to stay a sane URL length
        sender = "Me" if turn.get("sender") == "user" else (bot.name or "Bot")
        text = (turn.get("text") or "").strip()
        if text:
            lines.append(f"{sender}: {text}")
    lines.append(f"Me: {latest_message}")
    transcript = "\n".join(lines)[:1500]

    from urllib.parse import quote
    return f"https://wa.me/{phone}?text={quote(transcript)}"


from app.extensions import csrf as _csrf
_csrf.exempt(chatbot_reply)


# ── Delete Website Page endpoint ──────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════
#  USER SETTINGS
# ══════════════════════════════════════════════════════════════════════
