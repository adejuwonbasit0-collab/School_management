"""Checkout page rendering for the Sales Funnel Builder's Checkout page
type. A Checkout page's `settings.checkout` config (product name, price,
currency, description) plus the funnel owner's connected payment
gateways (from app.utils.payments.get_user_enabled_gateways) is enough
to render a complete, self-contained buyer-facing checkout page — same
idea as app/utils/funnel_blocks.py's render_blocks_to_html(), just for
one specific, purpose-built page type instead of freeform blocks.

The actual charge is created by the existing, already-in-production
app.utils.payments helpers (create_stripe_session, create_paystack_
transaction, etc.) via the /funnels/<subdomain>/<page_slug>/checkout/
<gateway> route in app/dashboard/routes.py — this module only renders
the page the buyer sees before they click "Pay".
"""
import html as _html


def _e(value):
    return _html.escape(str(value or ""), quote=True)


GATEWAY_LABELS = {
    "stripe": "Pay with Card (Stripe)",
    "paystack": "Pay with Paystack",
    "flutterwave": "Pay with Flutterwave",
    "paypal": "Pay with PayPal",
}


def render_checkout_page_html(page, checkout, gateways, action_base_url, csrf_token, extra_content_html=""):
    """
    page:  FunnelPage — used for title only
    checkout: dict — {"product_name","price","currency","description"}
    gateways: list[str] — gateway keys the funnel owner has connected & enabled
    action_base_url: str — e.g. "/dashboard/funnels/<subdomain>/<slug>/checkout/"
                            (gateway key gets appended by the page's own JS)
    csrf_token: str
    extra_content_html: str — pre-rendered block content (from
        funnel_blocks.render_blocks_body_html) to show ABOVE the payment
        card. Previously a Checkout page's own Blocks/AI/Code content was
        silently thrown away entirely the moment checkout settings were
        configured — you could build a whole sales-style page with
        testimonials and copy, and none of it would ever appear once the
        page became a real checkout. Now both coexist: your blocks render
        first, the auto-generated payment card renders after.
    """
    title = checkout.get("product_name") or page.title or "Checkout"
    price = checkout.get("price") or "0"
    currency = checkout.get("currency") or "USD"
    description = checkout.get("description") or ""

    if not gateways:
        gateway_html = '<p class="muted" style="color:#ef4444;">No payment methods are available on this checkout yet.</p>'
    else:
        buttons = "".join(
            f'<button type="button" onclick="submitCheckout(\'{_e(g)}\')" class="pay-btn">'
            f'{_e(GATEWAY_LABELS.get(g, g.title()))}</button>'
            for g in gateways
        )
        gateway_html = f'<div class="pay-buttons">{buttons}</div>'

    # The block system renders Tailwind-class markup; the checkout card
    # itself uses its own plain CSS reset (predates the block system,
    # deliberately self-contained so a checkout page never depends on an
    # external stylesheet loading correctly at the moment of payment).
    # Tailwind/Lucide only get pulled in when there's actually block
    # content to render.
    extra_head = ""
    extra_body_open = ""
    extra_script = ""
    if extra_content_html:
        extra_head = '<script src="https://cdn.tailwindcss.com"></script><script src="https://unpkg.com/lucide@latest"></script>'
        extra_body_open = f'<div style="max-width:1100px;margin:0 auto;">{extra_content_html}</div>'
        extra_script = "if (window.lucide) lucide.createIcons();"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_e(title)} — Checkout</title>
{extra_head}
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#0a0a0a; color:#fff;
          min-height:100vh; padding:24px; }}
  .checkout-wrap {{ min-height:calc(100vh - 48px); display:flex; align-items:center; justify-content:center; }}
  .card {{ width:100%; max-width:440px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1);
           border-radius:20px; padding:36px 32px; text-align:center; margin:0 auto; }}
  h1 {{ font-size:1.4rem; font-weight:800; margin-bottom:8px; }}
  .desc {{ color:#a3a3a3; font-size:0.9rem; margin-bottom:22px; white-space:pre-line; }}
  .price {{ font-size:2.4rem; font-weight:800; margin-bottom:28px; background:linear-gradient(135deg,#1DB954,#22d3ee);
            -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
  label {{ display:block; text-align:left; font-size:0.85rem; color:#a3a3a3; margin-bottom:6px; }}
  input {{ width:100%; padding:12px 14px; border-radius:10px; background:rgba(255,255,255,0.05);
           border:1px solid rgba(255,255,255,0.1); color:#fff; font-size:0.95rem; margin-bottom:14px; outline:none; }}
  input:focus {{ border-color:#1DB954; }}
  .pay-buttons {{ display:flex; flex-direction:column; gap:10px; margin-top:6px; }}
  .pay-btn {{ width:100%; padding:13px 16px; border-radius:10px; border:none; background:#1DB954; color:#08110c;
              font-weight:700; font-size:0.9rem; cursor:pointer; }}
  .pay-btn:hover {{ opacity:0.9; }}
  .error {{ color:#ef4444; font-size:0.8rem; margin-top:10px; display:none; }}
  .muted {{ color:#a3a3a3; }}
</style>
</head>
<body>
  {extra_body_open}
  <div class="checkout-wrap">
  <div class="card">
    <h1>{_e(title)}</h1>
    {f'<p class="desc">{_e(description)}</p>' if description else ''}
    <div class="price">{_e(price)} {_e(currency)}</div>
    <form id="checkout-form">
      <label>Your name</label>
      <input id="buyer_name" type="text" placeholder="Jane Doe">
      <label>Your email (for your receipt)</label>
      <input id="buyer_email" type="email" required placeholder="you@example.com">
    </form>
    {gateway_html}
    <p id="checkout-error" class="error">Please enter your email first.</p>
  </div>
  </div>
  <script>
    function submitCheckout(gateway) {{
      var email = document.getElementById('buyer_email').value.trim();
      var name = document.getElementById('buyer_name').value.trim();
      var err = document.getElementById('checkout-error');
      if (!email) {{ err.style.display = 'block'; return; }}
      err.style.display = 'none';
      var form = document.createElement('form');
      form.method = 'POST';
      form.action = {action_base_url!r} + gateway;
      form.innerHTML = '<input type="hidden" name="buyer_name" value="' + name.replace(/"/g,'&quot;') + '">' +
                        '<input type="hidden" name="buyer_email" value="' + email.replace(/"/g,'&quot;') + '">' +
                        '<input type="hidden" name="csrf_token" value="{_e(csrf_token)}">';
      document.body.appendChild(form);
      form.submit();
    }}
    {extra_script}
  </script>
</body>
</html>"""
