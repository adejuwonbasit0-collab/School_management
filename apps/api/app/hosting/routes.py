from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app.models.commerce import HostingPlan, HostingSubscription
from app.extensions import db
from app.utils.feature_flags import require_feature
from app.utils.settings import get_setting
from app.hosting.domain_utils import (
    check_domain_availability, validate_subdomain_format, RESERVED_SUBDOMAINS,
)

hosting_bp = Blueprint("hosting", __name__)


def _base_domain():
    return get_setting("hosting_base_domain", "bazillinapps.com")


@hosting_bp.route("/")
@require_feature("hosting_portal_enabled")
def index():
    plans = HostingPlan.query.filter_by(active=True).order_by(HostingPlan.order).all()
    return render_template("hosting/index.html", plans=plans, base_domain=_base_domain())


@hosting_bp.route("/api/check-subdomain")
@require_feature("hosting_portal_enabled")
def api_check_subdomain():
    value = (request.args.get("value") or "").strip().lower()
    ok, error = validate_subdomain_format(value)
    if not ok:
        return jsonify({"available": False, "error": error})
    taken = HostingSubscription.query.filter_by(subdomain=value).filter(
        HostingSubscription.status != "cancelled"
    ).first()
    if taken:
        return jsonify({"available": False, "error": "That subdomain is already taken."})
    return jsonify({"available": True, "full": f"{value}.{_base_domain()}"})


@hosting_bp.route("/api/check-domain", methods=["POST"])
@login_required
@require_feature("hosting_portal_enabled")
def api_check_domain():
    """Real WHOIS-based availability check for a domain the user wants to
    register or already owns — doesn't purchase anything, just checks."""
    domain = (request.get_json(silent=True) or {}).get("domain", "")
    result = check_domain_availability(domain)
    return jsonify(result)


@hosting_bp.route("/subscribe/<int:plan_id>", methods=["POST"])
@login_required
@require_feature("hosting_portal_enabled")
def subscribe(plan_id):
    plan = HostingPlan.query.get_or_404(plan_id)
    cycle = request.form.get("billing_cycle", "monthly")
    domain_type = request.form.get("domain_type", "subdomain")

    if domain_type == "subdomain":
        subdomain = (request.form.get("subdomain") or "").strip().lower()
        ok, error = validate_subdomain_format(subdomain)
        if not ok:
            flash(error, "danger")
            return redirect(url_for("hosting.index"))
        if HostingSubscription.query.filter_by(subdomain=subdomain).filter(
            HostingSubscription.status != "cancelled"
        ).first():
            flash(f'"{subdomain}" is already taken — please choose another.', "danger")
            return redirect(url_for("hosting.index"))
        domain_value = f"{subdomain}.{_base_domain()}"
    else:
        own_domain = (request.form.get("domain") or "").strip().lower()
        if not own_domain or "." not in own_domain:
            flash("Please enter a valid domain name.", "danger")
            return redirect(url_for("hosting.index"))
        subdomain = None
        domain_value = own_domain

    price = float(plan.annual_price if cycle == "annual" else plan.monthly_price)
    sub = HostingSubscription(
        user_id=current_user.id,
        plan_id=plan_id,
        domain=domain_value,
        domain_type=domain_type,
        subdomain=subdomain,
        dns_verified=(domain_type == "subdomain"),  # subdomains are ours, always "verified"
        billing_cycle=cycle,
        status="pending",
        auto_renew=True,
    )
    db.session.add(sub)
    db.session.commit()

    from app.utils.payments import get_enabled_gateways
    enabled = get_enabled_gateways()
    if len(enabled) <= 1:
        gw = enabled[0] if enabled else "bank_transfer"
        return _redirect_to_hosting_gateway(sub, gw)
    return render_template("hosting/choose_gateway.html", sub=sub, price=price,
                           gateways=[(g, g.replace('_', ' ').title()) for g in enabled])


def _redirect_to_hosting_gateway(sub, gateway):
    price = float(sub.plan.annual_price if sub.billing_cycle == "annual" else sub.plan.monthly_price)
    title = f"Hosting — {sub.domain}"
    try:
        if gateway == "stripe":
            from app.utils.payments import create_stripe_session
            session = create_stripe_session(
                title, price, current_user,
                url_for("dashboard.home", _external=True),
                url_for("hosting.index", _external=True),
                metadata={"hosting_subscription_id": sub.id},
            )
            return redirect(session.url, code=303)
        if gateway == "paystack":
            from app.utils.payments import create_paystack_transaction
            data = create_paystack_transaction(
                title, price, current_user,
                url_for("hosting.paystack_callback", sub_id=sub.id, _external=True),
                metadata={"hosting_subscription_id": sub.id},
            )
            return redirect(data["authorization_url"], code=303)
        if gateway == "flutterwave":
            from app.utils.payments import create_flutterwave_transaction
            tx_ref = f"hosting-{sub.id}-{int(datetime.utcnow().timestamp())}"
            link = create_flutterwave_transaction(title, price, current_user, tx_ref,
                url_for("hosting.index", _external=True))
            return redirect(link, code=303)
    except Exception as e:
        flash(f"Payment could not be initiated: {e}", "danger")
        return redirect(url_for("hosting.index"))
    # bank_transfer (default/fallback)
    flash(f"Hosting subscription for {sub.domain} submitted! Complete payment to activate.", "success")
    return redirect(url_for("cms.bank_transfer_pay", kind="hosting_subscription", reference_id=sub.id))


@hosting_bp.route("/checkout/<int:sub_id>/<gateway>")
@login_required
@require_feature("hosting_portal_enabled")
def checkout_with_gateway(sub_id, gateway):
    sub = HostingSubscription.query.filter_by(id=sub_id, user_id=current_user.id).first_or_404()
    return _redirect_to_hosting_gateway(sub, gateway)


@hosting_bp.route("/paystack/callback/<int:sub_id>")
@login_required
def paystack_callback(sub_id):
    from app.utils.payments import verify_paystack_payment
    sub = HostingSubscription.query.filter_by(id=sub_id, user_id=current_user.id).first_or_404()
    result = verify_paystack_payment(request.args.get("reference", ""))
    if result:
        sub.status = "active"
        db.session.commit()
        flash("Payment successful — your hosting is now active!", "success")
    else:
        flash("We couldn't verify that payment. If you were charged, contact support.", "danger")
    return redirect(url_for("dashboard.home"))


@hosting_bp.route("/dns-instructions/<int:sub_id>")
@login_required
@require_feature("hosting_portal_enabled")
def dns_instructions(sub_id):
    """Shows the DNS records a 'bring your own domain' user needs to add —
    standard pattern for any hosting panel connecting an external domain."""
    sub = HostingSubscription.query.filter_by(id=sub_id, user_id=current_user.id).first_or_404()
    if sub.domain_type != "own_domain":
        abort(404)
    return render_template("hosting/dns_instructions.html", sub=sub,
                           server_ip=get_setting("hosting_server_ip", "203.0.113.10"))
