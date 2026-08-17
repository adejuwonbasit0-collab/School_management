from flask import g
from app.extensions import db


def _resolve_org_id(organization_id=None):
    """Every existing get_setting()/set_setting() call site in the codebase
    stays unchanged — this just resolves WHICH organization's copy of a
    setting to read/write, based on the request's current org (set by
    _load_current_organization in app/__init__.py). That's what makes an
    org's own AI keys, SMTP config, Google service account, etc. isolated
    from every other org's, without having to touch every call site."""
    if organization_id is not None:
        return organization_id
    org = getattr(g, "current_org", None)
    return org.id if org else None


def get_setting(key, default=None, organization_id=None):
    try:
        from app.models.core import SiteSetting
        org_id = _resolve_org_id(organization_id)
        s = SiteSetting.query.filter_by(key=key, organization_id=org_id).first()
        if s is None:
            return default
        return s.typed_value()
    except Exception:
        return default


def default_site_currency():
    """Used as a SQLAlchemy column default (a callable, evaluated per-row
    at insert time) so new records pick up whatever currency the site is
    ACTUALLY configured for right now, instead of a value frozen in at
    import time. Fixes the bug where every new Order/Invoice/Transaction
    silently defaulted to USD even after the admin switched the whole
    site's currency to Naira in Settings."""
    return get_setting("site_currency") or "NGN"


def set_setting(key, value, value_type="string", group="general", label=None, organization_id=None):
    from app.models.core import SiteSetting
    org_id = _resolve_org_id(organization_id)
    s = SiteSetting.query.filter_by(key=key, organization_id=org_id).first()
    if s:
        s.value = str(value)
        s.value_type = value_type
    else:
        s = SiteSetting(key=key, value=str(value), value_type=value_type, group=group, label=label or key, organization_id=org_id)
        db.session.add(s)
    db.session.commit()
    return s
