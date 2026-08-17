"""
Feature flags — every protected route calls check_feature() which reads
from DB (via get_setting) and aborts with a nice maintenance/disabled page.
"""
from functools import wraps
from flask import abort, render_template, redirect, url_for, request
from app.utils.settings import get_setting


def feature_enabled(key, default=True):
    """Return bool for a feature-flag setting key."""
    val = get_setting(key, str(default).lower())
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes", "on")


def require_feature(setting_key, default=True):
    """Decorator: abort 503 if feature is disabled in DB."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if get_setting("maintenance_mode", "false") in ("true", "True", True, "1"):
                return render_template("errors/maintenance.html"), 503
            if not feature_enabled(setting_key, default):
                return render_template("errors/feature_disabled.html",
                                       feature=setting_key.replace("_", " ").replace(" enabled", "").title()), 503
            return f(*args, **kwargs)
        return decorated
    return decorator
