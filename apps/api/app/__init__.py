"""
Application Factory
"""
import os
from flask import Flask, render_template, request, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache

from app.extensions import db, migrate, login_manager, mail, csrf, limiter, cache
from app.utils.settings import get_setting
from app.utils.template_filters import register_filters
from app.utils.audit import log_action


def create_app(config_env=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # --- Configuration ---
    if config_env is None:
        config_env = os.environ.get("FLASK_ENV", "development")

    if config_env == "production":
        from config import ProductionConfig
        app.config.from_object(ProductionConfig)
    elif config_env == "testing":
        from config import TestingConfig
        app.config.from_object(TestingConfig)
    else:
        from config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)

    # Override with environment variables (e.g., DATABASE_URL)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", app.config.get("SQLALCHEMY_DATABASE_URI")
    )
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", app.config.get("SECRET_KEY"))

    # --- Error logging ---
    # There was no logging configuration at all before this — Flask's
    # default logger only writes to stderr, which on many hosts (including
    # PythonAnywhere) either isn't captured anywhere accessible or gets
    # lost between worker restarts. This writes every WARNING-and-above
    # (including unhandled 500 errors) to a real rotating log file so
    # they're actually visible, in addition to stderr.
    if not app.debug and not app.testing:
        import logging
        from logging.handlers import RotatingFileHandler
        log_dir = os.path.join(app.root_path, "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(os.path.join(log_dir, "app_errors.log"), maxBytes=1_000_000, backupCount=3)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s"))
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.WARNING)

    # --- Initialize Extensions ---
    _init_extensions(app)
    _register_blueprints(app)
    _register_context_processors(app)
    _register_error_handlers(app)
    register_filters(app)
    _register_admin_idle_timeout(app)

    # Background automation worker — see app/utils/job_queue.py's
    # docstring for exactly what this does and doesn't guarantee
    # (in-process, single-process only; not a Celery replacement).
    # Without this call, trigger() still enqueues jobs just fine (see
    # automation.py) but nothing ever dequeues and runs them — every
    # automation-triggered event would pile up in memory and simply
    # never execute, with no error anywhere to signal that.
    from app.utils.job_queue import start_worker
    start_worker(app)

    return app


def _init_extensions(app):
    """Initialize all Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login_manager.init_app(app)
    mail.init_app(app)
    # WTF_CSRF_SSL_STRICT defaults to True, which additionally checks that
    # the browser's Referer header matches this site's host whenever the
    # request is HTTPS. Behind a host's own reverse proxy (PythonAnywhere,
    # etc.) or when a browser simply doesn't send Referer (privacy
    # settings, some referrer-policy configurations, long-open tabs),
    # that check fails even with a perfectly valid CSRF token — surfacing
    # as exactly the intermittent "CSRF error" pattern reported on
    # actions clicked a while after the page loaded (Run Backup, Page
    # Speed Check) rather than on quick immediate ones. The token itself
    # is still fully validated; only the extra Referer check is relaxed.
    app.config.setdefault("WTF_CSRF_SSL_STRICT", False)
    # Flask-WTF's CSRF token defaults to expiring after 1 hour (WTF_CSRF_TIME_LIMIT),
    # completely independent of the session itself, which lasts 30 days
    # (PERMANENT_SESSION_LIFETIME above). That mismatch is a second, distinct
    # cause of "CSRF error" reports — anyone who loads a page (the AI Console,
    # an Agent chat, a long admin form) and comes back to submit it more than
    # an hour later gets a token that's still tied to a perfectly valid
    # session but has separately expired on its own clock. Tying the token's
    # lifetime to the session's removes that surprise entirely.
    app.config.setdefault("WTF_CSRF_TIME_LIMIT", None)
    csrf.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)

    @limiter.request_filter
    def _exempt_logged_in_admins_from_global_rate_limit():
        # The global 200/day, 50/hour default limit exists to slow down
        # anonymous abuse (credential stuffing, scraping, etc.). It was
        # also silently applying to every logged-in admin's own dashboard
        # traffic — Content Studio, the AI Console, AI Agent tests, Leads
        # searches, all sharing one 50-per-hour bucket per IP — so normal
        # admin work could trip it, and (until the 429 page below was
        # added) crash outright instead of showing a real message. Routes
        # that still need their OWN tighter limit (e.g. @limiter.limit(...)
        # on login/forgot-password) are unaffected — this only lifts the
        # blanket default for people who are already authenticated admins.
        try:
            from flask_login import current_user
            return current_user.is_authenticated and current_user.is_admin()
        except Exception:
            return False

    # Login manager settings
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    @login_manager.unauthorized_handler
    def unauthorized():
        # AJAX/API calls must never get redirected to the HTML login page —
        # fetch()'s res.json() would then fail on the '<!DOCTYPE html>'
        # response with a confusing parse error. Any request that is JSON,
        # expects JSON, or targets an /api/ path gets a proper 401 instead.
        wants_json = (
            request.is_json
            or request.accept_mimetypes.best == "application/json"
            or "/api/" in request.path
        )
        if wants_json:
            from flask import jsonify
            # A bare 401 here used to leave every AI-tool fetch() call with
            # no way to route the person back to where they were — the
            # frontend had nothing to redirect to except a hardcoded
            # "/login" (which drops them at the dashboard afterward,
            # instead of back on the tool page). Including login_url with
            # ?next= already pointed at the CURRENT tool page fixes that
            # for every tool at once, from one place, instead of needing
            # every individual tool's JS to build that URL itself. See
            # the matching fetch-wrapper in partials/navbar.html.
            return jsonify({
                "error": "Please log in to use this tool.",
                "login_required": True,
                "login_url": url_for(login_manager.login_view, next=request.referrer or request.url),
            }), 401
        from flask import flash
        flash(login_manager.login_message, login_manager.login_message_category)
        return redirect(url_for(login_manager.login_view, next=request.url))

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))


def _register_blueprints(app):
    """Register all blueprints."""
    from app.admin.routes import admin_bp
    from app.auth.routes import auth_bp
    from app.telephony.routes import telephony_bp
    from app.marketplace.routes import marketplace_bp
    from app.blog.routes import blog_bp
    from app.freelance.routes import freelance_bp
    from app.hosting.routes import hosting_bp
    from app.ai_tools.routes import ai_bp
    from app.ai_tools.browser_tools import ai_browser_bp
    from app.tools.routes import tools_bp
    from app.portfolio.routes import portfolio_bp
    from app.payments.routes import payments_bp
    from app.analytics.routes import analytics_bp
    from app.api.routes import api_bp
    from app.comms.routes import comms_bp
    from app.shorturl.routes import shorturl_bp
    from app.social.routes import social_bp
    from app.dashboard.routes import dashboard_bp

    # URL prefixes
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(telephony_bp)
    from app.cms.routes import cms_bp
    app.register_blueprint(cms_bp, url_prefix="/")
    app.register_blueprint(marketplace_bp, url_prefix="/marketplace")
    app.register_blueprint(blog_bp, url_prefix="/blog")
    app.register_blueprint(freelance_bp, url_prefix="/hire")
    app.register_blueprint(hosting_bp, url_prefix="/hosting")
    app.register_blueprint(ai_bp, url_prefix="/ai")
    app.register_blueprint(ai_browser_bp, url_prefix="/ai")
    app.register_blueprint(tools_bp, url_prefix="/tools")
    app.register_blueprint(portfolio_bp, url_prefix="/portfolio")
    app.register_blueprint(payments_bp, url_prefix="/payments")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(comms_bp, url_prefix="/messages")
    app.register_blueprint(shorturl_bp, url_prefix="/")
    app.register_blueprint(social_bp, url_prefix="/")

    # Webhook endpoints receive POSTs from external services with no
    # session cookie and no CSRF token — only the secret baked into each
    # URL authenticates them. CSRFProtect blocks any POST without a valid
    # token by default, which would 400 every inbound bot message and
    # (pre-existing, same gap) every Stripe webhook call.
    csrf.exempt(social_bp)
    csrf.exempt(telephony_bp)
    # Only exempt if the endpoint actually exists
    if "payments.stripe_webhook" in app.view_functions:
        csrf.exempt(app.view_functions["payments.stripe_webhook"])
    # Public funnel-page beacons and website form submissions have no
    # CSRF token either (anonymous visitors, no session) — same category
    # as the webhooks above. NOTE: calling csrf.exempt(view_func) from
    # INSIDE the view function itself (as these two previously did) does
    # NOT work — CSRFProtect's before_request check runs before the view
    # body executes, so that pattern only ever appears to work by never
    # actually being exercised. Exemption has to be registered here, at
    # app-setup time, same as everything else in this block.
    if "dashboard.funnel_track" in app.view_functions:
        csrf.exempt(app.view_functions["dashboard.funnel_track"])
    if "dashboard.site_submit_form" in app.view_functions:
        csrf.exempt(app.view_functions["dashboard.site_submit_form"])
    if "dashboard.site_submit_form_by_slug" in app.view_functions:
        csrf.exempt(app.view_functions["dashboard.site_submit_form_by_slug"])
    for _endpoint in ("dashboard.site_data_create", "dashboard.site_data_update", "dashboard.site_data_delete"):
        if _endpoint in app.view_functions:
            csrf.exempt(app.view_functions[_endpoint])
    # WhatsApp Chat Widget view/click beacons — same anonymous-visitor,
    # no-session, no-CSRF-token situation as the two above.
    if "dashboard.whatsapp_widget_view" in app.view_functions:
        csrf.exempt(app.view_functions["dashboard.whatsapp_widget_view"])
    if "dashboard.whatsapp_widget_click" in app.view_functions:
        csrf.exempt(app.view_functions["dashboard.whatsapp_widget_click"])
    # Embed-widget messages come from a THIRD-PARTY page's iframe — this
    # site's session/CSRF cookie can't reliably reach a cross-site iframe
    # under modern SameSite rules, so this one endpoint is exempted (like
    # the webhooks above) and protected by rate-limiting instead.
    if "cms.agent_embed_send" in app.view_functions:
        csrf.exempt(app.view_functions["cms.agent_embed_send"])


def _register_context_processors(app):
    """Register global template context processors."""
    from app.utils.settings import get_setting
    app.jinja_env.globals["get_setting"] = get_setting

    @app.context_processor
    def inject_settings():
        from app.models.core import SiteSetting
        settings = {}
        try:
            for s in SiteSetting.query.all():
                settings[s.key] = s.value
        except Exception:
            pass
        return {"settings": settings}

    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return {"current_user": current_user}

    @app.context_processor
    def inject_cart_count():
        return {"cart_count": 0}

    @app.context_processor
    def inject_currency_switcher():
        from flask import g
        from app.utils.currency import SUPPORTED_CURRENCIES, base_currency, get_rates
        base = base_currency()
        # Only offer currencies that actually have a manual rate set (plus
        # the base itself) — an entry here always converts to something real.
        codes = [base] + sorted(c for c in get_rates() if c != base)
        return {
            "currency_switcher_options": [(c, SUPPORTED_CURRENCIES[c]) for c in codes if c in SUPPORTED_CURRENCIES],
            "active_display_currency": getattr(g, "currency", base),
        }

    # ✅ ADDED – makes site_name and site_tagline available in all templates
    @app.context_processor
    def inject_site_name():
        from app.models.core import SiteSetting
        site_name = SiteSetting.query.filter_by(key='site_name').first()
        site_tagline = SiteSetting.query.filter_by(key='site_tagline').first()
        return {
            'site_name': site_name.value if site_name else 'Bazillin Studio',
            'site_tagline': site_tagline.value if site_tagline else 'Build. Ship. Scale.'
        }


def _wants_json():
    return (
        request.is_json
        or request.accept_mimetypes.best == "application/json"
        or "/api/" in request.path
    )


def _register_error_handlers(app):
    """Register custom error pages."""
    from flask_wtf.csrf import CSRFError
    from flask import jsonify

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        if _wants_json():
            return jsonify({"error": f"Security check failed ({e.description}). Please refresh the page and try again."}), 400
        return render_template("errors/400.html", reason=e.description), 400

    @app.errorhandler(400)
    def bad_request(e):
        if _wants_json():
            return jsonify({"error": getattr(e, "description", "Bad request.")}), 400
        return render_template("errors/400.html", reason=getattr(e, "description", "")), 400

    @app.errorhandler(401)
    def unauthorized_error(e):
        if _wants_json():
            return jsonify({"error": "Please log in to continue."}), 401
        return redirect(url_for("auth.login", next=request.url))

    @app.errorhandler(415)
    def unsupported_media(e):
        if _wants_json():
            return jsonify({"error": "Request format not supported."}), 415
        return render_template("errors/400.html", reason="Unsupported request format."), 415

    @app.errorhandler(403)
    def forbidden(e):
        if _wants_json():
            return jsonify({"error": "You don't have permission to do that."}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        if _wants_json():
            return jsonify({"error": "Not found."}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        if _wants_json():
            return jsonify({"error": "Something went wrong on our end. Please try again."}), 500
        return render_template("errors/500.html"), 500

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        if _wants_json():
            return jsonify({"error": "Too many requests — please slow down and try again shortly."}), 429
        return render_template("errors/429.html"), 429

def _register_admin_idle_timeout(app):
    """Logs admin accounts out after 10 minutes of inactivity. Scoped to
    admins only — a 10-minute timeout would be a bad experience for a
    customer browsing the marketplace, but is a sensible security
    default for the account with full site control."""
    import datetime
    from flask_login import current_user, logout_user
    from flask import session, redirect, url_for, request

    IDLE_LIMIT_SECONDS = 10 * 60

    @app.before_request
    def _set_display_currency():
        """Default is ONE currency everywhere — whatever the admin set in
        Settings -> Payment Config -> site_currency (this is what actual
        prices are stored/entered in, and what admin reports fall back
        to). A visitor MAY override that for their own session via the
        currency switcher (POST /set-currency/<code>) — that override is
        display-only, scoped to their session, and restricted to
        currencies the admin has set a manual rate for, so it can never
        silently show a made-up conversion. This replaces an earlier
        version of this hook that removed per-visitor switching entirely
        after a bug where an unvalidated override caused stale dollar
        signs to stick around after the admin switched the site to
        Naira — the fix here is validating the override, not removing it."""
        from flask import g, session
        from app.utils.currency import base_currency, get_rates
        base = base_currency()
        override = (session.get("display_currency") or "").upper()
        if override and override != base and override not in get_rates():
            # rate was removed/renamed since the visitor picked it — fall
            # back to the base currency rather than converting through a
            # rate that no longer exists
            session.pop("display_currency", None)
            override = ""
        g.currency = override or base

    @app.before_request
    def _set_current_organization():
        from flask import g
        # For now everything still runs as your own single organization
        # ("My Studio", created by the multi-tenant migration) — this is
        # what keeps every existing AI key, bot, and workflow working
        # exactly as before. A real per-client organization switcher
        # (so a bot/workflow you build FOR a client lives under THEIR
        # organization instead) is the next step, not wired in yet.
        from app.models.tenant import Organization
        g.current_org = Organization.query.filter_by(slug="my-studio").first()

    @app.before_request
    def _capture_referral_code():
        # Someone clicked a referral link like yoursite.com/?ref=CODE —
        # remember it for this visitor's session so that IF they later
        # submit the hire-me form, that lead gets attributed to whoever
        # the code belongs to. Doesn't validate the code here (that's a
        # DB lookup on every single request) — validated once, at the
        # point it's actually used.
        ref = request.args.get("ref")
        if ref:
            session["referral_code"] = ref[:32]

    @app.before_request
    def _check_admin_idle_timeout():
        if not current_user.is_authenticated or not getattr(current_user, "is_admin", lambda: False)():
            return
        if request.endpoint in ("static",):
            return
        now = datetime.datetime.utcnow().timestamp()
        last_seen = session.get("admin_last_seen")
        if last_seen is not None and (now - last_seen) > IDLE_LIMIT_SECONDS:
            logout_user()
            session.pop("admin_last_seen", None)
            if request.blueprint == "admin" or request.path.startswith("/admin"):
                return redirect(url_for("auth.login", timeout="1"))
            return
        session["admin_last_seen"] = now