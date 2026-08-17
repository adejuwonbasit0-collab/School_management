from datetime import datetime
from flask import Blueprint, redirect, url_for, flash, request, jsonify, abort, current_app, render_template, g
from flask_login import login_required, current_user
from app.extensions import db
from app.models.commerce import Product, Order
from app.utils.analytics import log_event

payments_bp = Blueprint("payments", __name__)

GATEWAY_LABELS = {
    "stripe": "Credit / Debit Card (Stripe)",
    "paystack": "Paystack",
    "flutterwave": "Flutterwave",
    "paypal": "PayPal",
    "bank_transfer": "Bank Transfer",
    "crypto": "Cryptocurrency (BTC/ETH/USDT/USDC)",
}


def _mark_order_paid(order):
    """Marks a marketplace order paid and sends the two emails that were
    completely missing before: a purchase receipt to the customer, and a
    sale notification to the admin. Every one of the 5 places that used to
    set `order.status = "paid"` (Stripe webhook, Paystack/Flutterwave/PayPal
    callbacks, and the generic `/success` redirect) had zero email logic —
    not a bug in existing code, this simply was never built. Idempotent: a
    webhook and a customer's browser redirect can both legitimately fire
    for the same order, so this only sends once (guarded on prior status).
    """
    if order.status == "paid":
        return  # already processed by another path (webhook + redirect race) — don't double-email
    order.status = "paid"
    db.session.commit()
    log_event("purchase", path=f"/product/{order.product_id}", value=order.amount,
              metadata={"order_id": order.id, "gateway": order.gateway})

    # Auto-unlock premium dashboard products
    try:
        from app.dashboard.premium import PREMIUM_PRODUCTS, grant_product_access
        from app.utils.notifications import notify_user
        product = order.product
        if product and product.slug in PREMIUM_PRODUCTS:
            grant_product_access(order.user, product.slug, order=order)
            info = PREMIUM_PRODUCTS[product.slug]
            link = url_for(info["endpoint"]) if info.get("endpoint") else None
            notify_user(
                order.user_id,
                type="product_unlocked",
                title="🎉 Payment Successful",
                body=f"{product.title} has been unlocked.",
                link=link,
            )
            db.session.commit()
    except Exception:
        # Don't break the payment flow if premium unlock fails — but a
        # silent `pass` here means a customer can pay successfully and
        # stay locked out with zero trace of why. Log it so this is
        # actually debuggable instead of a mystery "I paid but nothing
        # unlocked" report.
        current_app.logger.exception(
            "grant_product_access failed after payment for order_id=%s "
            "user_id=%s product_id=%s — customer paid but was NOT unlocked. "
            "This usually means a pending `flask db upgrade` (missing "
            "UserProductAccess table/columns).",
            order.id, order.user_id, order.product_id,
        )

    from app.utils.email import send_email
    from app.utils.settings import get_setting
    customer = order.user
    product = order.product
    product_name = product.title if product else f"Order #{order.id}"
    amount_str = f"{order.currency or 'USD'} {order.amount}"

    if customer and customer.email:
        send_email(
            to=customer.email,
            subject=f"Your purchase: {product_name}",
            body_html=f"""<p>Thanks for your purchase{f', {customer.name}' if customer.name else ''}!</p>
                <p><strong>{product_name}</strong><br>Amount paid: {amount_str}</p>
                <p>You can download it anytime from your dashboard.</p>""",
        )

    admin_email = get_setting("admin_email") or get_setting("contact_email")
    if admin_email:
        send_email(
            to=admin_email,
            subject=f"💰 New sale — {product_name}",
            body_html=f"""<p><strong>{customer.name if customer and customer.name else (customer.email if customer else 'A customer')}</strong>
                just purchased <strong>{product_name}</strong> for {amount_str} via {GATEWAY_LABELS.get(order.gateway, order.gateway or 'unknown gateway')}.</p>""",
        )

@payments_bp.route("/checkout/<int:product_id>")
@login_required
def checkout(product_id):
    from app.utils.payments import get_enabled_gateways
    product = Product.query.get_or_404(product_id)
    if product.type == "premium_tool":
        # Premium dashboard tools are owned via UserProductAccess (with a
        # self-healing fallback onto paid Orders), not a raw Order lookup —
        # using a different check here than the rest of the app used to
        # cause a real deadlock: this route would say "already owned"
        # while the product page still said "not owned", with no way out.
        from app.dashboard.premium import has_product_access
        if has_product_access(current_user, product.slug):
            flash("You already own this product.", "info")
            return redirect(url_for("marketplace.product_detail", slug=product.slug))
    else:
        already = Order.query.filter_by(user_id=current_user.id, product_id=product_id, status="paid").first()
        if already:
            flash("You already own this product.", "info")
            return redirect(url_for("marketplace.product_detail", slug=product.slug))

    enabled = get_enabled_gateways()
    if not enabled:
        flash("No payment methods are configured yet on this site. Please contact us directly to arrange payment.", "danger")
        return redirect(url_for("marketplace.product_detail", slug=product.slug))

    from app.utils.payments import resolve_checkout_currency
    preferred_currency = getattr(g, "currency", None)
    gateway_list = [(gw, GATEWAY_LABELS.get(gw, gw.title())) for gw in enabled]
    gateway_currencies = {gw: resolve_checkout_currency(gw, preferred_currency)[0] for gw, _ in gateway_list}
    return render_template("payments/choose_gateway.html", product=product,
                           gateways=gateway_list, gateway_currencies=gateway_currencies)


@payments_bp.route("/checkout/addon/<slug>")
@login_required
def checkout_addon(slug):
    from app.models.platform import PremiumModule
    from app.models.commerce import Product
    from app.utils.payments import get_enabled_gateways
    
    module = PremiumModule.query.filter_by(slug=slug, active=True).first_or_404()
    
    # 1. Check if user already has access
    from app.dashboard.premium import has_product_access
    if has_product_access(current_user, slug):
        flash("You already own this premium module.", "info")
        return redirect(url_for("dashboard.home"))
        
    # 2. Get or create the underlying product record for checkout processing
    prod = Product.query.filter_by(slug=slug).first()
    if not prod:
        prod = Product(
            title=module.name,
            slug=module.slug,
            price=module.price,
            status="addon", # Hidden from store list
            type="premium_tool",
            description=f"Premium module addon: {module.name}"
        )
        db.session.add(prod)
        db.session.commit()
    else:
        # Sync price
        prod.price = module.price
        db.session.commit()
        
    # 3. Choose payment gateway
    enabled = get_enabled_gateways()
    if not enabled:
        flash("No payment methods are configured yet on this site. Please contact us directly to arrange payment.", "danger")
        return redirect(url_for("dashboard.home"))
        
    return render_template("payments/choose_gateway.html", product=prod,
                           gateways=[(g, GATEWAY_LABELS.get(g, g.title())) for g in enabled])


@payments_bp.route("/checkout/<int:product_id>/<gateway>")
@login_required
def checkout_with_gateway(product_id, gateway):
    product = Product.query.get_or_404(product_id)
    already = Order.query.filter_by(user_id=current_user.id, product_id=product_id, status="paid").first()
    if already:
        flash("You already own this product.", "info")
        return redirect(url_for("marketplace.product_detail", slug=product.slug))

    # Charge in the currency the visitor picked with the site-wide currency
    # switcher, IF this gateway can actually process it — otherwise fall
    # back to the site's base currency rather than sending a gateway a
    # currency it will just reject. Either way, the amount is converted
    # from the product's own listed currency (product.price is entered by
    # the admin in product.currency, which may not be the site's base
    # currency) into whatever we're actually charging, and the Order
    # records THAT real charged amount/currency — never the product's
    # original listing — because Financials and Analytics depend on
    # Order.amount/currency reflecting what the customer was actually
    # charged, not what the product page happened to show them.
    from app.utils.payments import resolve_checkout_currency
    from app.utils.currency import convert
    preferred_currency = getattr(g, "currency", None)
    charge_currency, matched_preference = resolve_checkout_currency(gateway, preferred_currency)
    charge_amount = round(convert(product.effective_price, product.currency, charge_currency), 2)

    order = Order(user_id=current_user.id, product_id=product_id, amount=charge_amount,
                  currency=charge_currency, gateway=gateway, status="pending")
    db.session.add(order)
    db.session.commit()

    if not matched_preference and preferred_currency and preferred_currency != charge_currency:
        flash(f"{GATEWAY_LABELS.get(gateway, gateway)} doesn't support {preferred_currency} yet, "
              f"so you'll be charged {charge_amount} {charge_currency} instead.", "info")

    try:
        if gateway == "stripe":
            from app.utils.payments import create_stripe_session
            session = create_stripe_session(
                product.title, charge_amount, current_user,
                url_for("payments.success", order_id=order.id, _external=True),
                url_for("marketplace.product_detail", slug=product.slug, _external=True),
                metadata={"product_id": product.id, "user_id": current_user.id},
                currency=charge_currency,
            )
            order.gateway_ref = session.id
            db.session.commit()
            return redirect(session.url, code=303)
        if gateway == "paystack":
            from app.utils.payments import create_paystack_transaction
            data = create_paystack_transaction(
                product.title, charge_amount, current_user,
                url_for("payments.paystack_callback", order_id=order.id, _external=True),
                metadata={"product_id": product.id, "user_id": current_user.id},
                currency=charge_currency,
            )
            order.gateway_ref = data["reference"]
            db.session.commit()
            return redirect(data["authorization_url"], code=303)
        if gateway == "flutterwave":
            from app.utils.payments import create_flutterwave_transaction
            tx_ref = f"order-{order.id}-{int(datetime.utcnow().timestamp())}"
            link = create_flutterwave_transaction(
                product.title, charge_amount, current_user, tx_ref,
                url_for("payments.flutterwave_callback", order_id=order.id, _external=True),
                currency=charge_currency,
            )
            order.gateway_ref = tx_ref
            db.session.commit()
            return redirect(link, code=303)
        if gateway == "paypal":
            from app.utils.payments import create_paypal_order
            paypal_order_id, approval_url = create_paypal_order(
                product.title, charge_amount,
                url_for("payments.paypal_capture", order_id=order.id, _external=True),
                url_for("marketplace.product_detail", slug=product.slug, _external=True),
                currency=charge_currency,
            )
            order.gateway_ref = paypal_order_id
            db.session.commit()
            return redirect(approval_url, code=303)
        if gateway == "bank_transfer":
            return redirect(url_for("cms.bank_transfer_pay", kind="order", reference_id=order.id))
        if gateway == "crypto":
            return redirect(url_for("cms.crypto_pay", kind="order", reference_id=order.id))
        flash(f"{GATEWAY_LABELS.get(gateway, gateway)} isn't fully configured yet.", "danger")
        db.session.delete(order)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Checkout error: {e}")
        flash(f"Payment could not be initiated: {e}", "danger")
        db.session.delete(order)
        db.session.commit()
    return redirect(url_for("marketplace.product_detail", slug=product.slug))


@payments_bp.route("/paystack/callback/<int:order_id>")
@login_required
def paystack_callback(order_id):
    from app.utils.payments import verify_paystack_payment, reconcile_charged_currency
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    result = verify_paystack_payment(order.gateway_ref)
    if result:
        # Paystack can silently process a transaction in a different
        # currency than requested if the account isn't actually approved
        # for the one we asked for — trust what Paystack confirms it
        # charged over what we intended, so Order/Financials stay correct.
        mismatched = reconcile_charged_currency(order, result.get("currency"), result.get("amount"), is_minor_unit=True)
        _mark_order_paid(order)
        if mismatched:
            current_app.logger.warning(
                f"Order #{order.id}: Paystack charged {order.currency} instead of the requested "
                f"currency — account likely isn't approved for that currency yet. Corrected the "
                f"order record to match what was actually charged.")
            flash(f"Payment successful! (Charged in {order.currency} — your Paystack account may "
                  f"not be approved for the currency you selected; set it up in Payment Config -> "
                  f"Enabled Currencies once approved.)", "success")
        else:
            flash("Payment successful! You can now download your product.", "success")
    else:
        flash("We couldn't verify that payment. If you were charged, contact support.", "danger")
    return redirect(url_for("dashboard.home"))


@payments_bp.route("/flutterwave/callback/<int:order_id>")
@login_required
def flutterwave_callback(order_id):
    from app.utils.payments import verify_flutterwave_payment, reconcile_charged_currency
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    transaction_id = request.args.get("transaction_id")
    result = verify_flutterwave_payment(transaction_id) if transaction_id else None
    if result:
        # Flutterwave amounts are in major units already (not kobo/cents).
        mismatched = reconcile_charged_currency(order, result.get("currency"), result.get("amount"), is_minor_unit=False)
        _mark_order_paid(order)
        if mismatched:
            current_app.logger.warning(f"Order #{order.id}: Flutterwave charged {order.currency} instead of the requested currency.")
            flash(f"Payment successful! (Charged in {order.currency} — that gateway account may not "
                  f"be approved for the currency you selected.)", "success")
        else:
            flash("Payment successful! You can now download your product.", "success")
    else:
        flash("We couldn't verify that payment. If you were charged, contact support.", "danger")
    return redirect(url_for("dashboard.home"))

@payments_bp.route("/paypal/capture/<int:order_id>")
@login_required
def paypal_capture(order_id):
    from app.utils.payments import capture_paypal_order, reconcile_charged_currency
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    result = capture_paypal_order(order.gateway_ref)
    if result:
        try:
            captured = result["purchase_units"][0]["payments"]["captures"][0]["amount"]
            mismatched = reconcile_charged_currency(order, captured.get("currency_code"), captured.get("value"), is_minor_unit=False)
        except (KeyError, IndexError, TypeError):
            mismatched = False
        _mark_order_paid(order)
        if mismatched:
            current_app.logger.warning(f"Order #{order.id}: PayPal charged {order.currency} instead of the requested currency.")
            flash(f"Payment successful! (Charged in {order.currency}.)", "success")
        else:
            flash("Payment successful! You can now download your product.", "success")
    else:
        flash("We couldn't verify that payment. If you were charged, contact support.", "danger")
    return redirect(url_for("dashboard.home"))


@payments_bp.route("/success/<int:order_id>")
@login_required
def success(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    _mark_order_paid(order)
    product = order.product

    # Dashboard add-on purchases don't have anything to "download" — buying
    # one unlocks a dashboard feature (already happened above, inside
    # _mark_order_paid, regardless of whether the buyer clicks anything on
    # this page), so send them straight there instead of a generic page.
    if product and product.type == "premium_tool":
        from app.dashboard.premium import PREMIUM_PRODUCTS
        info = PREMIUM_PRODUCTS.get(product.slug)
        if info and info.get("endpoint"):
            flash(f"Payment successful! '{product.title}' is unlocked — set it up below.", "success")
            return redirect(url_for(info["endpoint"]))
        flash(f"Payment successful! The '{product.title}' premium module is now unlocked and active.", "success")
    else:
        flash("Payment successful! You can now download your product.", "success")
    return redirect(url_for("dashboard.home"))

@payments_bp.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    import stripe
    payload = request.data
    sig = request.headers.get("Stripe-Signature", "")
    secret = current_app.config.get("STRIPE_WEBHOOK_SECRET", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
        if event["type"] == "checkout.session.completed":
            sess = event["data"]["object"]
            order = Order.query.filter_by(gateway_ref=sess["id"]).first()
            if order:
                order.gateway_ref = sess.get("payment_intent", order.gateway_ref)
                _mark_order_paid(order)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True})


# ── Invoice payments (client project billing) ───────────────────────────────
def _get_owned_invoice(invoice_id):
    from app.models.platform import Invoice
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.project.client_id != current_user.id:
        abort(404)
    return invoice


@payments_bp.route("/invoice/<int:invoice_id>/pdf")
@login_required
def invoice_pdf(invoice_id):
    from flask import send_file
    from app.models.platform import Invoice
    from app.utils.invoice_pdf import generate_invoice_pdf
    from app.utils.settings import get_setting
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.project.client_id != current_user.id and not current_user.is_admin():
        abort(404)
    pdf = generate_invoice_pdf(invoice, site_name=get_setting("site_name", "Bazillin Studio"))
    return send_file(pdf, mimetype="application/pdf", as_attachment=False,
                     download_name=f"invoice-{invoice.id}.pdf")


def _generate_receipt_reference():
    """Short, human-typeable reference — not a raw UUID — so a client can
    read it off a screenshot or printed receipt without difficulty."""
    import secrets
    from app.models.platform import Receipt
    for _ in range(10):
        ref = "RCT-" + secrets.token_hex(4).upper()
        if not Receipt.query.filter_by(reference=ref).first():
            return ref
    raise RuntimeError("Could not generate a unique receipt reference")


def _mark_invoice_paid(invoice, gateway_ref=None):
    invoice.status = "paid"
    invoice.amount_paid = invoice.amount
    invoice.paid_at = datetime.utcnow()
    if gateway_ref:
        invoice.gateway_ref = gateway_ref
    db.session.commit()

    from app.models.platform import Receipt
    if not Receipt.query.filter_by(invoice_id=invoice.id).first():
        receipt = Receipt(
            invoice_id=invoice.id, reference=_generate_receipt_reference(),
            amount=invoice.amount, currency=invoice.currency,
            payment_method=invoice.gateway, paid_at=invoice.paid_at,
        )
        db.session.add(receipt)
        db.session.commit()

    log_event("invoice_payment", path=f"/client/project/{invoice.project_id}", value=invoice.amount,
              metadata={"invoice_id": invoice.id, "gateway": invoice.gateway})
    # Notify + email the client's project owner (admin) that payment landed
    from app.models.core import Notification
    from app.utils.email import send_email
    from app.utils.settings import get_setting
    admin_email = get_setting("admin_email") or get_setting("contact_email")
    notify_user_id = invoice.created_by or invoice.project.client_id
    db.session.add(Notification(
        user_id=notify_user_id, type="invoice_paid", title="Invoice paid",
        body=f"{invoice.project.client.name} paid \"{invoice.title}\" (${invoice.amount}) on {invoice.project.title}.",
        link=url_for("admin.admin_project_detail", pid=invoice.project_id),
    ))
    db.session.commit()
    if admin_email:
        send_email(to=admin_email, subject=f"💰 Invoice paid — {invoice.project.title}",
                    body_html=f"<p><strong>{invoice.project.client.name}</strong> just paid <strong>{invoice.title}</strong> "
                              f"(${invoice.amount} {invoice.currency}) on project <strong>{invoice.project.title}</strong>.</p>")
    # The client who actually paid never got anything before this — only
    # the admin notification above existed. Real receipt for the person
    # who paid, separate from the admin alert.
    client = invoice.project.client
    if client and client.email:
        send_email(
            to=client.email,
            subject=f"Receipt — {invoice.title}",
            body_html=f"""<p>Hi {client.name or 'there'},</p>
                <p>This confirms your payment of <strong>{invoice.currency or 'USD'} {invoice.amount}</strong>
                for <strong>{invoice.title}</strong> on <strong>{invoice.project.title}</strong>.</p>
                <p>You can view your invoice and download a PDF receipt anytime from your project dashboard.</p>""",
        )


@payments_bp.route("/invoice/<int:invoice_id>/checkout")
@login_required
def invoice_checkout(invoice_id):
    from app.utils.payments import get_enabled_gateways
    from app.utils.wallet import get_or_create_wallet
    invoice = _get_owned_invoice(invoice_id)
    if invoice.status == "paid":
        flash("This invoice is already paid.", "info")
        return redirect(url_for("cms.client_project", pid=invoice.project_id))

    enabled = get_enabled_gateways()
    wallet = get_or_create_wallet(current_user.id)
    remaining = invoice.remaining_amount
    wallet_balance = float(wallet.balance or 0)
    wallet_sufficient = wallet_balance >= remaining
    wallet_partial_available = 0 < wallet_balance < remaining

    if not enabled and not wallet_sufficient and not wallet_partial_available:
        flash("No payment methods are configured yet on this site, and your wallet balance isn't enough to cover this. Please contact us directly to arrange payment.", "danger")
        return redirect(url_for("cms.client_project", pid=invoice.project_id))

    return render_template("payments/choose_gateway.html", invoice=invoice, product=None,
                           gateways=[(g, GATEWAY_LABELS.get(g, g.title())) for g in enabled],
                           wallet=wallet, wallet_sufficient=wallet_sufficient,
                           wallet_partial_available=wallet_partial_available, remaining=remaining)


@payments_bp.route("/invoice/<int:invoice_id>/checkout/<gateway>")
@login_required
def invoice_checkout_with_gateway(invoice_id, gateway):
    invoice = _get_owned_invoice(invoice_id)
    if invoice.status == "paid":
        flash("This invoice is already paid.", "info")
        return redirect(url_for("cms.client_project", pid=invoice.project_id))

    # Charge whatever's actually still owed — if a wallet payment already
    # covered part of this invoice, the gateway should only charge the rest.
    charge_amount = invoice.remaining_amount
    title = f"{invoice.project.title} — {invoice.title}"
    try:
        if gateway == "stripe":
            from app.utils.payments import create_stripe_session
            session = create_stripe_session(
                title, charge_amount, current_user,
                url_for("payments.invoice_success", invoice_id=invoice.id, _external=True),
                url_for("cms.client_project", pid=invoice.project_id, _external=True),
                metadata={"invoice_id": invoice.id},
            )
            invoice.gateway, invoice.gateway_ref = gateway, session.id
            db.session.commit()
            return redirect(session.url, code=303)
        if gateway == "paystack":
            from app.utils.payments import create_paystack_transaction
            data = create_paystack_transaction(
                title, charge_amount, current_user,
                url_for("payments.invoice_paystack_callback", invoice_id=invoice.id, _external=True),
                metadata={"invoice_id": invoice.id},
            )
            invoice.gateway, invoice.gateway_ref = gateway, data["reference"]
            db.session.commit()
            return redirect(data["authorization_url"], code=303)
        if gateway == "flutterwave":
            from app.utils.payments import create_flutterwave_transaction
            tx_ref = f"invoice-{invoice.id}-{int(datetime.utcnow().timestamp())}"
            link = create_flutterwave_transaction(
                title, charge_amount, current_user, tx_ref,
                url_for("payments.invoice_flutterwave_callback", invoice_id=invoice.id, _external=True),
            )
            invoice.gateway, invoice.gateway_ref = gateway, tx_ref
            db.session.commit()
            return redirect(link, code=303)
        if gateway == "paypal":
            from app.utils.payments import create_paypal_order
            paypal_order_id, approval_url = create_paypal_order(
                title, charge_amount,
                url_for("payments.invoice_paypal_capture", invoice_id=invoice.id, _external=True),
                url_for("cms.client_project", pid=invoice.project_id, _external=True),
            )
            invoice.gateway, invoice.gateway_ref = gateway, paypal_order_id
            db.session.commit()
            return redirect(approval_url, code=303)
        if gateway == "bank_transfer":
            return redirect(url_for("cms.bank_transfer_pay", kind="invoice", reference_id=invoice.id))
        if gateway == "crypto":
            return redirect(url_for("cms.crypto_pay", kind="invoice", reference_id=invoice.id))
        flash(f"{GATEWAY_LABELS.get(gateway, gateway)} isn't fully configured yet.", "danger")
    except Exception as e:
        current_app.logger.error(f"Invoice checkout error: {e}")
        flash(f"Payment could not be initiated: {e}", "danger")
    return redirect(url_for("cms.client_project", pid=invoice.project_id))


@payments_bp.route("/invoice/<int:invoice_id>/success")
@login_required
def invoice_success(invoice_id):
    invoice = _get_owned_invoice(invoice_id)
    _mark_invoice_paid(invoice)
    flash("Payment successful — thank you!", "success")
    return redirect(url_for("cms.client_project", pid=invoice.project_id))


@payments_bp.route("/invoice/<int:invoice_id>/paystack/callback")
@login_required
def invoice_paystack_callback(invoice_id):
    from app.utils.payments import verify_paystack_payment
    invoice = _get_owned_invoice(invoice_id)
    result = verify_paystack_payment(invoice.gateway_ref)
    if result:
        _mark_invoice_paid(invoice)
        flash("Payment successful — thank you!", "success")
    else:
        flash("We couldn't verify that payment. If you were charged, contact support.", "danger")
    return redirect(url_for("cms.client_project", pid=invoice.project_id))


@payments_bp.route("/invoice/<int:invoice_id>/flutterwave/callback")
@login_required
def invoice_flutterwave_callback(invoice_id):
    from app.utils.payments import verify_flutterwave_payment
    invoice = _get_owned_invoice(invoice_id)
    transaction_id = request.args.get("transaction_id")
    result = verify_flutterwave_payment(transaction_id) if transaction_id else None
    if result:
        _mark_invoice_paid(invoice)
        flash("Payment successful — thank you!", "success")
    else:
        flash("We couldn't verify that payment. If you were charged, contact support.", "danger")
    return redirect(url_for("cms.client_project", pid=invoice.project_id))


@payments_bp.route("/invoice/<int:invoice_id>/paypal/capture")
@login_required
def invoice_paypal_capture(invoice_id):
    from app.utils.payments import capture_paypal_order
    invoice = _get_owned_invoice(invoice_id)
    result = capture_paypal_order(invoice.gateway_ref)
    if result:
        _mark_invoice_paid(invoice)
        flash("Payment successful — thank you!", "success")
    else:
        flash("We couldn't verify that payment. If you were charged, contact support.", "danger")
    return redirect(url_for("cms.client_project", pid=invoice.project_id))


# ── Receipts ─────────────────────────────────────────────────────────────
@payments_bp.route("/receipt/<int:invoice_id>/pdf")
@login_required
def receipt_pdf(invoice_id):
    from flask import send_file
    from app.models.platform import Receipt, Invoice
    from app.utils.receipt_pdf import generate_receipt_pdf
    from app.utils.settings import get_setting
    if current_user.is_admin():
        invoice = Invoice.query.get_or_404(invoice_id)
    else:
        invoice = _get_owned_invoice(invoice_id)
    receipt = Receipt.query.filter_by(invoice_id=invoice.id).first()
    if not receipt:
        flash("No receipt exists for this invoice yet — it may not be paid.", "danger")
        return redirect(url_for("cms.client_project", pid=invoice.project_id))
    verify_url = url_for("payments.verify_receipt", reference=receipt.reference, _external=True)
    pdf = generate_receipt_pdf(receipt, verify_url, site_name=get_setting("site_name", "Bazillin Studio"))
    return send_file(pdf, mimetype="application/pdf", as_attachment=False,
                     download_name=f"receipt-{receipt.reference}.pdf")


@payments_bp.route("/verify/<reference>")
def verify_receipt(reference):
    """Public page — deliberately shows only non-sensitive confirmation
    (reference, amount, currency, paid date) so a receipt can be verified
    by anyone holding it without exposing client identity or project
    details to whoever scans the QR code."""
    from app.models.platform import Receipt
    from app.utils.currency import format_amount
    receipt = Receipt.query.filter_by(reference=reference).first()
    return render_template("payments/verify_receipt.html", receipt=receipt,
                           amount_str=format_amount(float(receipt.amount), receipt.currency) if receipt else None)


# ── Wallet ───────────────────────────────────────────────────────────────
@payments_bp.route("/wallet")
@login_required
def wallet_dashboard():
    from app.utils.wallet import get_or_create_wallet
    from app.models.platform import WithdrawalRequest
    wallet = get_or_create_wallet(current_user.id)
    withdrawals = WithdrawalRequest.query.filter_by(user_id=current_user.id).order_by(
        WithdrawalRequest.created_at.desc()).all()
    return render_template("payments/wallet.html", wallet=wallet, withdrawals=withdrawals)


@payments_bp.route("/wallet/transfer", methods=["POST"])
@login_required
def wallet_transfer():
    from app.utils.wallet import transfer_wallet
    from app.models.user import User
    from app.admin.routes import _parse_amount
    email = (request.form.get("email") or "").strip().lower()
    amount = _parse_amount(request.form.get("amount"))

    recipient = User.query.filter(db.func.lower(User.email) == email).first()
    if not recipient:
        flash(f"No account found with email {email}.", "danger")
        return redirect(url_for("payments.wallet_dashboard"))
    if amount <= 0:
        flash("Amount must be greater than zero.", "danger")
        return redirect(url_for("payments.wallet_dashboard"))

    ok, err = transfer_wallet(current_user.id, recipient.id, amount,
                              note=f"Transfer from {current_user.email}")
    if not ok:
        flash(err, "danger")
    else:
        flash(f"Sent to {recipient.email}.", "success")
    return redirect(url_for("payments.wallet_dashboard"))


@payments_bp.route("/wallet/withdraw", methods=["POST"])
@login_required
def wallet_withdraw():
    """Requests a withdrawal — the wallet is debited immediately (reserved)
    so the same balance can't also be spent or transferred while the
    request is pending; admin fulfils it manually outside the platform
    (there's no outbound payout API integration) and marks it paid."""
    from decimal import Decimal
    from app.utils.wallet import debit_wallet
    from app.models.platform import WithdrawalRequest
    from app.admin.routes import _parse_amount
    destination = (request.form.get("destination") or "").strip()
    amount = _parse_amount(request.form.get("amount"))

    if not destination:
        flash("Tell us where to send the funds (bank details or other payout info).", "danger")
        return redirect(url_for("payments.wallet_dashboard"))
    if amount <= 0:
        flash("Amount must be greater than zero.", "danger")
        return redirect(url_for("payments.wallet_dashboard"))

    wallet, err = debit_wallet(current_user.id, amount, kind="withdrawal_request",
                               note="Withdrawal requested — pending admin fulfillment",
                               reference=None, created_by=current_user.id)
    if err:
        flash(err, "danger")
        return redirect(url_for("payments.wallet_dashboard"))

    req = WithdrawalRequest(user_id=current_user.id, amount=Decimal(str(amount)),
                            currency=wallet.currency, destination=destination, status="pending")
    db.session.add(req)
    db.session.commit()
    flash("Withdrawal requested — your balance has been reserved and we'll process it shortly.", "success")
    return redirect(url_for("payments.wallet_dashboard"))


@payments_bp.route("/invoice/<int:invoice_id>/pay-with-wallet", methods=["POST"])
@login_required
def invoice_pay_with_wallet(invoice_id):
    from decimal import Decimal
    from app.utils.wallet import debit_wallet, get_or_create_wallet
    invoice = _get_owned_invoice(invoice_id)
    if invoice.status == "paid":
        flash("This invoice is already paid.", "info")
        return redirect(url_for("cms.client_project", pid=invoice.project_id))

    wallet = get_or_create_wallet(current_user.id)
    remaining = Decimal(str(invoice.remaining_amount))
    available = Decimal(str(wallet.balance or 0))
    if available <= 0:
        flash("Your wallet balance is empty. Try another payment method or top up your wallet.", "danger")
        return redirect(url_for("payments.invoice_checkout", invoice_id=invoice.id))

    # Apply as much as the wallet can cover — full or partial — rather than
    # requiring the whole invoice to be covered in one go.
    apply_amount = min(available, remaining)
    wallet, err = debit_wallet(
        current_user.id, apply_amount, kind="invoice_payment",
        note=f'Paid invoice "{invoice.title}"', reference=f"invoice:{invoice.id}",
        created_by=current_user.id,
    )
    if err:
        flash(f"Couldn't pay from wallet: {err}. Try another payment method or top up your wallet balance.", "danger")
        return redirect(url_for("payments.invoice_checkout", invoice_id=invoice.id))

    invoice.amount_paid = Decimal(str(invoice.amount_paid or 0)) + apply_amount
    db.session.commit()

    if invoice.amount_paid >= Decimal(str(invoice.amount)):
        invoice.gateway = "wallet"
        _mark_invoice_paid(invoice, gateway_ref=f"wallet-{current_user.id}")
        flash("Paid from your wallet balance — thank you!", "success")
        return redirect(url_for("cms.client_project", pid=invoice.project_id))

    invoice.status = "partial"
    db.session.commit()
    still_owed = invoice.remaining_amount
    from app.utils.currency import format_amount
    flash(f"Applied {format_amount(float(apply_amount), invoice.currency)} from your wallet — "
          f"{format_amount(still_owed, invoice.currency)} still remaining, pick another payment method to finish.", "success")
    return redirect(url_for("payments.invoice_checkout", invoice_id=invoice.id))


