from datetime import datetime
from app.extensions import db
from app.utils.settings import default_site_currency

class Product(db.Model):
    __tablename__ = "products"
    id             = db.Column(db.Integer, primary_key=True)
    title          = db.Column(db.String(256), nullable=False)
    slug           = db.Column(db.String(256), unique=True, index=True)
    description    = db.Column(db.Text)
    long_desc      = db.Column(db.Text)
    category       = db.Column(db.String(64))
    type           = db.Column(db.String(64))
    price          = db.Column(db.Numeric(10, 2), default=0)
    sale_price     = db.Column(db.Numeric(10, 2))
    currency       = db.Column(db.String(8), default=default_site_currency)  # currency this product collects payment in
    images         = db.Column(db.JSON, default=list)
    tags           = db.Column(db.JSON, default=list)
    tech_stack     = db.Column(db.JSON, default=list)
    documentation  = db.Column(db.Text)
    status         = db.Column(db.String(32), default="active")
    featured       = db.Column(db.Boolean, default=False)
    download_count = db.Column(db.Integer, default=0)
    view_count     = db.Column(db.Integer, default=0)
    rating         = db.Column(db.Float, default=0.0)
    review_count   = db.Column(db.Integer, default=0)
    file_url       = db.Column(db.String(1024))
    preview_url    = db.Column(db.String(1024))
    demo_url       = db.Column(db.String(1024))
    license        = db.Column(db.String(32), default="standard")
    version        = db.Column(db.String(32), default="1.0.0")
    features       = db.Column(db.JSON, default=list)   # structured feature-list bullets, shown on product detail + Customer Tools
    billing_period = db.Column(db.String(16), default="one_time")  # one_time | monthly | yearly — drives UserProductAccess.expires_at on grant
    seo_title      = db.Column(db.String(256))
    seo_desc       = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    orders         = db.relationship("Order", back_populates="product", lazy="dynamic")
    wishlist_items = db.relationship("WishlistItem", back_populates="product", lazy="dynamic")
    reviews        = db.relationship("ProductReview", back_populates="product", lazy="dynamic")

    @property
    def effective_price(self):
        return self.sale_price if self.sale_price else self.price

    @property
    def is_free(self):
        return float(self.effective_price or 0) == 0

class Order(db.Model):
    __tablename__ = "orders"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"))
    product_id  = db.Column(db.Integer, db.ForeignKey("products.id"))
    amount      = db.Column(db.Numeric(10, 2))
    currency    = db.Column(db.String(8), default=default_site_currency)
    status      = db.Column(db.String(32), default="pending")
    gateway     = db.Column(db.String(32))
    gateway_ref = db.Column(db.String(256))
    notes       = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user        = db.relationship("User", back_populates="orders")
    product     = db.relationship("Product", back_populates="orders")
    downloads   = db.relationship("Download", back_populates="order", lazy="dynamic")
    transactions = db.relationship("Transaction", back_populates="order", lazy="dynamic")

class Download(db.Model):
    __tablename__ = "downloads"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"))
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id"))
    file_url   = db.Column(db.String(1024))
    ip_address = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship("User", back_populates="downloads")
    order      = db.relationship("Order", back_populates="downloads")

class WishlistItem(db.Model):
    __tablename__ = "wishlist_items"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship("User", back_populates="wishlist_items")
    product    = db.relationship("Product", back_populates="wishlist_items")

class ProductReview(db.Model):
    __tablename__ = "product_reviews"
    id         = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating     = db.Column(db.Integer, nullable=False)  # 1-5
    title      = db.Column(db.String(256))
    body       = db.Column(db.Text)
    approved   = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    product    = db.relationship("Product", back_populates="reviews")
    user       = db.relationship("User")
    __table_args__ = (db.UniqueConstraint("product_id", "user_id", name="uq_review_per_user"),)

class Transaction(db.Model):
    __tablename__ = "transactions"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"))
    order_id    = db.Column(db.Integer, db.ForeignKey("orders.id"))
    type        = db.Column(db.String(32))
    amount      = db.Column(db.Numeric(10, 2))
    currency    = db.Column(db.String(8), default=default_site_currency)
    gateway     = db.Column(db.String(32))
    gateway_ref = db.Column(db.String(256))
    status      = db.Column(db.String(32))
    meta        = db.Column(db.JSON)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    user        = db.relationship("User", back_populates="transactions")
    order       = db.relationship("Order", back_populates="transactions")

class HostingPlan(db.Model):
    __tablename__ = "hosting_plans"
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(128), nullable=False)
    slug          = db.Column(db.String(128), unique=True)
    description   = db.Column(db.Text)
    monthly_price = db.Column(db.Numeric(10, 2))
    annual_price  = db.Column(db.Numeric(10, 2))
    features      = db.Column(db.JSON, default=list)
    limits        = db.Column(db.JSON, default=dict)
    active        = db.Column(db.Boolean, default=True)
    featured      = db.Column(db.Boolean, default=False)
    order         = db.Column(db.Integer, default=0)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

class HostingSubscription(db.Model):
    __tablename__ = "hosting_subscriptions"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"))
    plan_id       = db.Column(db.Integer, db.ForeignKey("hosting_plans.id"))
    domain        = db.Column(db.String(256))
    domain_type   = db.Column(db.String(16), default="subdomain")  # "subdomain" | "own_domain"
    subdomain     = db.Column(db.String(64), unique=True, index=True)  # e.g. "jane" -> jane.bazillinapps.com
    dns_verified  = db.Column(db.Boolean, default=False)  # for own_domain: has the CNAME/A record been confirmed?
    billing_cycle = db.Column(db.String(16), default="monthly")
    status        = db.Column(db.String(32), default="pending")
    gateway_ref   = db.Column(db.String(256))
    starts_at     = db.Column(db.DateTime)
    expires_at    = db.Column(db.DateTime)
    auto_renew    = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    user          = db.relationship("User", back_populates="hosting_subs")
    plan          = db.relationship("HostingPlan")

class HostingServer(db.Model):
    """Admin-managed provisioning target (cPanel/WHM/Plesk/DirectAdmin/cloud).
    API credentials live here so plans/subscriptions can reference a server by label
    without hardcoding anything in source code."""
    __tablename__ = "hosting_servers"
    id            = db.Column(db.Integer, primary_key=True)
    label         = db.Column(db.String(128), nullable=False)
    provider      = db.Column(db.String(32), default="cpanel")  # cpanel | whm | plesk | directadmin | cloud
    api_endpoint  = db.Column(db.String(256))
    api_key       = db.Column(db.String(512))
    notes         = db.Column(db.Text)
    active        = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


class BankTransferPayment(db.Model):
    """A manual payment claim — user says they've sent a bank transfer,
    admin verifies against their actual bank statement and approves or
    rejects it. `kind` + `reference_id` point at whatever's being paid
    for (hosting subscription, marketplace order, client project) without
    needing a separate table per payment type."""
    __tablename__ = "bank_transfer_payments"
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    kind            = db.Column(db.String(32), nullable=False)   # "hosting_subscription" | "order" | "client_project"
    reference_id    = db.Column(db.Integer, nullable=False)
    amount          = db.Column(db.Numeric(10, 2), nullable=False)
    currency        = db.Column(db.String(8), default=default_site_currency)
    sender_reference = db.Column(db.String(256))   # what the user typed in ("transfer ref ABC123", their bank name, etc.)
    status          = db.Column(db.String(16), default="pending")  # pending | approved | rejected
    rejection_reason = db.Column(db.Text)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at     = db.Column(db.DateTime)
    reviewed_by_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user            = db.relationship("User", foreign_keys=[user_id])
    reviewed_by     = db.relationship("User", foreign_keys=[reviewed_by_id])
    proof_image      = db.Column(db.String(512))


class PaymentLink(db.Model):
    """A standalone, public, shareable 'pay me' page — the admin sets a
    title/description/amount once, picks which payment methods to accept,
    and gets a public URL (/pay/<slug>) that ANYONE can pay from, with no
    account needed on this site. This is deliberately separate from the
    internal client-project Invoice model above: Invoice is for billing
    YOUR existing clients inside their project dashboard (login required);
    PaymentLink is for selling anything to anyone (a course, a one-off
    service, a funnel offer) via a link dropped in an email, DM, or bio."""
    __tablename__ = "payment_links"
    id                = db.Column(db.Integer, primary_key=True)
    owner_id          = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    slug              = db.Column(db.String(64), unique=True, nullable=False, index=True)
    title             = db.Column(db.String(200), nullable=False)
    description       = db.Column(db.Text)
    image_url         = db.Column(db.String(512))
    amount            = db.Column(db.Numeric(10, 2), nullable=False)
    currency          = db.Column(db.String(8), default=default_site_currency)
    status            = db.Column(db.String(16), default="draft")   # draft | published | archived
    # Which of paystack/flutterwave/paypal/stripe/bank_transfer/crypto/wave/payoneer to show —
    # gateway ones only actually appear if that gateway is ALSO enabled/configured site-wide.
    allowed_methods   = db.Column(db.JSON, default=list)
    wave_instructions = db.Column(db.Text)      # e.g. Wave number/@handle + note, since Wave has no public checkout API
    payoneer_instructions = db.Column(db.Text)  # e.g. Payoneer payment request link/email, same reason
    thank_you_message = db.Column(db.Text, default="Thank you! Your payment has been received.")
    redirect_url      = db.Column(db.String(512))  # optional: send buyer here after payment instead of the built-in thank-you page
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at        = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner             = db.relationship("User")

    @property
    def paid_count(self):
        return sum(1 for p in self.payments if p.status == "paid")

    @property
    def total_collected(self):
        from decimal import Decimal
        return float(sum((Decimal(str(p.amount)) for p in self.payments if p.status == "paid"), Decimal("0")))


class PaymentLinkPayment(db.Model):
    """One payment attempt against a PaymentLink. No user_id/login
    required — payer_name/payer_email are simply what the buyer typed in,
    since they're very likely not a registered account on this site."""
    __tablename__ = "payment_link_payments"
    id              = db.Column(db.Integer, primary_key=True)
    payment_link_id = db.Column(db.Integer, db.ForeignKey("payment_links.id"), nullable=False)
    payer_name      = db.Column(db.String(200))
    payer_email     = db.Column(db.String(200))
    amount          = db.Column(db.Numeric(10, 2), nullable=False)
    currency        = db.Column(db.String(8))
    gateway         = db.Column(db.String(24))    # paystack | flutterwave | paypal | stripe | bank_transfer | crypto | wave | payoneer
    gateway_ref     = db.Column(db.String(256))
    status          = db.Column(db.String(16), default="pending")   # pending | paid | failed
    sender_reference = db.Column(db.String(256))   # manual-method note (tx hash, transfer ref, Wave confirmation code, etc.)
    proof_image     = db.Column(db.String(512))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at         = db.Column(db.DateTime)
    payment_link    = db.relationship("PaymentLink", backref=db.backref("payments", lazy="dynamic", cascade="all, delete-orphan"))
