"""
One-time fix: creates the missing 'whatsapp-widget' marketplace Product row.

THE BUG THIS FIXES
-------------------
PREMIUM_PRODUCTS (app/dashboard/premium.py) lists 'whatsapp-widget' as a
real product with a real dashboard page (dashboard.whatsapp_widget) — but
no matching row existed in the `products` table. The sidebar builds each
product's link like this (templates/dashboard/base_dashboard.html):

    url_for(p.endpoint) if p.unlocked and p.endpoint
    else (url_for('marketplace.product_detail', slug=p.product_slug) if p.product_id else '#')

With no Product row, `p.product_id` was always None for every non-admin
user, so the fallback resolved to a literal '#' — clicking "WhatsApp Chat
Widget" in the sidebar did nothing. This is exactly the "click and nothing
happens" bug reported.

Run this once on your production server:

    python -m scripts.seed_whatsapp_widget_product

(or `flask shell` and paste the body). Safe to re-run — it's a no-op if
the product already exists.
"""
import os
from dotenv import load_dotenv
load_dotenv()
from app import create_app
from app.extensions import db
from app.models.commerce import Product

app = create_app(os.environ.get("FLASK_ENV", "production"))

with app.app_context():
    existing = Product.query.filter_by(slug="whatsapp-widget").first()
    if existing:
        print(f"'whatsapp-widget' product already exists (id={existing.id}) — nothing to do.")
    else:
        p = Product(
            title="WhatsApp Chat Widget",
            slug="whatsapp-widget",
            description="Add a WhatsApp chat button to your website in minutes — no API, no coding.",
            long_desc=(
                "## WhatsApp Chat Widget\n\n"
                "A professional WhatsApp chat button for your website. Visitors click it "
                "and go straight into WhatsApp to message you directly.\n\n"
                "### Features\n"
                "- No Meta API, no webhooks, no developer setup\n"
                "- Fully customizable position, color, icon, and pre-filled message\n"
                "- Copy embed code, download a WordPress plugin, or use a hosted link\n"
                "- Views / clicks / click-rate analytics"
            ),
            category="Bots",
            type="premium_tool",
            price=14.99,
            currency="NGN",
            status="active",
            license="standard",
            version="1.0.0",
            images="[]",
            tags='["whatsapp", "widget", "chat button", "website"]',
            tech_stack="[]",
        )
        db.session.add(p)
        db.session.commit()
        print(f"Created 'whatsapp-widget' product (id={p.id}). The sidebar link will work now.")
