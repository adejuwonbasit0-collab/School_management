from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, current_app, session
from datetime import datetime
from flask_login import login_required, current_user, login_user
from app.extensions import db, limiter
from app.models import (
    Project, Service, Testimonial, BlogPost,
    CmsBlock, SiteSetting, NewsletterSubscriber,
    Notification, SupportTicket, Product, FAQItem, User,
)
from app.utils.settings import get_setting, default_site_currency
from app.utils.feature_flags import feature_enabled, require_feature
from app.utils.analytics import log_event

cms_bp = Blueprint("cms", __name__)


def _get_cms(key, default=None):
    block = CmsBlock.query.filter_by(key=key, active=True).first()
    if block:
        return block.content if block.content is not None else default
    return default


@cms_bp.route("/favicon.ico")
def favicon():
    from flask import send_from_directory, current_app, Response
    import os, requests

    fav = get_setting("seo_favicon_url")
    if fav and fav.startswith("http"):
        try:
            r = requests.get(fav, timeout=5)
            if r.status_code == 200:
                return Response(r.content, mimetype=r.headers.get("Content-Type", "image/x-icon"))
        except Exception:
            pass

    static_dir = os.path.join(current_app.root_path, "..", "static")
    if os.path.exists(os.path.join(static_dir, "favicon.ico")):
        return send_from_directory(static_dir, "favicon.ico", mimetype="image/x-icon")
    
    return send_from_directory(static_dir, "favicon.png", mimetype="image/png")


@cms_bp.route("/manifest.json")
def manifest():
    return current_app.send_static_file("manifest.json")


@cms_bp.route("/service-worker.js")
def service_worker():
    response = current_app.send_static_file("js/service-worker.js")
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@cms_bp.route("/set-currency/<code>", methods=["GET", "POST"])
def set_currency(code):
    """Visitor-facing currency switcher. Stores the choice in the visitor's
    own session (never touches the site-wide site_currency setting, which
    stays the admin's base/pricing currency) — every {{ amount|display_currency }}
    on the site then renders in this currency for this visitor until they
    change it again or their session ends. Only currencies the admin has
    actually set a manual rate for (plus the base currency) are accepted,
    so you can never end up display-converting through a rate that doesn't
    exist."""
    from app.utils.currency import SUPPORTED_CURRENCIES, base_currency, get_rates
    code = (code or "").upper()
    allowed = {base_currency()} | set(get_rates().keys())
    if code in SUPPORTED_CURRENCIES and code in allowed:
        session["display_currency"] = code
    next_url = request.form.get("next") or request.args.get("next") or request.referrer or url_for("cms.home")
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": code in allowed, "currency": session.get("display_currency")})
    return redirect(next_url)


@cms_bp.route("/")
def home():
    # maintenance check
    if get_setting("maintenance_mode", "false") in ("true", True, "True", "1"):
        return render_template("errors/maintenance.html"), 503

    hero = _get_cms("hero", {})
    services = Service.query.filter_by(active=True).order_by(Service.order).limit(6).all()
    projects = Project.query.filter_by(featured=True).order_by(Project.order).limit(6).all()
    testimonials = Testimonial.query.filter_by(featured=True, approved=True).order_by(Testimonial.order).limit(6).all()
    recent_posts = []
    if feature_enabled("blog_enabled"):
        recent_posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).limit(3).all()
    cta = _get_cms("cta", {})
    stats = _get_cms("stats", [])
    # marketplace preview (if enabled)
    products = []
    if feature_enabled("marketplace_enabled"):
        products = Product.query.filter_by(status="active", featured=True).order_by(Product.created_at.desc()).limit(4).all()
        if not products:
            products = Product.query.filter_by(status="active").order_by(Product.created_at.desc()).limit(4).all()
    services_cms = _get_cms("services_section", {})
    from app.models.platform import TrendItem
    trends = TrendItem.query.filter_by(approved=True, hidden=False).order_by(
        TrendItem.pinned.desc(), TrendItem.created_at.desc()).limit(6).all()
    from app.models.content import Partner
    active_partners = Partner.query.filter_by(active=True).order_by(Partner.order).all()
    return render_template("cms/home.html",
        hero=hero, services=services, projects=projects,
        testimonials=testimonials, recent_posts=recent_posts,
        cta=cta, stats=stats, products=products, services_cms=services_cms, trends=trends,
        active_partners=active_partners)


@cms_bp.route("/about")
def about():
    from app.models.content import Profile, Skill, Experience, Education, Certification
    profile = Profile.query.first()
    skills  = Skill.query.order_by(Skill.order).all()
    exps    = Experience.query.order_by(Experience.order).all()
    edus    = Education.query.order_by(Education.order).all()
    certs   = Certification.query.order_by(Certification.order).all()
    projects = Project.query.order_by(Project.featured.desc(), Project.order).all()
    services = Service.query.filter_by(active=True).order_by(Service.order).all()
    testimonials = Testimonial.query.filter_by(featured=True, approved=True).order_by(Testimonial.order).all()
    return render_template("cms/about.html",
        profile=profile, skills=skills, experiences=exps,
        educations=edus, certifications=certs,
        projects=projects, services=services, testimonials=testimonials)


@cms_bp.route("/services")
def services():
    services = Service.query.filter_by(active=True).order_by(Service.order).all()
    return render_template("cms/services.html", services=services)


@cms_bp.route("/services/<int:service_id>")
def service_detail(service_id):
    service = Service.query.filter_by(id=service_id, active=True).first_or_404()
    related = Service.query.filter_by(active=True).filter(Service.id != service.id).order_by(Service.order).limit(3).all()
    return render_template("cms/service_detail.html", service=service, related=related)


@cms_bp.route("/works")
def works():
    projects = Project.query.order_by(Project.featured.desc(), Project.order, Project.created_at.desc()).all()
    return render_template("cms/works.html", projects=projects)


@cms_bp.route("/works/<identifier>")
def work_detail(identifier):
    # Slugs are auto-generated for every project created going forward, but
    # older/seeded rows may not have one — fall back to numeric id so no
    # existing project 404s just because it predates slugs.
    project = Project.query.filter_by(slug=identifier).first()
    if not project and identifier.isdigit():
        project = Project.query.filter_by(id=int(identifier)).first()
    if not project:
        abort(404)
    related = Project.query.filter(Project.id != project.id).order_by(Project.featured.desc(), Project.order).limit(3).all()
    return render_template("cms/work_detail.html", project=project, related=related,
        page_seo_title=project.seo_title or project.title,
        page_seo_desc=project.seo_desc or project.description,
        page_og_image=project.image_url)


@cms_bp.route("/blog")
def blog():
    if not feature_enabled("blog_enabled"):
        return render_template("errors/feature_disabled.html", feature="Blog"), 503
    page     = request.args.get("page", 1, type=int)
    category = request.args.get("category", "")
    q        = request.args.get("q", "")
    query    = BlogPost.query.filter_by(published=True)
    if category:
        query = query.filter_by(category=category)
    if q:
        query = query.filter(BlogPost.title.ilike(f"%{q}%"))
    posts = query.order_by(BlogPost.created_at.desc()).paginate(page=page, per_page=9)
    categories = [c[0] for c in db.session.query(BlogPost.category).distinct().all() if c[0]]
    return render_template("cms/blog.html", posts=posts, categories=categories, current_cat=category)


@cms_bp.route("/blog/<slug>")
def blog_post(slug):
    if not feature_enabled("blog_enabled"):
        return render_template("errors/feature_disabled.html", feature="Blog"), 503
    post = BlogPost.query.filter_by(slug=slug, published=True).first_or_404()
    post.views += 1
    db.session.commit()
    related = BlogPost.query.filter_by(published=True, category=post.category).filter(BlogPost.id != post.id).limit(3).all()
    return render_template("cms/blog_post.html", post=post, related=related,
        page_seo_title=post.seo_title or post.title,
        page_seo_desc=post.seo_desc or post.excerpt,
        page_og_image=post.cover_image)


@cms_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name    = request.form.get("name", "").strip()
        email   = request.form.get("email", "").strip()
        subject = request.form.get("subject", "General Inquiry")
        message = request.form.get("message", "").strip()
        if name and email and message:
            ticket = SupportTicket(name=name, email=email, subject=subject, message=message,
                                   user_id=current_user.id if current_user.is_authenticated else None)
            db.session.add(ticket)
            db.session.commit()
            log_event("contact_submit", path="/contact", metadata={"subject": subject})
            flash("Message sent! We will get back to you shortly.", "success")
            return redirect(url_for("cms.contact"))
        flash("Please fill in all required fields.", "danger")
    contact_cms = _get_cms("contact", {})
    return render_template("cms/contact.html", contact=contact_cms)


@cms_bp.route("/newsletter/subscribe", methods=["POST"])
def newsletter_subscribe():
    email = request.form.get("email") or (request.get_json(silent=True) or {}).get("email", "")
    name  = request.form.get("name", "")
    if not email:
        if request.is_json:
            return jsonify({"error": "Email required"}), 400
        flash("Email is required.", "danger")
        return redirect(request.referrer or url_for("cms.home"))
    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    is_new = not existing
    if not existing:
        sub = NewsletterSubscriber(email=email, name=name)
        sub.ensure_token()
        db.session.add(sub)
    elif existing.unsubscribed:
        existing.unsubscribed = False  # re-subscribing
    db.session.commit()

    if is_new:
        from app.utils.automation import trigger as automation_trigger
        automation_trigger("newsletter_subscribed", {"email": email, "name": name})
        log_event("newsletter_signup", path="/newsletter/subscribe")

        from app.models.core import EmailSequence
        from app.utils.email_sequences import enroll_subscriber
        for seq in EmailSequence.query.filter_by(trigger="newsletter_signup", active=True).all():
            enroll_subscriber(seq, sub)

    if request.is_json:
        return jsonify({"success": True})
    flash("Successfully subscribed!", "success")
    return redirect(request.referrer or url_for("cms.home"))


@cms_bp.route("/newsletter/unsubscribe/<token>")
def newsletter_unsubscribe(token):
    sub = NewsletterSubscriber.query.filter_by(unsub_token=token).first()
    if not sub:
        abort(404)
    sub.unsubscribed = True
    db.session.commit()
    return render_template("cms/newsletter_unsubscribed.html", email=sub.email)


def _get_viewing_user():
    """Admin-only, session-based dashboard preview. Never touches the real
    database role — just substitutes which user's data the *admin* is
    looking at, with an obvious exit path. Falls back to current_user for
    everyone else, or if no preview is active."""
    from flask import session
    if current_user.is_admin():
        preview_id = session.get("preview_user_id")
        if preview_id:
            preview_user = User.query.get(preview_id)
            if preview_user:
                return preview_user
    return current_user





@cms_bp.route("/notifications/read/<int:nid>", methods=["POST"])
@login_required
def mark_notification_read(nid):
    n = Notification.query.filter_by(id=nid, user_id=current_user.id).first_or_404()
    n.read = True
    db.session.commit()
    return jsonify({"success": True})


@cms_bp.route("/api/notifications")
@login_required
def api_notifications():
    """Powers the notification bell dropdown shown site-wide (not just the
    dashboard page) for any logged-in user."""
    items = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()).limit(20).all()
    unread_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    return jsonify({
        "unread_count": unread_count,
        "notifications": [{
            "id": n.id, "title": n.title, "body": n.body, "read": n.read,
            "link": n.link, "created_at": n.created_at.strftime("%b %d, %H:%M"),
        } for n in items],
    })


@cms_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, read=False).update({"read": True})
    db.session.commit()
    return jsonify({"success": True})


# ── FAQ Auto-Reply Chat Widget ───────────────────────────────────────────────
@cms_bp.route("/api/faq")
def api_faq_list():
    """All active FAQs, grouped by category, for the chat widget's initial menu."""
    items = FAQItem.query.filter_by(active=True).order_by(FAQItem.category, FAQItem.order).all()
    grouped = {}
    for i in items:
        grouped.setdefault(i.category or "General", []).append(
            {"id": i.id, "question": i.question}
        )
    return jsonify({"categories": grouped})


@cms_bp.route("/api/faq/<int:fid>")
def api_faq_answer(fid):
    item = FAQItem.query.filter_by(id=fid, active=True).first_or_404()
    item.view_count = (item.view_count or 0) + 1
    db.session.commit()
    return jsonify({"id": item.id, "question": item.question, "answer": item.answer})


@cms_bp.route("/api/faq/search")
def api_faq_search():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"results": []})
    matches = (FAQItem.query.filter_by(active=True)
               .filter(db.or_(FAQItem.question.ilike(f"%{q}%"), FAQItem.answer.ilike(f"%{q}%")))
               .order_by(FAQItem.order).limit(8).all())
    return jsonify({"results": [{"id": i.id, "question": i.question} for i in matches]})


@cms_bp.route("/api/chat/handoff", methods=["POST"])
def api_chat_handoff():
    """'Talk to a person' — creates a real support ticket the admin team will see,
    and if the visitor is logged in, also opens a real Comms thread with an admin."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    message = data.get("message", "").strip()
    transcript = data.get("transcript", "")  # what the bot couldn't answer, for context

    if current_user.is_authenticated:
        name = name or (current_user.name or current_user.email)
        email = email or current_user.email

    if not name or not email or not message:
        return jsonify({"error": "Please provide your name, email, and a message."}), 400

    full_message = message
    if transcript:
        full_message += f"\n\n--- Chat widget context ---\n{transcript}"

    ticket = SupportTicket(
        name=name, email=email, subject="Live chat handoff request", message=full_message,
        user_id=current_user.id if current_user.is_authenticated else None,
        priority="high",
    )
    db.session.add(ticket)
    db.session.commit()

    thread_id = None
    if current_user.is_authenticated:
        from app.models.user import Role
        from app.models.core import Message
        admin_role = Role.query.filter_by(name="admin").first()
        admin_user = admin_role.users.first() if admin_role else None
        if admin_user and admin_user.id != current_user.id:
            a, b = sorted([current_user.id, admin_user.id])
            thread_id = f"{a}-{b}"
            db.session.add(Message(
                sender_id=current_user.id, receiver_id=admin_user.id,
                content=f"[Support request] {message}", thread_id=thread_id,
            ))
            db.session.commit()

    # Always notify the admin directly — regardless of whether the visitor
    # was logged in — since a Message thread alone was easy to miss.
    from app.models.user import Role
    from app.models.core import Notification
    from app.utils.email import send_email
    admin_role = Role.query.filter_by(name="admin").first()
    if admin_role:
        for admin_user in admin_role.users:
            db.session.add(Notification(
                user_id=admin_user.id, type="chat_handoff", title="Someone wants to talk — live chat handoff",
                body=f"{name} ({email}): {message[:150]}",
                link=url_for("admin.support") if thread_id is None else url_for("comms.thread", thread_id=thread_id),
            ))
    db.session.commit()
    admin_email = get_setting("admin_email")
    if admin_email:
        send_email(to=admin_email, subject=f"💬 Live chat handoff — {name}",
                   body_html=f"<p><strong>{name}</strong> ({email}) asked to talk to a human:</p>"
                             f"<blockquote style='border-left:3px solid #2D68FF;padding-left:12px'>{message}</blockquote>"
                             + (f"<p><em>Chat context:</em><br>{transcript}</p>" if transcript else ""))

    return jsonify({"success": True, "ticket_id": ticket.id, "thread_id": thread_id})


# ── Hire / Project Workflow ────────────────────────────────────────────────────
from app.models.platform import ProjectRequest, ClientProject, ProjectMilestone, ProjectUpdate

@cms_bp.route("/hire-me")
@require_feature("client_mode_enabled")
def hire_me():
    faqs = FAQItem.query.filter_by(active=True).order_by(FAQItem.category, FAQItem.order).all()
    whatsapp_number = get_setting("whatsapp_number", "")
    
    from app.models.user import Role
    admin_role = Role.query.filter_by(name="admin").first()
    admin_user = admin_role.users.first() if admin_role else None

    return render_template("cms/hire_me.html", faqs=faqs,
                           whatsapp_number=whatsapp_number,
                           whatsapp_url=f"https://wa.me/{whatsapp_number.replace('+','').replace(' ','')}" if whatsapp_number else "",
                           admin_user=admin_user)


@cms_bp.route("/hire-me/submit", methods=["POST"])
@require_feature("client_mode_enabled")
def hire_me_submit():
    data = request.get_json(silent=True) or request.form.to_dict()
    name  = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    desc  = (data.get("description") or "").strip()
    chosen_password = (data.get("password") or "").strip()
    if not name or not email or not desc:
        if request.is_json:
            return jsonify({"error": "Name, email and project description are required."}), 400
        flash("Please fill in all required fields.", "danger")
        return redirect(url_for("cms.hire_me"))

    new_account_created = False
    if current_user.is_authenticated:
        req_user = current_user
    else:
        from app.models.user import User, Role
        req_user = User.query.filter_by(email=email).first()
        if not req_user:
            if len(chosen_password) < 8:
                msg = "Set a password of at least 8 characters to create your account."
                if request.is_json:
                    return jsonify({"error": msg}), 400
                flash(msg, "danger")
                return redirect(url_for("cms.hire_me"))
            from app.models.platform import ClientProfile
            client_role = Role.query.filter_by(name="client").first()
            req_user = User(name=name, email=email, role=client_role, email_verified=False)
            req_user.set_password(chosen_password)
            db.session.add(req_user)
            db.session.commit()
            db.session.add(ClientProfile(user_id=req_user.id, company_name=data.get("company", "")))
            db.session.commit()
            new_account_created = True

    from app.utils.currency import SUPPORTED_CURRENCIES
    from app.utils.settings import default_site_currency
    submitted_currency = (data.get("currency") or "").upper()
    req = ProjectRequest(
        user_id=req_user.id if req_user else None,
        name=name, email=email,
        company=data.get("company", ""),
        country=data.get("country", ""),
        project_type=data.get("project_type", ""),
        budget_range=data.get("budget_range", ""),
        timeline=data.get("timeline", ""),
        description=desc,
        status="new",
        currency=submitted_currency if submitted_currency in SUPPORTED_CURRENCIES else default_site_currency(),
    )
    db.session.add(req)
    db.session.commit()
    log_event("hire_me_lead", path="/hire-me", metadata={"project_type": req.project_type, "budget_range": req.budget_range})

    if new_account_created:
        from app.utils.email import send_email
        send_email(
            to=email, subject="Your account — track your project request",
            body_html=(
                f"<p>Thanks for reaching out, {name}! We've created an account for you at this email so you "
                f"can track your request and any proposal — log in any time with the email and password you "
                f"just set on the form.</p>"
            ),
        )
        # Log them in immediately for this session too — no need to wait on the email to see their own submission.
        login_user(req_user)

    # Notify the admin directly — don't rely solely on automation config,
    # which may not be set up, to make sure new leads are never missed.
    from app.models.user import Role
    from app.models.core import Notification
    from app.utils.email import send_email
    admin_role = Role.query.filter_by(name="admin").first()
    if admin_role:
        for admin_user in admin_role.users:
            db.session.add(Notification(
                user_id=admin_user.id, type="project_request", title="New project request",
                body=f"{name} ({email}) wants help with: {data.get('project_type') or 'a project'}",
                link=url_for("admin.leads"),
            ))
    db.session.commit()
    admin_email = get_setting("admin_email")
    if admin_email:
        send_email(
            to=admin_email, subject=f"New project request from {name}",
            body_html=f"<p><strong>{name}</strong> ({email}) submitted a project request:</p>"
                      f"<ul>"
                      f"<li><strong>Type:</strong> {data.get('project_type','—')}</li>"
                      f"<li><strong>Budget:</strong> {data.get('budget_range','—')}</li>"
                      f"<li><strong>Timeline:</strong> {data.get('timeline','—')}</li>"
                      f"</ul>"
                      f"<p><strong>Description:</strong><br>{desc}</p>",
        )

    from app.utils.automation import trigger as automation_trigger
    automation_trigger("hire_request_submitted", {
        "name": name, "email": email, "company": data.get("company", ""),
        "project_type": data.get("project_type", ""), "budget_range": data.get("budget_range", ""),
        "timeline": data.get("timeline", ""), "description": desc, "request_id": req.id,
    })

    ref_code = session.get("referral_code")
    if ref_code:
        from app.models.platform import ReferralCode, ReferralSignup
        rc = ReferralCode.query.filter_by(code=ref_code, active=True).first()
        if rc:
            db.session.add(ReferralSignup(referral_code_id=rc.id, name=name, email=email, source="hire_request"))
            db.session.commit()

    if request.is_json:
        resp = {"success": True, "id": req.id}
        if new_account_created:
            resp.update({"account_created": True, "email": email, "account_password": chosen_password})
        return jsonify(resp)
    flash("Thanks! Your project request has been sent. I'll be in touch soon.", "success")
    return redirect(url_for("cms.hire_me"))


@cms_bp.route("/project/<int:pid>")
@require_feature("client_mode_enabled")
@login_required
def client_project(pid):
    proj = ClientProject.query.filter_by(id=pid, client_id=current_user.id).first_or_404()
    from app.models.user import User, Role
    admin_role = Role.query.filter_by(name="admin").first()
    admin_user = User.query.filter_by(role_id=admin_role.id).first() if admin_role else None
    return render_template("cms/client_project.html", proj=proj, admin_user=admin_user)


@cms_bp.route("/project/<int:pid>/review", methods=["POST"])
@login_required
def submit_project_review(pid):
    from app.models.platform import ProjectReview
    proj = ClientProject.query.filter_by(id=pid, client_id=current_user.id).first_or_404()
    if proj.status != "completed":
        flash("This project isn't marked complete yet.", "danger")
        return redirect(url_for("cms.client_project", pid=pid))
    if proj.review:
        flash("You've already reviewed this project.", "info")
        return redirect(url_for("cms.client_project", pid=pid))
    rating = request.form.get("rating", type=int)
    if not rating or not (1 <= rating <= 5):
        flash("Please choose a star rating.", "danger")
        return redirect(url_for("cms.client_project", pid=pid))
    review = ProjectReview(project_id=pid, rating=rating, review_text=request.form.get("review_text", "").strip() or None)
    db.session.add(review)
    db.session.commit()

    from app.models.user import Role
    from app.models.core import Notification
    admin_role = Role.query.filter_by(name="admin").first()
    if admin_role:
        for admin_user in admin_role.users:
            db.session.add(Notification(
                user_id=admin_user.id, type="review", title=f"New {rating}★ review",
                body=f"{current_user.name or current_user.email} rated \"{proj.title}\" {rating}/5.",
                link=url_for("admin.admin_project_detail", pid=pid),
            ))
    db.session.commit()
    flash("Thanks for the feedback!", "success")
    return redirect(url_for("cms.client_project", pid=pid))


def _dashboard_badges(user_id):
    """Sidebar notification counts — unread messages and requests waiting
    on the user's decision (a sent proposal they haven't accepted/declined
    yet). This was called from my_requests() and client_project() but was
    never actually defined anywhere, which crashed both pages outright."""
    from app.models.core import Message
    unread_messages = Message.query.filter_by(receiver_id=user_id, read=False).count()
    pending_requests = ProjectRequest.query.filter_by(user_id=user_id, status="quoted").count()
    return {"messages": unread_messages, "requests": pending_requests}


@cms_bp.route("/my-requests")
@login_required
def my_requests():
    requests_list = ProjectRequest.query.filter_by(user_id=current_user.id).order_by(ProjectRequest.created_at.desc()).all()
    badges = _dashboard_badges(current_user.id)
    from app.dashboard.premium import get_user_products
    products = get_user_products(current_user)
    return render_template("cms/my_requests.html", requests_list=requests_list, badges=badges, products=products)


@cms_bp.route("/my-requests/<int:rid>/accept", methods=["POST"])
@login_required
def accept_proposal(rid):
    req = ProjectRequest.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
    if req.status != "quoted":
        flash("This proposal is no longer available to accept.", "danger")
        return redirect(url_for("cms.my_requests"))

    payment_mode = request.form.get("payment_mode")
    valid_modes = []
    if req.allow_part_payment: valid_modes.append("part")
    if req.allow_full_payment: valid_modes.append("full")
    if req.allow_after_service: valid_modes.append("after_service")
    if payment_mode not in valid_modes:
        flash("Please choose a valid payment option.", "danger")
        return redirect(url_for("cms.my_requests"))

    proj = ClientProject(
        request_id=req.id, client_id=current_user.id,
        title=req.project_type or "New Project", description=req.description,
        status="planning", progress_pct=0, payment_mode=payment_mode,
        allow_part_payment=req.allow_part_payment, allow_full_payment=req.allow_full_payment,
        allow_after_service=req.allow_after_service, agreed_budget=req.proposal_amount,
    )
    db.session.add(proj)
    req.status = "accepted"
    db.session.flush()

    # Generate the first invoice based on the payment mode chosen — matching
    # how the admin set things up for this specific project.
    from app.models.platform import Invoice
    amount = float(req.proposal_amount or 0)
    if payment_mode == "full":
        db.session.add(Invoice(project_id=proj.id, title="Full Payment", amount=amount, status="unpaid", created_by=None))
    elif payment_mode == "part":
        db.session.add(Invoice(project_id=proj.id, title="50% Deposit", amount=round(amount * 0.5, 2), status="unpaid", created_by=None))
    # after_service: no invoice yet — admin bills at completion

    from app.models.user import Role
    from app.models.core import Notification
    admin_role = Role.query.filter_by(name="admin").first()
    if admin_role:
        for admin_user in admin_role.users:
            db.session.add(Notification(
                user_id=admin_user.id, type="proposal_accepted", title="Proposal accepted!",
                body=f"{current_user.name or current_user.email} accepted the ${amount:.2f} proposal for \"{proj.title}\" — payment mode: {payment_mode.replace('_',' ')}.",
                link=url_for("admin.admin_project_detail", pid=proj.id),
            ))
    db.session.commit()
    flash("Proposal accepted! Your project is now underway.", "success")
    return redirect(url_for("cms.client_project", pid=proj.id))


@cms_bp.route("/my-requests/<int:rid>/request-meeting", methods=["POST"])
@login_required
def request_meeting(rid):
    from app.models.platform import ProjectMeeting
    from app.models.user import Role
    from app.models.core import Notification
    req = ProjectRequest.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
    if req.status != "quoted":
        flash("This proposal is no longer available.", "danger")
        return redirect(url_for("cms.my_requests"))
    preferred_raw = request.form.get("preferred_time", "").strip()
    if not preferred_raw:
        flash("Pick a preferred date/time first.", "danger")
        return redirect(url_for("cms.my_requests"))
    try:
        preferred_time = datetime.fromisoformat(preferred_raw)
    except ValueError:
        flash("Invalid date/time.", "danger")
        return redirect(url_for("cms.my_requests"))

    meeting = ProjectMeeting(
        request_id=req.id, title=f"Meeting requested — {req.project_type or 'proposal'}",
        scheduled_at=preferred_time, status="requested",
        notes=request.form.get("note", "").strip() or None,
    )
    db.session.add(meeting)

    admin_role = Role.query.filter_by(name="admin").first()
    if admin_role:
        for admin_user in admin_role.users:
            db.session.add(Notification(
                user_id=admin_user.id, type="meeting_requested",
                title="Meeting requested",
                body=f"{current_user.name or current_user.email} requested a meeting for "
                     f"{preferred_time.strftime('%b %d, %Y %I:%M %p')} about their proposal.",
                link=url_for("admin.project_requests"),
            ))
    db.session.commit()
    flash("Meeting requested — you'll hear back once it's confirmed.", "success")
    return redirect(url_for("cms.my_requests"))


@cms_bp.route("/my-requests/<int:rid>/decline", methods=["POST"])
@login_required
def decline_proposal(rid):
    req = ProjectRequest.query.filter_by(id=rid, user_id=current_user.id).first_or_404()
    req.status = "declined"
    db.session.commit()

    from app.models.user import Role
    from app.models.core import Notification
    admin_role = Role.query.filter_by(name="admin").first()
    if admin_role:
        for admin_user in admin_role.users:
            db.session.add(Notification(
                user_id=admin_user.id, type="proposal_declined", title="Proposal declined",
                body=f"{current_user.name or current_user.email} declined the proposal for \"{req.project_type or 'a project'}\".",
                link=url_for("admin.project_requests"),
            ))
    db.session.commit()
    flash("Proposal declined.", "info")
    return redirect(url_for("cms.my_requests"))


@cms_bp.route("/admin-preview/start/<int:uid>")
@login_required
def start_preview(uid):
    """Admin-only. Lets you see a specific real user's dashboard exactly as
    they see it — read-only, session-based, and never touches their actual
    account or role. Always exitable via the banner shown while active."""
    from flask import session
    if not current_user.is_admin():
        abort(403)
    target = User.query.get_or_404(uid)
    session["preview_user_id"] = target.id
    flash(f"Previewing as {target.name or target.email}. Exit anytime from the banner.", "info")
    if target.is_freelancer():
        return redirect(url_for("dashboard.home"))
    if target.is_client():
        return redirect(url_for("dashboard.home"))
    return redirect(url_for("dashboard.home"))


@cms_bp.route("/admin-preview/exit")
@login_required
def exit_preview():
    from flask import session
    session.pop("preview_user_id", None)
    flash("Exited preview mode.", "info")
    return redirect(url_for("admin.dashboard") if current_user.is_admin() else url_for("cms.home"))


@cms_bp.route("/account/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            current_user.name = name

        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename:
            import os, uuid
            ext = avatar_file.filename.rsplit(".", 1)[-1].lower() if "." in avatar_file.filename else "jpg"
            if ext not in {"png", "jpg", "jpeg", "gif", "webp"}:
                flash("Avatar must be an image (png, jpg, gif, or webp).", "danger")
                return redirect(url_for("cms.profile"))
            filename = f"{uuid.uuid4().hex}.{ext}"
            upload_dir = os.path.join(current_app.static_folder, "uploads", "avatars")
            os.makedirs(upload_dir, exist_ok=True)
            avatar_file.save(os.path.join(upload_dir, filename))
            current_user.avatar = f"/static/uploads/avatars/{filename}"

        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("cms.profile"))

    from app.models.commerce import Order
    from app.models.platform import ClientProject
    order_count = Order.query.filter_by(user_id=current_user.id).count()
    project_count = ClientProject.query.filter_by(client_id=current_user.id).count()
    badges = _dashboard_badges(current_user.id)
    from app.dashboard.premium import get_user_products
    products = get_user_products(current_user)
    return render_template("cms/profile.html", order_count=order_count, project_count=project_count, badges=badges, products=products)


@cms_bp.route("/my-projects")
@require_feature("client_mode_enabled")
@login_required
def my_projects():
    projects = ClientProject.query.filter_by(client_id=current_user.id).order_by(ClientProject.created_at.desc()).all()
    return render_template("cms/my_projects.html", projects=projects)


# ── Bank Transfer Payments ───────────────────────────────────────────────────
def _resolve_payable(kind, reference_id):
    """Shared by bank_transfer_pay and crypto_pay — resolves what's being
    paid for and enforces that the current user actually owns it."""
    from app.models.commerce import HostingSubscription, Order
    from app.models.platform import Invoice

    if kind == "hosting_subscription":
        obj = HostingSubscription.query.filter_by(id=reference_id, user_id=current_user.id).first_or_404()
        amount = obj.plan.annual_price if obj.billing_cycle == "annual" else obj.plan.monthly_price
        label = f"Hosting — {obj.domain}"
        redirect_to = url_for("dashboard.home")
    elif kind == "order":
        obj = Order.query.filter_by(id=reference_id, user_id=current_user.id).first_or_404()
        amount = obj.amount
        label = f"Order #{obj.id}"
        redirect_to = url_for("dashboard.home")
    elif kind == "invoice":
        obj = Invoice.query.get_or_404(reference_id)
        if obj.project.client_id != current_user.id:
            abort(404)
        amount = obj.remaining_amount
        label = f"{obj.project.title} — {obj.title}"
        redirect_to = url_for("cms.client_project", pid=obj.project_id)
    else:
        abort(404)
    return obj, float(amount), label, redirect_to


@cms_bp.route("/pay/bank-transfer/<kind>/<int:reference_id>", methods=["GET", "POST"])
@login_required
def bank_transfer_pay(kind, reference_id):
    from app.models.commerce import BankTransferPayment
    obj, amount, label, redirect_to = _resolve_payable(kind, reference_id)
    currency = getattr(obj, "currency", None) or default_site_currency()

    if request.method == "POST":
        sender_ref = (request.form.get("sender_reference") or "").strip()
        proof_img_url = None
        if "proof_image" in request.files:
            file = request.files["proof_image"]
            if file and file.filename:
                import uuid, os
                from werkzeug.utils import secure_filename
                ext = file.filename.split(".")[-1]
                filename = f"proof_{uuid.uuid4().hex}.{ext}"
                upload_dir = os.path.join(current_app.root_path, "static", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, filename))
                proof_img_url = f"/static/uploads/{filename}"
                
        db.session.add(BankTransferPayment(
            user_id=current_user.id, kind=kind, reference_id=reference_id,
            amount=amount, currency=currency, sender_reference=sender_ref, 
            proof_image=proof_img_url, status="pending",
        ))
        db.session.commit()
        flash("Payment submitted for review. You'll be notified once it's confirmed.", "success")
        return redirect(redirect_to)

    bank_details = {
        "bank_name": get_setting("bank_name", ""),
        "account_name": get_setting("bank_account_name", ""),
        "account_number": get_setting("bank_account_number", ""),
        "routing_swift": get_setting("bank_routing_swift", ""),
        "instructions": get_setting("bank_instructions", ""),
    }
    return render_template("cms/bank_transfer_pay.html", kind=kind, reference_id=reference_id,
                           amount=amount, label=label, bank_details=bank_details)


@cms_bp.route("/pay/crypto/<kind>/<int:reference_id>", methods=["GET", "POST"])
@login_required
def crypto_pay(kind, reference_id):
    from app.models.commerce import BankTransferPayment
    obj, amount, label, redirect_to = _resolve_payable(kind, reference_id)
    currency = getattr(obj, "currency", None) or default_site_currency()

    # Wallets are configured per-network in Admin -> Settings -> Crypto Payments.
    # Only networks with a wallet address actually filled in are offered.
    all_networks = [
        ("btc", "Bitcoin (BTC)"), ("eth", "Ethereum (ETH)"),
        ("usdt_trc20", "USDT (TRC20)"), ("usdt_erc20", "USDT (ERC20)"),
        ("usdc", "USDC"), ("bnb", "BNB (BEP20)"),
    ]
    wallets = {code: get_setting(f"crypto_wallet_{code}") for code, _ in all_networks}
    available = [(code, name, wallets[code]) for code, name in all_networks if wallets.get(code)]

    from app.utils.qr import generate_qr_data_uri
    qr_codes = {code: generate_qr_data_uri(address) for code, _, address in available}

    if request.method == "POST":
        network = request.form.get("network", "")
        tx_hash = (request.form.get("tx_hash") or "").strip()
        if not network or network not in wallets or not wallets[network]:
            flash("Please choose a valid network.", "danger")
            return redirect(url_for("cms.crypto_pay", kind=kind, reference_id=reference_id))
            
        proof_img_url = None
        if "proof_image" in request.files:
            file = request.files["proof_image"]
            if file and file.filename:
                import uuid, os
                ext = file.filename.split(".")[-1]
                filename = f"proof_{uuid.uuid4().hex}.{ext}"
                upload_dir = os.path.join(current_app.root_path, "static", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, filename))
                proof_img_url = f"/static/uploads/{filename}"

        db.session.add(BankTransferPayment(
            user_id=current_user.id, kind=kind, reference_id=reference_id,
            amount=amount, currency=currency, sender_reference=f"[{network}] tx: {tx_hash}", 
            proof_image=proof_img_url, status="pending",
        ))
        db.session.commit()
        flash("Payment submitted for review — I'll confirm it and message you once it's verified.", "success")
        return redirect(redirect_to)

    return render_template("cms/crypto_pay.html", kind=kind, reference_id=reference_id,
                           amount=amount, label=label, networks=available, qr_codes=qr_codes,
                           crypto_note=get_setting("crypto_instructions", ""))


def _notify_admins(message):
    from app.models.user import User
    from app.models.core import Notification
    admins = User.query.join(User.role).filter_by(name="admin").all()
    for admin in admins:
        db.session.add(Notification(user_id=admin.id, type="payment_link", title="Payment Link", body=message, read=False))
    db.session.commit()


@cms_bp.route("/pay/<slug>")
def payment_link_view(slug):
    from app.models.commerce import PaymentLink
    link = PaymentLink.query.filter_by(slug=slug).first_or_404()
    if link.status == "archived":
        return render_template("cms/payment_link_closed.html", link=link)
    if link.status != "published":
        abort(404)
    from app.utils.payments import get_enabled_gateways
    site_gateways = set(get_enabled_gateways())
    gateway_methods = [g for g in (link.allowed_methods or []) if g in ("paystack", "flutterwave", "paypal", "stripe") and g in site_gateways]
    manual_methods = [g for g in (link.allowed_methods or []) if g in ("bank_transfer", "crypto", "wave", "payoneer")]
    return render_template("cms/payment_link.html", link=link, gateway_methods=gateway_methods, manual_methods=manual_methods)


def _start_payment_link_gateway(link, gateway, payer_name, payer_email):
    from app.models.commerce import PaymentLinkPayment
    from types import SimpleNamespace
    payment = PaymentLinkPayment(payment_link_id=link.id, payer_name=payer_name, payer_email=payer_email,
                                  amount=link.amount, currency=link.currency, gateway=gateway, status="pending")
    db.session.add(payment)
    db.session.commit()
    fake_payer = SimpleNamespace(email=payer_email or "guest@example.com", name=payer_name or "Guest")

    if gateway == "paystack":
        from app.utils.payments import create_paystack_transaction
        data = create_paystack_transaction(link.title, float(link.amount), fake_payer,
            url_for("cms.payment_link_callback", slug=link.slug, gateway="paystack", payment_id=payment.id, _external=True),
            metadata={"payment_link_id": link.id, "payment_id": payment.id})
        payment.gateway_ref = data["reference"]
        db.session.commit()
        return redirect(data["authorization_url"], code=303)
    if gateway == "flutterwave":
        from app.utils.payments import create_flutterwave_transaction
        tx_ref = f"paylink-{payment.id}-{int(datetime.utcnow().timestamp())}"
        checkout_link = create_flutterwave_transaction(link.title, float(link.amount), fake_payer, tx_ref,
            url_for("cms.payment_link_callback", slug=link.slug, gateway="flutterwave", payment_id=payment.id, _external=True))
        payment.gateway_ref = tx_ref
        db.session.commit()
        return redirect(checkout_link, code=303)
    if gateway == "paypal":
        from app.utils.payments import create_paypal_order
        paypal_order_id, approval_url = create_paypal_order(link.title, float(link.amount),
            url_for("cms.payment_link_callback", slug=link.slug, gateway="paypal", payment_id=payment.id, _external=True),
            url_for("cms.payment_link_view", slug=link.slug, _external=True))
        payment.gateway_ref = paypal_order_id
        db.session.commit()
        return redirect(approval_url, code=303)
    if gateway == "stripe":
        from app.utils.payments import create_stripe_session
        session_obj = create_stripe_session(link.title, float(link.amount), fake_payer,
            url_for("cms.payment_link_callback", slug=link.slug, gateway="stripe", payment_id=payment.id, _external=True),
            url_for("cms.payment_link_view", slug=link.slug, _external=True),
            metadata={"payment_link_id": link.id, "payment_id": payment.id})
        payment.gateway_ref = session_obj.id
        db.session.commit()
        return redirect(session_obj.url, code=303)

    db.session.delete(payment)
    db.session.commit()
    abort(400)


@cms_bp.route("/pay/<slug>/checkout/<gateway>", methods=["POST"])
@limiter.limit("20 per hour")
def payment_link_checkout(slug, gateway):
    from app.models.commerce import PaymentLink
    link = PaymentLink.query.filter_by(slug=slug, status="published").first_or_404()
    payer_name = (request.form.get("payer_name") or "").strip()
    payer_email = (request.form.get("payer_email") or "").strip()
    if not payer_email:
        flash("Please enter your email so a receipt can be sent to you.", "danger")
        return redirect(url_for("cms.payment_link_view", slug=slug))
    try:
        return _start_payment_link_gateway(link, gateway, payer_name, payer_email)
    except Exception as e:
        current_app.logger.error(f"Payment link checkout error ({gateway}): {e}")
        flash(f"Payment could not be started: {e}", "danger")
        return redirect(url_for("cms.payment_link_view", slug=slug))


def _mark_payment_link_paid(payment):
    if payment.status == "paid":
        return
    payment.status = "paid"
    payment.paid_at = datetime.utcnow()
    db.session.commit()
    _notify_admins(f"Payment received: \"{payment.payment_link.title}\" — {payment.currency} {payment.amount} from {payment.payer_name or payment.payer_email}.")


@cms_bp.route("/pay/<slug>/callback/<gateway>/<int:payment_id>")
def payment_link_callback(slug, gateway, payment_id):
    from app.models.commerce import PaymentLink, PaymentLinkPayment
    link = PaymentLink.query.filter_by(slug=slug).first_or_404()
    payment = PaymentLinkPayment.query.filter_by(id=payment_id, payment_link_id=link.id).first_or_404()
    verified = False
    if gateway == "paystack":
        from app.utils.payments import verify_paystack_payment
        verified = bool(verify_paystack_payment(payment.gateway_ref))
    elif gateway == "flutterwave":
        from app.utils.payments import verify_flutterwave_payment
        transaction_id = request.args.get("transaction_id")
        verified = bool(verify_flutterwave_payment(transaction_id)) if transaction_id else False
    elif gateway == "paypal":
        from app.utils.payments import capture_paypal_order
        verified = bool(capture_paypal_order(payment.gateway_ref))
    elif gateway == "stripe":
        # Stripe's success_url only ever loads after a completed checkout —
        # the webhook (stripe_webhook, app/payments/routes.py) remains the
        # authoritative source that actually marks orders/payments paid in
        # production; this redirect just gets the buyer to a thank-you page.
        verified = True
    if verified:
        _mark_payment_link_paid(payment)
        if link.redirect_url:
            return redirect(link.redirect_url)
        return redirect(url_for("cms.payment_link_thanks", slug=slug, payment_id=payment.id))
    flash("We couldn't verify that payment. If you were charged, contact the seller with your email as reference.", "danger")
    return redirect(url_for("cms.payment_link_view", slug=slug))


@cms_bp.route("/pay/<slug>/thanks/<int:payment_id>")
def payment_link_thanks(slug, payment_id):
    from app.models.commerce import PaymentLink, PaymentLinkPayment
    link = PaymentLink.query.filter_by(slug=slug).first_or_404()
    payment = PaymentLinkPayment.query.filter_by(id=payment_id, payment_link_id=link.id).first_or_404()
    return render_template("cms/payment_link_thanks.html", link=link, payment=payment)


@cms_bp.route("/pay/<slug>/manual/<method>", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"])
def payment_link_manual(slug, method):
    """bank_transfer / crypto / wave / payoneer — none of these have a
    real-time API this app can confirm a payment through automatically
    (Wave and Payoneer don't expose a public checkout API at all), so the
    buyer submits proof of payment and the seller reviews/confirms it,
    same as the existing bank-transfer flow used for orders/invoices."""
    from app.models.commerce import PaymentLink, PaymentLinkPayment
    if method not in ("bank_transfer", "crypto", "wave", "payoneer"):
        abort(404)
    link = PaymentLink.query.filter_by(slug=slug, status="published").first_or_404()

    if request.method == "POST":
        payer_name = (request.form.get("payer_name") or "").strip()
        payer_email = (request.form.get("payer_email") or "").strip()
        sender_reference = (request.form.get("sender_reference") or "").strip()
        proof_img_url = None
        if "proof_image" in request.files:
            file = request.files["proof_image"]
            if file and file.filename:
                import uuid, os
                ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
                filename = f"paylink_{uuid.uuid4().hex}.{ext}"
                upload_dir = os.path.join(current_app.root_path, "static", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, filename))
                proof_img_url = f"/static/uploads/{filename}"
        payment = PaymentLinkPayment(payment_link_id=link.id, payer_name=payer_name, payer_email=payer_email,
                                      amount=link.amount, currency=link.currency, gateway=method,
                                      sender_reference=sender_reference, proof_image=proof_img_url, status="pending")
        db.session.add(payment)
        db.session.commit()
        _notify_admins(f"New {method.replace('_', ' ')} claim for \"{link.title}\" — {link.currency} {link.amount} from "
                        f"{payer_name or payer_email}. Review it in Admin -> Payment Links.")
        flash("Submitted! The seller will confirm your payment shortly.", "success")
        return redirect(url_for("cms.payment_link_thanks", slug=slug, payment_id=payment.id))

    ctx = {"link": link, "method": method}
    if method == "bank_transfer":
        ctx["bank_details"] = {
            "bank_name": get_setting("bank_name", ""), "account_name": get_setting("bank_account_name", ""),
            "account_number": get_setting("bank_account_number", ""), "routing_swift": get_setting("bank_routing_swift", ""),
            "instructions": get_setting("bank_instructions", ""),
        }
    elif method == "crypto":
        all_networks = [("btc", "Bitcoin (BTC)"), ("eth", "Ethereum (ETH)"), ("usdt_trc20", "USDT (TRC20)"),
                         ("usdt_erc20", "USDT (ERC20)"), ("usdc", "USDC"), ("bnb", "BNB (BEP20)")]
        wallets = {code: get_setting(f"crypto_wallet_{code}") for code, _ in all_networks}
        available = [(code, name, wallets[code]) for code, name in all_networks if wallets.get(code)]
        from app.utils.qr import generate_qr_data_uri
        ctx["networks"] = available
        ctx["qr_codes"] = {code: generate_qr_data_uri(address) for code, _, address in available}
    elif method == "wave":
        ctx["instructions"] = link.wave_instructions or get_setting("wave_instructions", "")
    elif method == "payoneer":
        ctx["instructions"] = link.payoneer_instructions or get_setting("payoneer_instructions", "")

    return render_template("cms/payment_link_manual.html", **ctx)


# ── SEO: robots.txt & sitemap.xml ────────────────────────────────────────────
@cms_bp.route("/robots.txt")
def robots_txt():
    from flask import Response
    custom = get_setting("seo_robots_txt", "")
    if custom.strip():
        body = custom
    else:
        body = """User-agent: *
Allow: /
Allow: /static/
Allow: /favicon.ico
Allow: /sitemap.xml
Disallow: /admin/
Disallow: /auth/
Disallow: /dashboard/
Disallow: /api/

User-agent: Googlebot-Image
Allow: /
Allow: /static/
Allow: /favicon.ico
"""
    body += f"\nSitemap: {request.url_root.rstrip('/')}/sitemap.xml\n"
    return Response(body, mimetype="text/plain")


@cms_bp.route("/sitemap.xml")
def sitemap_xml():
    from flask import Response
    from app.models.commerce import Product

    urls = [
        {"loc": url_for("cms.home", _external=True), "priority": "1.0"},
        {"loc": url_for("cms.about", _external=True), "priority": "0.9"},
        {"loc": url_for("cms.services", _external=True), "priority": "0.8"},
        {"loc": url_for("cms.works", _external=True), "priority": "0.8"},
        {"loc": url_for("cms.contact", _external=True), "priority": "0.6"},
    ]
    for svc in Service.query.filter_by(active=True).all():
        urls.append({"loc": url_for("cms.service_detail", service_id=svc.id, _external=True), "priority": "0.6"})
    for proj in Project.query.all():
        urls.append({
            "loc": url_for("cms.work_detail", identifier=proj.slug or proj.id, _external=True),
            "lastmod": proj.updated_at.strftime("%Y-%m-%d") if proj.updated_at else None, "priority": "0.6",
        })
    if feature_enabled("blog_enabled"):
        urls.append({"loc": url_for("cms.blog", _external=True), "priority": "0.8"})
        for post in BlogPost.query.filter_by(published=True).all():
            urls.append({
                "loc": url_for("cms.blog_post", slug=post.slug, _external=True),
                "lastmod": post.updated_at.strftime("%Y-%m-%d"), "priority": "0.7",
            })
    if feature_enabled("marketplace_enabled"):
        urls.append({"loc": url_for("marketplace.index", _external=True), "priority": "0.8"})
        for product in Product.query.filter_by(status="active").all():
            urls.append({
                "loc": url_for("marketplace.product_detail", slug=product.slug, _external=True),
                "priority": "0.6",
            })
    if feature_enabled("client_mode_enabled"):
        urls.append({"loc": url_for("cms.hire_me", _external=True), "priority": "0.9"})

    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append("<url>")
        xml.append(f"<loc>{u['loc']}</loc>")
        if u.get("lastmod"):
            xml.append(f"<lastmod>{u['lastmod']}</lastmod>")
        xml.append(f"<priority>{u['priority']}</priority>")
        xml.append("</url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


# ── Project Update Review Links (shareable, no login required) ──────────────
@cms_bp.route("/review/<token>", methods=["GET", "POST"])
def project_update_review(token):
    from app.models.platform import ProjectUpdate, ProjectUpdateComment
    update = ProjectUpdate.query.filter_by(review_token=token).first_or_404()

    if request.method == "POST":
        body = (request.form.get("body") or "").strip()
        if not body:
            flash("Comment cannot be empty.", "danger")
            return redirect(url_for("cms.project_update_review", token=token))
        comment = ProjectUpdateComment(update_id=update.id, body=body)
        if current_user.is_authenticated:
            comment.author_id = current_user.id
            comment.author_name = current_user.name
            comment.author_email = current_user.email
        else:
            comment.author_name = (request.form.get("name") or "Anonymous").strip()
            comment.author_email = (request.form.get("email") or "").strip()
        db.session.add(comment)
        db.session.commit()

        # Notify the admin/author of the update that feedback came in
        from app.utils.email import send_email
        from app.utils.settings import get_setting
        admin_email = get_setting("admin_notification_email")
        if admin_email:
            send_email(to=admin_email, subject=f"New feedback on: {update.project.title}",
                       body_html=f"<p><strong>{comment.author_name}</strong> commented:</p><p>{body}</p>")
        flash("Thanks for your feedback!", "success")
        return redirect(url_for("cms.project_update_review", token=token))

    comments = ProjectUpdateComment.query.filter_by(update_id=update.id).order_by(ProjectUpdateComment.created_at).all()
    return render_template("cms/project_review.html", update=update, comments=comments)


# ── Public customer-facing AI agent widget ──────────────────────────────────
# Deliberately conversation-only (see Agent model docstring) — no tool-calling,
# so a public visitor can't trigger real site actions. History lives in the
# browser session only (capped short — this is a signed client-side cookie,
# not server-side storage) so one visitor's chat never crosses into another's
# or into the admin's own conversation log with that agent.
_AGENT_WIDGET_HISTORY_CAP = 12  # messages (6 exchanges) kept in the session


@cms_bp.route("/chat/<int:agent_id>")
def agent_widget(agent_id):
    from app.models.core import Agent
    agent = Agent.query.get_or_404(agent_id)
    if not agent.active or not agent.customer_facing:
        abort(404)
    history = session.get(f"agent_widget_{agent_id}", [])
    return render_template("cms/agent_widget.html", agent=agent, history=history)


@cms_bp.route("/chat/<int:agent_id>/send", methods=["POST"])
def agent_widget_send(agent_id):
    from app.models.core import Agent
    from app.ai_tools.routes import _call_ai
    agent = Agent.query.get_or_404(agent_id)
    if not agent.active or not agent.customer_facing:
        abort(404)

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message can't be empty"}), 400
    if len(message) > 2000:
        return jsonify({"error": "That message is too long."}), 400

    session_key = f"agent_widget_{agent_id}"
    history = session.get(session_key, [])
    history.append({"role": "user", "content": message})

    from app.utils.knowledge import search_knowledge_base, format_knowledge_results
    knowledge_context = format_knowledge_results(search_knowledge_base(message, limit=5))

    system = (
        f"You are {agent.name}" + (f", the {agent.role}" if agent.role else "")
        + f" at this business, talking directly with a website visitor/customer. Your instructions: {agent.instructions}\n\n"
        "You do NOT have any tools or the ability to take real actions — you can only have a helpful "
        "conversation. If asked to do something you can't (book something, change an order, etc), say so "
        "plainly and suggest they contact the business directly. Keep replies concise and friendly.\n\n"
        f"Real information from the site that may be relevant to their message:\n{knowledge_context}\n\n"
        "If this list doesn't actually answer what they asked, say you don't have that information rather "
        "than inventing a service, price, or project that isn't listed above."
    )
    text, err = _call_ai(system, history, max_tokens=800)
    if err:
        return jsonify({"error": "Sorry, I'm not available right now — please try again shortly."})

    history.append({"role": "assistant", "content": text or ""})
    session[session_key] = history[-_AGENT_WIDGET_HISTORY_CAP:]
    return jsonify({"response": text})


# ── Embeddable branded chatbot widget (for pasting on ANY site, including
# other people's) ────────────────────────────────────────────────────────
# Deliberately separate from the widget above: an embed runs inside an
# iframe on a THIRD-PARTY page, so it can't rely on this site's session
# cookie reliably reaching it (modern browsers' SameSite cookie rules
# don't guarantee a cross-site iframe's fetch calls carry it) — so
# conversation history is round-tripped in the request body by the
# client's own JS instead of kept server-side, and this endpoint is CSRF-
# exempt for the same cross-site reason (real bots/webhooks in this app
# use the same pattern — see `csrf.exempt(social_bp)`). Same tool-free,
# knowledge-grounded behavior as the same-site widget above.
_EMBED_HISTORY_CAP = 12


@cms_bp.route("/embed/chat/<int:agent_id>")
def agent_embed(agent_id):
    from app.models.core import Agent
    agent = Agent.query.get_or_404(agent_id)
    if not agent.active or not agent.customer_facing:
        abort(404)
    return render_template("cms/agent_embed.html", agent=agent)


@cms_bp.route("/embed/chat/<int:agent_id>/send", methods=["POST"])
@limiter.limit("30 per minute")
def agent_embed_send(agent_id):
    from app.models.core import Agent
    from app.ai_tools.routes import _call_ai
    agent = Agent.query.get_or_404(agent_id)
    if not agent.active or not agent.customer_facing:
        abort(404)

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []
    if not message:
        return jsonify({"error": "Message can't be empty"}), 400
    if len(message) > 2000:
        return jsonify({"error": "That message is too long."}), 400
    if not isinstance(history, list) or len(history) > _EMBED_HISTORY_CAP:
        history = []
    # Only trust role/content shape from the client — nothing else.
    clean_history = [{"role": m.get("role"), "content": str(m.get("content", ""))[:2000]}
                      for m in history if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    clean_history.append({"role": "user", "content": message})

    from app.utils.knowledge import search_knowledge_base, format_knowledge_results
    knowledge_context = format_knowledge_results(search_knowledge_base(message, limit=5))

    system = (
        f"You are {agent.name}" + (f", the {agent.role}" if agent.role else "")
        + f" — you're embedded as a chat widget on a website talking with a visitor. Your instructions: {agent.instructions}\n\n"
        "You do NOT have any tools or the ability to take real actions — you can only have a helpful "
        "conversation. If asked to do something you can't, say so plainly and suggest they contact the "
        "business directly. Keep replies concise and friendly.\n\n"
        f"Real information from the site that may be relevant to their message:\n{knowledge_context}\n\n"
        "If this list doesn't actually answer what they asked, say you don't have that information rather "
        "than inventing a service, price, or project that isn't listed above."
    )
    text, err = _call_ai(system, clean_history, max_tokens=800)
    if err:
        return jsonify({"error": "Sorry, I'm not available right now — please try again shortly."})
    return jsonify({"response": text})

