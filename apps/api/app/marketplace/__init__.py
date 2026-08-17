"""
Application Factory
"""
import os
from flask import Flask, render_template, request
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

    # --- Initialize Extensions ---
    _init_extensions(app)
    _register_blueprints(app)
    _register_context_processors(app)
    _register_error_handlers(app)
    register_filters(app)

    return app


def _init_extensions(app):
    """Initialize all Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)

    # Login manager settings
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))


def _register_blueprints(app):
    """Register all blueprints."""
    from app.admin.routes import admin_bp
    from app.auth.routes import auth_bp
    from app.cms.routes import cms_bp
    from app.marketplace.routes import marketplace_bp
    from app.blog.routes import blog_bp
    from app.freelance.routes import freelance_bp
    from app.hosting.routes import hosting_bp
    from app.ai_tools.routes import ai_bp
    from app.tools.routes import tools_bp
    from app.portfolio.routes import portfolio_bp
    from app.payments.routes import payments_bp
    from app.analytics.routes import analytics_bp
    from app.api.routes import api_bp
    from app.comms.routes import comms_bp

    # URL prefixes
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(cms_bp, url_prefix="/")          # homepage, about, contact, etc.
    app.register_blueprint(marketplace_bp, url_prefix="/marketplace")
    app.register_blueprint(blog_bp, url_prefix="/blog")
    app.register_blueprint(freelance_bp, url_prefix="/hire")
    app.register_blueprint(hosting_bp, url_prefix="/hosting")
    app.register_blueprint(ai_bp, url_prefix="/ai")
    app.register_blueprint(tools_bp, url_prefix="/tools")
    app.register_blueprint(portfolio_bp, url_prefix="/portfolio")
    app.register_blueprint(payments_bp, url_prefix="/payments")
    app.register_blueprint(analytics_bp, url_prefix="/analytics")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(comms_bp, url_prefix="/messages")


def _register_context_processors(app):
    """Register global template context processors."""
    @app.context_processor
    def inject_settings():
        from app.models.core import SiteSetting
        settings = {}
        for s in SiteSetting.query.all():
            settings[s.key] = s.value
        return {"settings": settings}

    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return {"current_user": current_user}

    @app.context_processor
    def inject_cart_count():
        # Example: if you have a cart system
        from flask_login import current_user
        count = 0
        if current_user.is_authenticated:
            from app.models.commerce import Cart
            cart = Cart.query.filter_by(user_id=current_user.id).first()
            if cart:
                count = sum(item.quantity for item in cart.items)
        return {"cart_count": count}


def _register_error_handlers(app):
    """Register custom error pages."""
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return render_template("errors/429.html"), 429