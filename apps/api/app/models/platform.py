from datetime import datetime
from app.extensions import db
from app.utils.settings import default_site_currency

class FreelancerProfile(db.Model):
    __tablename__ = "freelancer_profiles"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    title         = db.Column(db.String(256))
    bio           = db.Column(db.Text)
    skills        = db.Column(db.JSON, default=list)
    hourly_rate   = db.Column(db.Numeric(10, 2))
    availability  = db.Column(db.String(32), default="available")
    verified      = db.Column(db.Boolean, default=False)
    featured      = db.Column(db.Boolean, default=False)
    rating        = db.Column(db.Float, default=0.0)
    completed_jobs = db.Column(db.Integer, default=0)
    portfolio_url = db.Column(db.String(512))
    location      = db.Column(db.String(128))
    languages     = db.Column(db.JSON, default=list)
    experience    = db.Column(db.String(32), default="intermediate")
    total_earned  = db.Column(db.Numeric(10, 2), default=0)
    verification_submitted = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user          = db.relationship("User", back_populates="freelancer_profile")
    proposals     = db.relationship("Proposal", lazy="dynamic", viewonly=True,
                                    primaryjoin="FreelancerProfile.user_id == foreign(Proposal.user_id)")

class ClientProfile(db.Model):
    __tablename__ = "client_profiles"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    company_name = db.Column(db.String(256))
    company_url  = db.Column(db.String(512))
    industry     = db.Column(db.String(128))
    verified     = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    user         = db.relationship("User", back_populates="client_profile")

class JobPost(db.Model):
    __tablename__ = "job_posts"
    id           = db.Column(db.Integer, primary_key=True)
    client_id    = db.Column(db.Integer, db.ForeignKey("users.id"))
    title        = db.Column(db.String(256), nullable=False)
    description  = db.Column(db.Text)
    category     = db.Column(db.String(64))
    skills       = db.Column(db.JSON, default=list)
    budget_min   = db.Column(db.Numeric(10, 2))
    budget_max   = db.Column(db.Numeric(10, 2))
    budget_type  = db.Column(db.String(32), default="fixed")
    duration     = db.Column(db.String(64))
    status       = db.Column(db.String(32), default="open")
    deadline     = db.Column(db.DateTime)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    client       = db.relationship("User", back_populates="jobs_posted")
    proposals    = db.relationship("Proposal", back_populates="job", lazy="dynamic")

class Proposal(db.Model):
    __tablename__ = "proposals"
    id            = db.Column(db.Integer, primary_key=True)
    job_id        = db.Column(db.Integer, db.ForeignKey("job_posts.id", ondelete="CASCADE"))
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"))
    cover_letter  = db.Column(db.Text)
    bid_amount    = db.Column(db.Numeric(10, 2))
    delivery_days = db.Column(db.Integer)
    status        = db.Column(db.String(32), default="pending")
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    job           = db.relationship("JobPost", back_populates="proposals")
    user          = db.relationship("User", back_populates="proposals")

class Payout(db.Model):
    __tablename__ = "payouts"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"))
    amount       = db.Column(db.Numeric(10, 2))
    method       = db.Column(db.String(32))
    status       = db.Column(db.String(32), default="pending")
    processed_at = db.Column(db.DateTime)
    notes        = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class PageView(db.Model):
    __tablename__ = "page_views"
    id         = db.Column(db.Integer, primary_key=True)
    path       = db.Column(db.String(512), index=True)
    referrer   = db.Column(db.String(512))
    country    = db.Column(db.String(64))
    device     = db.Column(db.String(32))
    session_id = db.Column(db.String(128))
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class AnalyticsEvent(db.Model):
    __tablename__ = "analytics_events"
    id         = db.Column(db.Integer, primary_key=True)
    event      = db.Column(db.String(128), index=True)
    path       = db.Column(db.String(512))
    value      = db.Column(db.String(512))
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    session_id = db.Column(db.String(128))
    event_metadata = db.Column("metadata", db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class ApiUsage(db.Model):
    __tablename__ = "api_usage"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"))
    tool       = db.Column(db.String(128), index=True)
    tokens     = db.Column(db.Integer, default=0)
    cost       = db.Column(db.Float, default=0.0)
    success    = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship("User", back_populates="api_usage")

class CodeProject(db.Model):
    __tablename__ = "code_projects"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"))
    title       = db.Column(db.String(256))
    description = db.Column(db.Text)
    html        = db.Column(db.Text, default="")
    css         = db.Column(db.Text, default="")
    js          = db.Column(db.Text, default="")
    framework   = db.Column(db.String(32), default="vanilla")
    is_public   = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user        = db.relationship("User", back_populates="code_projects")

class SupportTicket(db.Model):
    __tablename__ = "support_tickets"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    name        = db.Column(db.String(128))
    email       = db.Column(db.String(256))
    subject     = db.Column(db.String(512))
    message     = db.Column(db.Text)
    status      = db.Column(db.String(32), default="open")
    priority    = db.Column(db.String(16), default="normal")
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TrendItem(db.Model):
    __tablename__ = "trend_items"
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(512))
    description = db.Column(db.Text)
    url         = db.Column(db.String(1024))
    source      = db.Column(db.String(128))
    category    = db.Column(db.String(64))
    score       = db.Column(db.Integer, default=0)
    approved    = db.Column(db.Boolean, default=False)
    pinned      = db.Column(db.Boolean, default=False)
    hidden      = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ShortUrl(db.Model):
    __tablename__ = "short_urls"
    id           = db.Column(db.Integer, primary_key=True)
    code         = db.Column(db.String(16), unique=True, nullable=False, index=True)
    target_url   = db.Column(db.String(2048), nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    click_count  = db.Column(db.Integer, default=0)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    last_clicked = db.Column(db.DateTime)
    user         = db.relationship("User")


class FAQItem(db.Model):
    """Auto-reply chat widget FAQ entries, fully admin-managed."""
    __tablename__ = "faq_items"
    id          = db.Column(db.Integer, primary_key=True)
    question    = db.Column(db.String(512), nullable=False)
    answer      = db.Column(db.Text, nullable=False)
    category    = db.Column(db.String(64), default="General")
    order       = db.Column(db.Integer, default=0)
    active      = db.Column(db.Boolean, default=True)
    view_count  = db.Column(db.Integer, default=0)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectRequest(db.Model):
    """The real 'Hire Me' intake — captures what someone wants built,
    distinct from a generic support ticket."""
    __tablename__ = "project_requests"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    name         = db.Column(db.String(128), nullable=False)
    email        = db.Column(db.String(256), nullable=False)
    company      = db.Column(db.String(256))
    country      = db.Column(db.String(128))
    project_type = db.Column(db.String(64))   # website, web app, mobile app, hosting, other
    budget_range = db.Column(db.String(64))
    timeline     = db.Column(db.String(64))
    description  = db.Column(db.Text, nullable=False)
    status       = db.Column(db.String(32), default="new")  # new, reviewing, quoted, accepted, declined
    admin_notes  = db.Column(db.Text)
    proposal_message  = db.Column(db.Text)
    proposal_amount   = db.Column(db.Float)
    proposal_timeline = db.Column(db.String(128))
    proposal_sent_at  = db.Column(db.DateTime)
    currency          = db.Column(db.String(8), default=default_site_currency)
    # Which payment modes the admin allows for this specific project —
    # decided at proposal time based on how much trust/relationship exists.
    allow_part_payment    = db.Column(db.Boolean, default=True)
    allow_full_payment    = db.Column(db.Boolean, default=True)
    allow_after_service   = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user         = db.relationship("User")
    client_project = db.relationship("ClientProject", back_populates="request", uselist=False)


class ProjectReview(db.Model):
    """Client's rating + review after a project is genuinely marked
    completed — separate from the 'review' status (which just means
    'demo ready, awaiting client sign-off'). One review per project."""
    __tablename__ = "project_reviews"
    id          = db.Column(db.Integer, primary_key=True)
    project_id  = db.Column(db.Integer, db.ForeignKey("client_projects.id"), nullable=False, unique=True)
    rating      = db.Column(db.Integer, nullable=False)  # 1-5
    review_text = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    project     = db.relationship("ClientProject", back_populates="review")


class ProjectDelivery(db.Model):
    """A single deliverable handed to the client when work is finished or
    at any milestone — a file, a URL, raw text/notes, or a video link.
    A project can have many of these (e.g. a zip now, a revision later)."""
    __tablename__ = "project_deliveries"
    id          = db.Column(db.Integer, primary_key=True)
    project_id  = db.Column(db.Integer, db.ForeignKey("client_projects.id"), nullable=False)
    kind        = db.Column(db.String(16), nullable=False)  # file, url, text, video
    title       = db.Column(db.String(256), nullable=False)
    note        = db.Column(db.Text)
    file_url    = db.Column(db.String(512))   # for kind == file
    external_url = db.Column(db.String(512))  # for kind == url / video
    text_content = db.Column(db.Text)         # for kind == text
    delivered_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    project     = db.relationship("ClientProject", back_populates="deliveries")


class Wallet(db.Model):
    """One wallet per user. `balance` is the available (spendable) amount;
    `pending_balance` tracks amounts not yet cleared (e.g. a bank-transfer
    credit still awaiting admin confirmation) so the two are never
    conflated on the client's own dashboard."""
    __tablename__ = "wallets"
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    balance         = db.Column(db.Numeric(10, 2), default=0)
    pending_balance = db.Column(db.Numeric(10, 2), default=0)
    currency        = db.Column(db.String(8), default=default_site_currency)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User")
    transactions = db.relationship("WalletTransaction", back_populates="wallet",
                                    order_by="WalletTransaction.created_at.desc()", cascade="all, delete-orphan")


class WalletTransaction(db.Model):
    """One ledger row per wallet movement. `kind` is one of: deposit,
    withdrawal, credit (admin-issued, e.g. refund/goodwill), debit
    (admin-issued deduction), invoice_payment (spent paying an invoice),
    referral_earning. Balance is never recomputed from a running total in
    code — it's the source of truth on Wallet.balance, this table is the
    auditable history of how it got there."""
    __tablename__ = "wallet_transactions"
    id          = db.Column(db.Integer, primary_key=True)
    wallet_id   = db.Column(db.Integer, db.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    kind        = db.Column(db.String(32), nullable=False)
    amount      = db.Column(db.Numeric(10, 2), nullable=False)  # positive=credit to wallet, negative=debit
    note        = db.Column(db.String(400))
    reference   = db.Column(db.String(128))  # e.g. related invoice id, admin username who issued it
    created_by  = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    wallet = db.relationship("Wallet", back_populates="transactions")


class Receipt(db.Model):
    """Auto-generated the moment an Invoice is marked paid. Kept as its own
    record (not just derived from the Invoice at PDF-render time) so the
    reference number and paid-amount snapshot are stable and independently
    verifiable even if the invoice is later edited."""
    __tablename__ = "receipts"
    id             = db.Column(db.Integer, primary_key=True)
    invoice_id     = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, unique=True)
    reference      = db.Column(db.String(32), nullable=False, unique=True, index=True)
    amount         = db.Column(db.Numeric(10, 2), nullable=False)
    currency       = db.Column(db.String(8))
    payment_method = db.Column(db.String(64))
    paid_at        = db.Column(db.DateTime, default=datetime.utcnow)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    invoice = db.relationship("Invoice")


class WithdrawalRequest(db.Model):
    """A client's request to move wallet balance out to their own bank/other
    account. Nothing here talks to a real payout API — this platform has no
    outbound-payment integration — so it's a request-and-manual-fulfillment
    flow: wallet balance is debited (reserved) the moment the request is
    made so it can't be spent twice while pending, and the admin marks it
    paid/rejected by hand after actually sending the money outside the
    platform. A rejected request refunds the wallet."""
    __tablename__ = "withdrawal_requests"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount       = db.Column(db.Numeric(10, 2), nullable=False)
    currency     = db.Column(db.String(8))
    destination  = db.Column(db.String(400), nullable=False)  # free-text bank/payout details the client typed in
    status       = db.Column(db.String(32), default="pending")  # pending, approved, rejected, paid
    admin_note   = db.Column(db.String(400))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at  = db.Column(db.DateTime)

    user = db.relationship("User")


class ScrapedSiteItem(db.Model):
    """One saved result from the 'Pull Info From Client's Website' /
    Custom Product Catalog importer (app/admin/routes.py
    import_catalog_from_url). Previously that endpoint only ever returned
    results to the browser for one look — nothing was kept, so nothing
    else on the platform could reuse it. Now every pulled item is saved
    here so it's available afterward to: the knowledge base search
    (app/utils/knowledge.py), social bots building a catalog reply, and
    this project's own record if pulled from a specific client project.
    `project_id` is nullable — a pull from the generic Social Channels
    catalog importer has no specific project."""
    __tablename__ = "scraped_site_items"
    id           = db.Column(db.Integer, primary_key=True)
    project_id   = db.Column(db.Integer, db.ForeignKey("client_projects.id", ondelete="CASCADE"), nullable=True)
    source_url   = db.Column(db.String(512), nullable=False)
    name         = db.Column(db.String(256))
    description  = db.Column(db.Text)
    price        = db.Column(db.String(64))
    image_url    = db.Column(db.String(512))
    video_url    = db.Column(db.String(512))
    link         = db.Column(db.String(512))
    kind         = db.Column(db.String(32), default="product")
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship("ClientProject")


class Invoice(db.Model):
    """A single billable item on a project — deposit, milestone payment,
    final payment, etc. A project can have many invoices, giving both
    admin and client a clear, itemized record of what was charged and when."""
    __tablename__ = "invoices"
    id           = db.Column(db.Integer, primary_key=True)
    project_id   = db.Column(db.Integer, db.ForeignKey("client_projects.id"), nullable=False)
    title        = db.Column(db.String(256), nullable=False)   # e.g. "50% Deposit", "Milestone 2 Payment"
    description  = db.Column(db.Text)
    amount       = db.Column(db.Numeric(10, 2), nullable=False)
    amount_paid  = db.Column(db.Numeric(10, 2), default=0)  # cumulative — lets a wallet payment cover PART of an invoice
    currency     = db.Column(db.String(8), default=default_site_currency)
    status       = db.Column(db.String(32), default="unpaid")  # unpaid, partial, paid, cancelled, pending_review
    gateway      = db.Column(db.String(32))
    gateway_ref  = db.Column(db.String(256))
    due_date     = db.Column(db.Date)
    created_by   = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at      = db.Column(db.DateTime)
    project      = db.relationship("ClientProject", back_populates="invoices")

    @property
    def remaining_amount(self):
        """What's still owed after any partial wallet payment. Gateway
        checkouts charge THIS, not the full invoice amount, so a partial
        wallet payment is actually reflected at checkout."""
        from decimal import Decimal
        return float(Decimal(str(self.amount)) - Decimal(str(self.amount_paid or 0)))


class ClientProject(db.Model):
    """A real, accepted engagement — visible and trackable by both admin and the client."""
    __tablename__ = "client_projects"
    id            = db.Column(db.Integer, primary_key=True)
    request_id    = db.Column(db.Integer, db.ForeignKey("project_requests.id"), nullable=True)
    client_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title         = db.Column(db.String(256), nullable=False)
    description   = db.Column(db.Text)
    status        = db.Column(db.String(32), default="planning")  # planning, in_progress, review, completed, on_hold
    progress_pct  = db.Column(db.Integer, default=0)
    payment_mode  = db.Column(db.String(32))  # part, full, after_service — client's choice, once made
    allow_part_payment  = db.Column(db.Boolean, default=True)
    allow_full_payment  = db.Column(db.Boolean, default=True)
    allow_after_service = db.Column(db.Boolean, default=False)
    agreed_budget = db.Column(db.Float)
    currency      = db.Column(db.String(8), default=default_site_currency)
    start_date    = db.Column(db.Date)
    due_date      = db.Column(db.Date)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    client        = db.relationship("User")
    request       = db.relationship("ProjectRequest", back_populates="client_project")
    milestones    = db.relationship("ProjectMilestone", back_populates="project",
                                    order_by="ProjectMilestone.order", cascade="all, delete-orphan")
    updates       = db.relationship("ProjectUpdate", back_populates="project",
                                    order_by="ProjectUpdate.created_at.desc()", cascade="all, delete-orphan")
    invoices      = db.relationship("Invoice", back_populates="project",
                                    order_by="Invoice.created_at.desc()", cascade="all, delete-orphan")
    deliveries    = db.relationship("ProjectDelivery", back_populates="project",
                                    order_by="ProjectDelivery.created_at.desc()", cascade="all, delete-orphan")
    review        = db.relationship("ProjectReview", back_populates="project", uselist=False, cascade="all, delete-orphan")
    meetings      = db.relationship("ProjectMeeting", back_populates="project",
                                    order_by="ProjectMeeting.scheduled_at", cascade="all, delete-orphan")
    completed_at  = db.Column(db.DateTime)

    @property
    def total_invoiced(self):
        return sum(float(i.amount) for i in self.invoices)

    @property
    def total_paid(self):
        return sum(float(i.amount) for i in self.invoices if i.status == "paid")

    @property
    def total_outstanding(self):
        return sum(float(i.amount) for i in self.invoices if i.status == "unpaid")


class ProjectMilestone(db.Model):
    __tablename__ = "project_milestones"
    id          = db.Column(db.Integer, primary_key=True)
    project_id  = db.Column(db.Integer, db.ForeignKey("client_projects.id"), nullable=False)
    title       = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    status      = db.Column(db.String(32), default="pending")  # pending, in_progress, done
    due_date    = db.Column(db.Date)
    order       = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime)
    project     = db.relationship("ClientProject", back_populates="milestones")


class ProjectUpdate(db.Model):
    """Timeline post — admin posts progress notes the client can see, like a build log.
    Can optionally include a preview URL/image/progress percentage and a
    shareable review link the client can open (and comment on) without
    needing to log in — sent to them by email."""
    __tablename__ = "project_updates"
    id          = db.Column(db.Integer, primary_key=True)
    project_id  = db.Column(db.Integer, db.ForeignKey("client_projects.id"), nullable=False)
    author_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    message     = db.Column(db.Text, nullable=False)
    preview_url = db.Column(db.String(1024))
    image_url   = db.Column(db.String(1024))
    progress_percent = db.Column(db.Integer)
    review_token = db.Column(db.String(64), unique=True, index=True)
    email_sent_at = db.Column(db.DateTime)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    project     = db.relationship("ClientProject", back_populates="updates")
    author      = db.relationship("User")
    comments    = db.relationship("ProjectUpdateComment", back_populates="update", cascade="all, delete-orphan")

    def ensure_review_token(self):
        if not self.review_token:
            import secrets
            self.review_token = secrets.token_urlsafe(24)
        return self.review_token


class ProjectUpdateComment(db.Model):
    """A comment/review left on a ProjectUpdate's shareable review link —
    can come from the client (logged in) or an anonymous reviewer the
    client forwarded the link to (name/email captured instead)."""
    __tablename__ = "project_update_comments"
    id          = db.Column(db.Integer, primary_key=True)
    update_id   = db.Column(db.Integer, db.ForeignKey("project_updates.id"), nullable=False)
    author_name = db.Column(db.String(128))
    author_email = db.Column(db.String(256))
    author_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    body        = db.Column(db.Text, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    update      = db.relationship("ProjectUpdate", back_populates="comments")
    author      = db.relationship("User")


class ProjectMeeting(db.Model):
    """A scheduled call/meeting with a client, tied to their project — you
    book it from the project's admin page, the client sees it on their own
    project page and gets an email, and it fires the
    `meeting_scheduled` automation trigger so it can also notify Slack/a
    webhook/whatever else you've wired up in the Automation Center.
    Can also originate from the CLIENT side before a project even exists
    yet — a client who's just been sent a proposal (ProjectRequest,
    status="quoted") can request a meeting to discuss it; that's tracked
    via request_id with project_id left null and status="requested"
    until you pick a real date and confirm it (status becomes
    "scheduled")."""
    __tablename__ = "project_meetings"
    id                = db.Column(db.Integer, primary_key=True)
    project_id        = db.Column(db.Integer, db.ForeignKey("client_projects.id"), nullable=True)
    request_id        = db.Column(db.Integer, db.ForeignKey("project_requests.id"), nullable=True)
    title             = db.Column(db.String(256), nullable=False)
    scheduled_at      = db.Column(db.DateTime, nullable=False)
    duration_minutes  = db.Column(db.Integer, default=30)
    location          = db.Column(db.String(512))  # a video call link, phone number, or physical address
    notes             = db.Column(db.Text)
    status            = db.Column(db.String(16), default="scheduled")  # requested, scheduled, completed, cancelled
    created_by_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    project           = db.relationship("ClientProject", back_populates="meetings")
    request           = db.relationship("ProjectRequest", backref=db.backref("meetings", lazy="dynamic"))


class ScheduledBroadcast(db.Model):
    """A message queued to broadcast to everyone who's messaged a given
    bot — the actual "post on a schedule" mechanism for channels that
    support free-form outbound messages (Telegram). WhatsApp/Facebook
    restrict proactive messaging outside a 24h reply window unless
    you're using pre-approved templates, so broadcasting through those
    isn't guaranteed to land — see the warning shown wherever this is
    used. True publishing to YouTube/Instagram/etc needs a real OAuth
    integration per platform that doesn't exist yet."""
    __tablename__ = "scheduled_broadcasts"
    id             = db.Column(db.Integer, primary_key=True)
    channel_id     = db.Column(db.Integer, db.ForeignKey("social_channels.id"), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=True)
    title          = db.Column(db.String(256))
    body           = db.Column(db.Text, nullable=False)
    scheduled_at   = db.Column(db.DateTime, nullable=False)
    status         = db.Column(db.String(16), default="pending")  # pending, sent, failed, cancelled
    sent_count     = db.Column(db.Integer, default=0)
    error          = db.Column(db.Text)
    platform_meta  = db.Column(db.JSON, default=dict)  # extra metadata (image URL, etc)
    approval_status = db.Column(db.String(32), default="approved")  # draft | pending_approval | approved
    created_by_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    channel        = db.relationship("SocialChannel")


class WorkflowTemplate(db.Model):
    """A workflow saved as a reusable template — either one of yours you
    want to reuse later, or (if you ever open this up) one shared by
    someone else. For now this is a personal template library, the
    foundation a real multi-user marketplace would sit on top of."""
    __tablename__ = "workflow_templates"
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(256), nullable=False)
    description  = db.Column(db.Text)
    trigger_type = db.Column(db.String(64), nullable=False)
    actions      = db.Column(db.JSON, default=list)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)


class AutomationWorkflow(db.Model):
    """A trigger -> ordered actions rule, in the spirit of n8n/Zapier but
    scoped to what this platform can actually fire events for. See
    app/utils/automation.py for the trigger points and action executors."""
    __tablename__ = "automation_workflows"
    id            = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=True)
    name          = db.Column(db.String(128), nullable=False)
    trigger_type  = db.Column(db.String(64), nullable=False)  # see automation.TRIGGERS
    trigger_config = db.Column(db.JSON, default=dict)         # e.g. {"category": "Billing"} to filter
    actions       = db.Column(db.JSON, default=list)          # ordered list of {"type":..., "config":{...}}
    canvas_positions = db.Column(db.JSON, default=dict)       # {"trigger": {"x":.., "y":..}, "action-0": {...}, ...} — visual layout only, purely cosmetic
    active        = db.Column(db.Boolean, default=True)
    run_count     = db.Column(db.Integer, default=0)
    last_run_at   = db.Column(db.DateTime)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    # Same purpose as SocialChannel.client_project_id — link this
    # workflow to whichever client it's actually running for. Each
    # workflow already has its own webhook URL inside `actions` (a
    # "webhook" action's config.url is per-workflow, not global), so one
    # customer's Zapier/n8n/Slack hook was already fully isolated from
    # another's before this field existed; this is what makes it billable
    # and shows it grouped under the right customer in Financials.
    client_project_id = db.Column(db.Integer, db.ForeignKey("client_projects.id"), nullable=True)
    monthly_fee   = db.Column(db.Float)
    client_project = db.relationship("ClientProject")


class AutomationRun(db.Model):
    """Execution log — one row per workflow firing, for the admin to audit
    what actually happened (and debug failed actions)."""
    __tablename__ = "automation_runs"
    id           = db.Column(db.Integer, primary_key=True)
    workflow_id  = db.Column(db.Integer, db.ForeignKey("automation_workflows.id"), nullable=False)
    status       = db.Column(db.String(16), default="success")  # success | partial | failed
    trigger_data = db.Column(db.JSON, default=dict)
    log          = db.Column(db.Text)
    metrics      = db.Column(db.JSON, default=dict)  # metrics (nodes run, execution speed, tokens)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    workflow     = db.relationship("AutomationWorkflow")


class AutomationCredential(db.Model):
    """A saved, encrypted connection to an external app (Slack, GitHub,
    Notion, etc.) that automation nodes reference by ID instead of storing
    raw secrets inline in a workflow's node config. Secrets are encrypted
    at rest with app/utils/crypto.py (same Fernet scheme already used for
    payment gateway credentials) — never stored or returned to the browser
    in plaintext. See app/utils/credential_providers.py for the provider
    registry and real test-connection logic, and
    app/utils/automation.py's api_request executor for how a node's
    `credential_id` gets resolved into real headers at execution time."""
    __tablename__ = "automation_credentials"
    id                 = db.Column(db.Integer, primary_key=True)
    name               = db.Column(db.String(128), nullable=False)   # admin's own label, e.g. "My Business Gmail"
    provider           = db.Column(db.String(64), nullable=False)    # key into credential_providers.PROVIDERS
    encrypted_data      = db.Column(db.Text, nullable=False)         # Fernet-encrypted JSON secret dict
    active             = db.Column(db.Boolean, default=True)
    last_tested_at     = db.Column(db.DateTime)
    last_test_ok       = db.Column(db.Boolean)
    last_test_message  = db.Column(db.String(256))
    created_by_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)

    def get_secret(self):
        from app.utils.crypto import decrypt_json
        return decrypt_json(self.encrypted_data)

    def set_secret(self, data):
        from app.utils.crypto import encrypt_json
        self.encrypted_data = encrypt_json(data)

    def usage_count(self):
        """How many workflows currently have a node referencing this
        credential — computed at call time rather than stored, since
        workflow node configs are free-form JSON and can change any time."""
        count = 0
        for wf in AutomationWorkflow.query.all():
            nodes = (wf.actions or {}).get("nodes", []) if isinstance(wf.actions, dict) else []
            for n in nodes:
                if (n.get("config") or {}).get("credential_id") == self.id:
                    count += 1
                    break
        return count


class Lead(db.Model):
    """A prospect for cold outreach — imported by the admin (CSV/manual entry),
    never scraped autonomously. See CHANGES notes for why."""
    __tablename__ = "leads"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(128))
    email       = db.Column(db.String(256), nullable=False)
    company     = db.Column(db.String(256))
    niche       = db.Column(db.String(128))
    source      = db.Column(db.String(128))   # e.g. "CSV import", "referral"
    status      = db.Column(db.String(16), default="new")  # new | contacted | replied | unsubscribed | bounced
    phone       = db.Column(db.String(64))
    website     = db.Column(db.String(512))
    address     = db.Column(db.Text)
    notes       = db.Column(db.Text)
    # Lightweight sales pipeline, separate from the cold-email `status`
    # above (that's about outreach delivery; this is about the deal).
    deal_stage  = db.Column(db.String(16), default="new")  # new | qualified | proposal | won | lost
    deal_value  = db.Column(db.Float)
    unsub_token = db.Column(db.String(64), unique=True, index=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    last_contacted_at = db.Column(db.DateTime)

    def ensure_token(self):
        if not self.unsub_token:
            import secrets
            self.unsub_token = secrets.token_urlsafe(32)
        return self.unsub_token


class ReferralCode(db.Model):
    """A shareable referral link/code for a partner, affiliate, or an
    existing happy client — share a link like yoursite.com/?ref=CODE and
    anyone who submits the hire-me form after clicking it gets logged
    below. Rewards/commission are tracked here but paid manually (there's
    no payout automation) — reward_note is just what you agreed to give them."""
    __tablename__ = "referral_codes"
    id           = db.Column(db.Integer, primary_key=True)
    code         = db.Column(db.String(32), unique=True, nullable=False, index=True)
    label        = db.Column(db.String(128))          # who this is for, e.g. "Jane — affiliate"
    owner_email  = db.Column(db.String(256))          # where their reward/commission gets sent
    reward_note  = db.Column(db.String(256))          # e.g. "$50 credit" or "10% commission"
    reward_amount = db.Column(db.Numeric(10, 2), nullable=True)  # set this to enable auto wallet-crediting on payout; leave blank for freeform/manual arrangements
    active       = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    signups      = db.relationship("ReferralSignup", back_populates="referral_code", cascade="all, delete-orphan")

    @staticmethod
    def generate_code():
        import secrets
        return secrets.token_urlsafe(6).replace("_", "").replace("-", "")[:8].upper()


class ReferralSignup(db.Model):
    """One lead that arrived via a referral code — logged when someone
    submits the hire-me form after their session picked up ?ref=CODE
    from an earlier page visit. `converted` and `reward_paid` are set
    manually by you as the deal and payout actually happen."""
    __tablename__ = "referral_signups"
    id               = db.Column(db.Integer, primary_key=True)
    referral_code_id = db.Column(db.Integer, db.ForeignKey("referral_codes.id"), nullable=False)
    name             = db.Column(db.String(128))
    email            = db.Column(db.String(256))
    source           = db.Column(db.String(64))   # e.g. "hire_request"
    converted        = db.Column(db.Boolean, default=False)
    reward_paid      = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    referral_code    = db.relationship("ReferralCode", back_populates="signups")


class ColdEmailCampaign(db.Model):
    __tablename__ = "cold_email_campaigns"
    id            = db.Column(db.Integer, primary_key=True)
    subject       = db.Column(db.String(256), nullable=False)
    body_html     = db.Column(db.Text, nullable=False)
    niche_filter  = db.Column(db.String(128))  # only send to leads with this niche, blank = all
    status        = db.Column(db.String(16), default="draft")
    recipient_count = db.Column(db.Integer, default=0)
    sent_count    = db.Column(db.Integer, default=0)
    failed_count  = db.Column(db.Integer, default=0)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at       = db.Column(db.DateTime)


class TodoItem(db.Model):
    """Personal work-planning board for the site owner/admins. Reminders
    work two ways: (1) while logged into admin, a lightweight poll checks
    for anything due and toasts it — same pattern as the notification bell;
    (2) for a reminder that fires even when nobody's logged in, an admin
    can point a PythonAnywhere (or any cron) scheduled task at
    /admin/api/check-reminders, which emails anything newly due. There's
    no background task runner in this stack, so option 2 is opt-in setup,
    not automatic — see Admin -> To-Do -> Reminder Setup."""
    __tablename__ = "todo_items"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title         = db.Column(db.String(256), nullable=False)
    description   = db.Column(db.Text)
    status        = db.Column(db.String(16), default="todo")  # todo | in_progress | done
    priority      = db.Column(db.String(8), default="medium")  # low | medium | high
    category      = db.Column(db.String(64))
    due_date      = db.Column(db.DateTime)
    reminder_at   = db.Column(db.DateTime)
    reminder_sent = db.Column(db.Boolean, default=False)
    order         = db.Column(db.Integer, default=0)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at  = db.Column(db.DateTime)
    user          = db.relationship("User")


class SocialChannel(db.Model):
    """One connected bot/agent — a WhatsApp number, a Telegram bot, or a
    Facebook Page. `credentials` holds whatever that platform's API needs
    (bot token, or phone-number-id + access token, etc); `auto_reply_rules`
    is an ordered list of {"match": "contains"|"exact", "keywords": [...],
    "reply": "...", "show_products": bool, "product_search": "..."} —
    checked top to bottom, first match wins. `webhook_secret` is a random
    per-channel token baked into that channel's webhook URL so a stranger
    can't POST fake messages at it."""
    __tablename__ = "social_channels"
    id                = db.Column(db.Integer, primary_key=True)
    organization_id   = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=True)
    platform          = db.Column(db.String(16), nullable=False)  # telegram | whatsapp | facebook
    label             = db.Column(db.String(128), nullable=False)  # admin-facing name, e.g. "Support WhatsApp"
    credentials       = db.Column(db.JSON, default=dict)
    webhook_secret    = db.Column(db.String(64), unique=True, index=True)
    active            = db.Column(db.Boolean, default=True)
    connected         = db.Column(db.Boolean, default=False)
    connection_error  = db.Column(db.Text)
    fallback_reply    = db.Column(db.Text, default="Thanks for your message! A team member will get back to you shortly.")
    welcome_message   = db.Column(db.Text)  # sent once to a contact's very first message, before any rule matching
    human_takeover_keywords = db.Column(db.JSON, default=list)  # e.g. ["agent","human"] -> pause bot, notify admin
    auto_reply_rules  = db.Column(db.JSON, default=list)
    message_count     = db.Column(db.Integer, default=0)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    # If you're running this bot AS A SERVICE for a client (not for
    # yourself), link it to their project here — this is purely for
    # billing/organization. Each channel already has its OWN bot
    # token/access token above in `credentials`, so one customer's bot is
    # already fully isolated from another's at the platform-connection
    # level; this field is what makes it show up under the right
    # customer in Financials.
    client_project_id = db.Column(db.Integer, db.ForeignKey("client_projects.id"), nullable=True)
    monthly_fee       = db.Column(db.Float)  # what you charge this client for running this bot, if anything
    # When this bot is for a CUSTOMER (not you), "show matching products"
    # rules need something to search that isn't your own marketplace
    # catalog. This is a simple manually-entered product/service list
    # scoped to just this one bot: [{"name","price","description","link"}].
    # If it's non-empty, show_products searches THIS instead of your
    # global Product table — that's what makes the bot usable for
    # someone else's business, not just yours.
    custom_catalog    = db.Column(db.JSON, default=list)
    # AI Agent Mode: when no keyword rule matches, instead of the static
    # fallback_reply, generate a live reply from these instructions +
    # the conversation + this bot's own product catalog. This is a real,
    # working "AI employee" for THIS bot — not the full multi-tool/RAG
    # agent framework the master prompt envisioned (that's a much bigger,
    # separate system), but it does actually think and respond, not just
    # match keywords.
    ai_agent_enabled      = db.Column(db.Boolean, default=False)
    ai_agent_instructions = db.Column(db.Text)   # persona/system prompt, e.g. "You are Jane's Bakery's assistant..."
    ai_agent_temperature  = db.Column(db.Float, default=0.7)
    client_project    = db.relationship("ClientProject")

    def ensure_secret(self):
        if not self.webhook_secret:
            import secrets
            self.webhook_secret = secrets.token_urlsafe(24)
        return self.webhook_secret


class ChatContact(db.Model):
    """A customer on a specific channel — e.g. one WhatsApp phone number or
    one Telegram chat_id. `human_takeover` pauses auto-replies for this one
    contact (set automatically if they use a takeover keyword, or manually
    by an admin from the inbox) without affecting the channel's other
    conversations."""
    __tablename__ = "chat_contacts"
    id             = db.Column(db.Integer, primary_key=True)
    channel_id     = db.Column(db.Integer, db.ForeignKey("social_channels.id"), nullable=False)
    external_id    = db.Column(db.String(128), nullable=False)  # phone number / chat_id / PSID
    display_name   = db.Column(db.String(128))
    human_takeover = db.Column(db.Boolean, default=False)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    # Staff-only — never sent to the customer. For handoff context between
    # whoever's answering this conversation ("waiting on refund approval").
    internal_notes = db.Column(db.Text)
    tags           = db.Column(db.JSON, default=list)  # e.g. ["vip","refund-issue"] — for filtering the inbox
    department     = db.Column(db.String(32))          # sales, support, billing, general — set manually or by AI analysis
    sentiment      = db.Column(db.String(16))          # positive, neutral, negative — set by on-demand AI analysis, not automatic on every message
    channel        = db.relationship("SocialChannel")

    __table_args__ = (db.UniqueConstraint("channel_id", "external_id", name="uq_channel_contact"),)


class ChatMessage(db.Model):
    """One inbound or outbound message, for the admin conversation inbox
    and for debugging what the bot actually said."""
    __tablename__ = "chat_messages"
    id          = db.Column(db.Integer, primary_key=True)
    contact_id  = db.Column(db.Integer, db.ForeignKey("chat_contacts.id"), nullable=False)
    direction   = db.Column(db.String(8), nullable=False)  # in | out
    body        = db.Column(db.Text)
    sent_by     = db.Column(db.String(16), default="bot")  # bot | admin | customer
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    contact     = db.relationship("ChatContact")


# ── Premium Product Access ────────────────────────────────────────────

class UserProductAccess(db.Model):
    """Tracks which premium dashboard features a user has unlocked via purchase."""
    __tablename__ = "user_product_access"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_slug  = db.Column(db.String(128), nullable=False, index=True)
    order_id      = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    activated_at  = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at    = db.Column(db.DateTime, nullable=True)  # None = lifetime
    active        = db.Column(db.Boolean, default=True)
    user          = db.relationship("User")
    order         = db.relationship("Order")
    __table_args__ = (db.UniqueConstraint("user_id", "product_slug", name="uq_user_product"),)


class UserWebsite(db.Model):
    """Websites created by users via the Website Builder premium tool.

    `pages` entries now carry `css`/`js` alongside `html` so a generated
    site is genuinely multi-file (index.html + style.css + script.js per
    page) instead of one embedded blob — old rows with only `html` still
    work fine, `css`/`js` just default to empty string for them.

    `chat_history` is what makes the prompt box an actual continuing
    conversation (Lovable-style) instead of a one-shot generator that
    forgets the site the moment you ask for a change: each page keeps its
    own list of {"role","content"} turns, fed back to the AI on every
    follow-up prompt so "make the header sticky" edits the existing site
    instead of generating an unrelated new one.
    """
    __tablename__ = "user_websites"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title         = db.Column(db.String(256), nullable=False)
    slug          = db.Column(db.String(256), unique=True, index=True)
    pages         = db.Column(db.JSON, default=list)   # [{"name":"Home","html":"...","css":"...","js":"...","order":0}, ...]
    settings      = db.Column(db.JSON, default=dict)   # {"theme","fonts","colors","nav_style","submissions":[...],...}
    chat_history  = db.Column(db.JSON, default=dict)   # {"Home": [{"role":"user"/"assistant","content":"..."}], ...} per page
    github_repo   = db.Column(db.String(256), nullable=True)   # "owner/repo" once pushed
    data_store    = db.Column(db.JSON, default=dict)   # {"products": [{"id":..,...}], "orders": [...]} — only
                                                         # populated when a site actually needs structured data
                                                         # (e-commerce, bookings, listings...), never forced.
    published     = db.Column(db.Boolean, default=False)
    subdomain     = db.Column(db.String(64), unique=True, nullable=True, index=True)
    custom_domain = db.Column(db.String(256), nullable=True)
    view_count    = db.Column(db.Integer, default=0)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user          = db.relationship("User")

    def get_page(self, name):
        """Case-insensitive lookup of a page by name, falling back to the
        first page (or None) — used everywhere a page name might be
        stale/missing rather than repeating the same loop."""
        pages = self.pages or []
        name = (name or "Home").lower()
        for p in pages:
            if (p.get("name") or "").lower() == name:
                return p
        return pages[0] if pages else None


class UserFunnel(db.Model):
    """Sales funnels created by users via the Funnel Builder premium tool.

    `steps` (legacy JSON blob) is kept ONLY so old rows / the download
    ZIP fallback never crash on data written before the FunnelPage table
    existed. Since the Foundation rebuild, real pages live in the
    `FunnelPage` table (see below) and are the source of truth for the
    flow builder, routing, and publishing — `steps` is no longer written
    to by the app and should be treated as read-only migration residue.
    """
    __tablename__ = "user_funnels"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title         = db.Column(db.String(256), nullable=False)
    slug          = db.Column(db.String(256), unique=True, index=True)
    steps         = db.Column(db.JSON, default=list)   # LEGACY — see FunnelPage. Kept for old-row fallback only.
    settings      = db.Column(db.JSON, default=dict)   # {"theme","pixel_id","analytics",...}
    published     = db.Column(db.Boolean, default=False)
    subdomain     = db.Column(db.String(64), unique=True, nullable=True, index=True)
    entry_page_id = db.Column(db.Integer, db.ForeignKey("funnel_pages.id", ondelete="SET NULL"), nullable=True)
    view_count    = db.Column(db.Integer, default=0)
    conversion_count = db.Column(db.Integer, default=0)
    smtp_credentials_encrypted = db.Column(db.Text, nullable=True)  # Fernet-encrypted {"host","port","username","password","use_tls","from_email"} — same pattern as UserChatbot.whatsapp_credentials_encrypted
    canvas_positions = db.Column(db.JSON, default=dict)  # {"<page_id>": {"x": 120, "y": 80}} — Flow Builder node layout, same pattern as AutomationWorkflow.canvas_positions. Purely cosmetic, never affects routing.
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user          = db.relationship("User")
    pages         = db.relationship(
        "FunnelPage", backref="funnel", lazy="dynamic",
        order_by="FunnelPage.order_index",
        primaryjoin="UserFunnel.id==FunnelPage.funnel_id",
        foreign_keys="FunnelPage.funnel_id",
        cascade="all, delete-orphan",
    )
    entry_page    = db.relationship("FunnelPage", foreign_keys=[entry_page_id], post_update=True)

    def ordered_pages(self):
        return self.pages.order_by(FunnelPage.order_index.asc()).all()

    def set_smtp_credentials(self, host, port, username, password, from_email, use_tls=True):
        """Own SMTP for this funnel's outbound receipts — real per-seller
        sending (mail actually originates from their own mail account),
        not just a From-name/Reply-To cosmetic override. Encrypted at
        rest with the same Fernet helper used for WhatsApp credentials."""
        from app.utils.crypto import encrypt_json
        self.smtp_credentials_encrypted = encrypt_json({
            "host": (host or "").strip(), "port": int(port or 587),
            "username": (username or "").strip(), "password": password or "",
            "from_email": (from_email or "").strip(), "use_tls": bool(use_tls),
        })

    def get_smtp_credentials(self):
        if not self.smtp_credentials_encrypted:
            return None
        from app.utils.crypto import decrypt_json
        try:
            return decrypt_json(self.smtp_credentials_encrypted)
        except Exception:
            return None

    @property
    def smtp_connected(self):
        creds = self.get_smtp_credentials()
        return bool(creds and creds.get("host") and creds.get("username"))


# Funnel page types recognised by the Flow Builder. Kept as a plain tuple
# (not a DB enum) so new types can be added later without a migration.
FUNNEL_PAGE_TYPES = (
    "landing", "sales", "checkout", "thank_you", "upsell", "downsell",
    "webinar_registration", "webinar_replay", "booking", "lead_capture",
    "survey", "quiz", "application", "membership_login",
    "membership_registration", "order_confirmation", "custom",
)


class FunnelPage(db.Model):
    """A single page inside a funnel's flow.

    Replaces the old `UserFunnel.steps` JSON blob with a real, addressable
    row per page so the Flow Builder can connect, reorder, and branch
    between pages individually instead of rewriting one giant blob on
    every change.

    Routing model:
      - `next_page_id`   — the default "continue" connection (linear flow).
      - `branch_yes_id`  — for upsell/downsell/quiz-style pages: where the
                            visitor goes if they accept / answer yes.
      - `branch_no_id`   — where the visitor goes if they decline / answer no.
    All three are optional; a page with none set is a dead end (e.g. the
    final Thank You page).
    """
    __tablename__ = "funnel_pages"
    id             = db.Column(db.Integer, primary_key=True)
    funnel_id      = db.Column(db.Integer, db.ForeignKey("user_funnels.id", ondelete="CASCADE"), nullable=False, index=True)
    page_type      = db.Column(db.String(32), nullable=False, default="custom")
    title          = db.Column(db.String(256), nullable=False, default="Untitled Page")
    slug           = db.Column(db.String(128), nullable=False)   # unique within the funnel, not globally
    order_index    = db.Column(db.Integer, nullable=False, default=0)
    html_content   = db.Column(db.Text, default="")
    builder_mode   = db.Column(db.String(16), nullable=False, default="code")  # 'ai' | 'blocks' | 'code' — which editor tab last built this page
    blocks         = db.Column(db.JSON, default=list)   # structured content when builder_mode == 'blocks'; see app/utils/funnel_blocks.py
    settings       = db.Column(db.JSON, default=dict)   # reserved for Milestone 3 (SEO/scripts/domain/password)
    next_page_id   = db.Column(db.Integer, db.ForeignKey("funnel_pages.id", ondelete="SET NULL"), nullable=True)
    branch_yes_id  = db.Column(db.Integer, db.ForeignKey("funnel_pages.id", ondelete="SET NULL"), nullable=True)
    branch_no_id   = db.Column(db.Integer, db.ForeignKey("funnel_pages.id", ondelete="SET NULL"), nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    next_page  = db.relationship("FunnelPage", remote_side=[id], foreign_keys=[next_page_id])
    branch_yes = db.relationship("FunnelPage", remote_side=[id], foreign_keys=[branch_yes_id])
    branch_no  = db.relationship("FunnelPage", remote_side=[id], foreign_keys=[branch_no_id])

    __table_args__ = (db.UniqueConstraint("funnel_id", "slug", name="uq_funnel_page_slug"),)

    def to_dict(self):
        return {
            "id": self.id, "funnel_id": self.funnel_id,
            "page_type": self.page_type, "title": self.title, "slug": self.slug,
            "order_index": self.order_index, "html": self.html_content or "",
            "builder_mode": self.builder_mode or "code", "blocks": self.blocks or [],
            "next_page_id": self.next_page_id,
            "branch_yes_id": self.branch_yes_id, "branch_no_id": self.branch_no_id,
            "settings": self.settings or {},
        }


class FunnelOrder(db.Model):
    """A completed (or attempted) checkout on a funnel's Checkout-type
    page. Separate from UserPaymentLink/Order (those are the standalone
    Payment Links / marketplace products) — this is scoped to a single
    FunnelPage's checkout config so funnel analytics and the order
    history shown in the builder stay self-contained per funnel."""
    __tablename__ = "funnel_orders"
    id                 = db.Column(db.Integer, primary_key=True)
    funnel_id          = db.Column(db.Integer, db.ForeignKey("user_funnels.id", ondelete="CASCADE"), nullable=False, index=True)
    page_id            = db.Column(db.Integer, db.ForeignKey("funnel_pages.id", ondelete="SET NULL"), nullable=True)
    user_id            = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # funnel owner, for quick "my orders" queries
    customer_name      = db.Column(db.String(256))
    customer_email     = db.Column(db.String(256))
    product_name       = db.Column(db.String(256))
    amount             = db.Column(db.Numeric(10, 2), nullable=False)
    currency            = db.Column(db.String(8), default=default_site_currency)
    gateway            = db.Column(db.String(32))
    status             = db.Column(db.String(32), default="pending")   # pending, paid, failed
    gateway_reference  = db.Column(db.String(256))
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at            = db.Column(db.DateTime)

    funnel = db.relationship("UserFunnel")
    user   = db.relationship("User")


class FunnelLead(db.Model):
    """A submission from a Form block on any funnel page — the actual
    "how do I collect information from the sales funnel" mechanism.
    Previously there was a Lead Capture page TYPE but no form block and
    nowhere for a submission to go, so a "Lead Capture" page had no way
    to actually capture anything. `data` holds whatever fields the form
    block was configured with (name/email/phone/custom), keyed by each
    field's own key so different forms on different pages don't collide."""
    __tablename__ = "funnel_leads"
    id          = db.Column(db.Integer, primary_key=True)
    funnel_id   = db.Column(db.Integer, db.ForeignKey("user_funnels.id", ondelete="CASCADE"), nullable=False, index=True)
    page_id     = db.Column(db.Integer, db.ForeignKey("funnel_pages.id", ondelete="SET NULL"), nullable=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    block_id    = db.Column(db.String(64))          # which Form block on the page, in case a page has more than one
    data        = db.Column(db.JSON, default=dict)  # {"name": "...", "email": "...", ...} per the form's configured fields
    source_ip   = db.Column(db.String(64))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    funnel = db.relationship("UserFunnel")
    user   = db.relationship("User")


class FunnelLicenseKey(db.Model):
    """A real license key for a funnel's WordPress plugin export, bound
    to a single domain on first activation. This is the actual
    "subscription plan" enforcement for the WordPress export — distinct
    from (and stronger than) the plain account-level has_product_access()
    check that funnel_page_embed() fell back to before: that only
    confirmed the OWNER's Bazillin subscription was active, not that a
    given WordPress install was authorized at all. A key issued for
    siteA.com now gets rejected if presented from siteB.com, even while
    the owner's subscription is perfectly current.

    One row per WordPress plugin download — re-exporting mints a fresh
    key so a copied/leaked old plugin file doesn't silently keep
    working forever."""
    __tablename__ = "funnel_license_keys"
    id              = db.Column(db.Integer, primary_key=True)
    funnel_id       = db.Column(db.Integer, db.ForeignKey("user_funnels.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key             = db.Column(db.String(64), unique=True, nullable=False, index=True)
    domain          = db.Column(db.String(256))          # bound on first successful activation; null = not yet activated
    status          = db.Column(db.String(16), default="active")  # active, revoked
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    activated_at    = db.Column(db.DateTime)
    last_checked_at = db.Column(db.DateTime)
    check_count     = db.Column(db.Integer, default=0)

    funnel = db.relationship("UserFunnel")
    user   = db.relationship("User")


class UserInvoice(db.Model):
    """Invoices created by users via the Invoice Generator premium tool.
    Distinct from the admin Invoice model which is for client project billing."""
    __tablename__ = "user_invoices"
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invoice_number  = db.Column(db.String(64), nullable=False)
    client_name     = db.Column(db.String(256))
    client_email    = db.Column(db.String(256))
    client_address  = db.Column(db.Text)
    client_phone    = db.Column(db.String(64))
    items           = db.Column(db.JSON, default=list)   # [{"description":"..","qty":1,"rate":100,"amount":100},...]
    subtotal        = db.Column(db.Numeric(10, 2), default=0)
    tax_rate        = db.Column(db.Float, default=0)
    tax_amount      = db.Column(db.Numeric(10, 2), default=0)
    discount        = db.Column(db.Numeric(10, 2), default=0)
    total           = db.Column(db.Numeric(10, 2), default=0)
    currency        = db.Column(db.String(8), default=default_site_currency)
    status          = db.Column(db.String(32), default="draft")  # draft, sent, paid, overdue, cancelled
    due_date        = db.Column(db.Date)
    notes           = db.Column(db.Text)
    terms           = db.Column(db.Text)
    logo_url        = db.Column(db.String(512))
    business_name   = db.Column(db.String(256))
    business_email  = db.Column(db.String(256))
    business_address = db.Column(db.Text)
    business_phone  = db.Column(db.String(64))
    payment_link_id = db.Column(db.Integer, db.ForeignKey("user_payment_links.id", ondelete="SET NULL"), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at         = db.Column(db.DateTime)
    user            = db.relationship("User")


class UserPaymentGateway(db.Model):
    """A payment gateway a user has connected to their OWN account, so
    Payment Links they create charge into their account — not the site
    admin's. One row per (user, gateway); credentials are stored
    encrypted (see app.utils.crypto) and never returned to the browser
    in full."""
    __tablename__ = "user_payment_gateways"
    id                     = db.Column(db.Integer, primary_key=True)
    user_id                = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    gateway                = db.Column(db.String(32), nullable=False)   # stripe, paystack, flutterwave, paypal
    mode                   = db.Column(db.String(16), default="live")   # live / test, where applicable
    credentials_encrypted  = db.Column(db.Text)
    last4                  = db.Column(db.String(8))    # last few chars of the main secret, for display only
    is_default             = db.Column(db.Boolean, default=False)
    active                 = db.Column(db.Boolean, default=True)
    created_at             = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at             = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user                   = db.relationship("User")

    __table_args__ = (db.UniqueConstraint("user_id", "gateway", name="uq_user_payment_gateway"),)


class UserPaymentLink(db.Model):
    """Payment links created by users via the Payment Link Generator premium tool.
    Distinct from the admin PaymentLink model."""
    __tablename__ = "user_payment_links"
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title           = db.Column(db.String(256), nullable=False)
    slug            = db.Column(db.String(128), unique=True, nullable=False, index=True)
    amount          = db.Column(db.Numeric(10, 2), nullable=False)
    currency        = db.Column(db.String(8), default=default_site_currency)
    description     = db.Column(db.Text)
    active          = db.Column(db.Boolean, default=True)
    settings        = db.Column(db.JSON, default=dict)   # {tax, discount, coupon, expiry, branding, success_msg, redirect_url,
                                                           #  link_type, min_amount, max_amount, purchase_limit, password,
                                                           #  enabled_gateways, thank_you: {...}, emails: {...}, archived}
    view_count      = db.Column(db.Integer, default=0)
    payment_count   = db.Column(db.Integer, default=0)
    total_collected = db.Column(db.Numeric(10, 2), default=0)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user            = db.relationship("User")
    orders          = db.relationship("UserPaymentLinkOrder", backref="link", cascade="all, delete-orphan")


class UserPaymentLinkOrder(db.Model):
    """A real, individual transaction against a UserPaymentLink — gives
    Payment Links actual Order + Customer records instead of just the
    aggregate payment_count/total_collected counters on the link itself."""
    __tablename__ = "user_payment_link_orders"
    id              = db.Column(db.Integer, primary_key=True)
    payment_link_id = db.Column(db.Integer, db.ForeignKey("user_payment_links.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)  # link owner, for fast "my orders"
    buyer_name      = db.Column(db.String(256))
    buyer_email     = db.Column(db.String(256), index=True)
    amount          = db.Column(db.Numeric(10, 2), nullable=False)
    currency        = db.Column(db.String(8))
    gateway         = db.Column(db.String(32))
    status          = db.Column(db.String(24), default="pending", index=True)  # pending, paid, failed, refunded
    reference       = db.Column(db.String(128), index=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    paid_at         = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id, "buyer_name": self.buyer_name, "buyer_email": self.buyer_email,
            "amount": float(self.amount or 0), "currency": self.currency, "gateway": self.gateway,
            "status": self.status, "reference": self.reference,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None,
        }


class UserChatbot(db.Model):
    """Chatbot configurations created by users via the WhatsApp Bot premium tool."""
    __tablename__ = "user_chatbots"
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name            = db.Column(db.String(128), nullable=False)
    platform        = db.Column(db.String(32), default="whatsapp")
    greeting        = db.Column(db.Text)
    flows           = db.Column(db.JSON, default=list)   # [{"trigger":"..","steps":[..]},...]
    keywords        = db.Column(db.JSON, default=list)   # [{"pattern":"..","reply":"..","type":"exact|contains|regex"},...]
    auto_replies    = db.Column(db.JSON, default=list)
    ai_enabled      = db.Column(db.Boolean, default=False)
    ai_instructions = db.Column(db.Text)
    faqs            = db.Column(db.JSON, default=list)   # [{"question":"..","answer":"..","category":".."},...]
    knowledge_text  = db.Column(db.Text)                  # freeform manual info (about us, policies, pricing...)
    unknown_reply   = db.Column(db.Text)                  # customizable "I don't have that information" message
    knowledge_sources = db.Column(db.JSON, default=list)  # [{"id","type":"url"|"file","title","source","text","added_at"},...] — website pages + uploaded documents
    logo_url        = db.Column(db.String(512))            # bubble/avatar image — shown in the widget button and the chat header
    widget_settings = db.Column(db.JSON, default=dict)      # {position, button_color, icon, animation, show_label, button_text, desktop_visible, mobile_visible} — same shape as UserWhatsAppWidget.settings for consistency
    display_phone   = db.Column(db.String(32))            # wa.me click-to-chat number shown in the builder — cosmetic only, NOT the same as whatsapp_credentials_encrypted's real connected sender number
    active          = db.Column(db.Boolean, default=True)
    message_count   = db.Column(db.Integer, default=0)
    whatsapp_credentials_encrypted = db.Column(db.Text)  # Fernet-encrypted {"account_sid","auth_token","whatsapp_number"} — this bot's OWN Twilio WhatsApp sender, separate from the site-wide Admin -> Settings -> Twilio config used by the telephony webhook's single admin agent.
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user            = db.relationship("User")

    def get_whatsapp_credentials(self):
        """Decrypts this bot's own connected Twilio WhatsApp sender, if
        any. Same Fernet scheme as AutomationCredential above."""
        from app.utils.crypto import decrypt_json
        return decrypt_json(self.whatsapp_credentials_encrypted) if self.whatsapp_credentials_encrypted else {}

    def set_whatsapp_credentials(self, account_sid, auth_token, whatsapp_number):
        from app.utils.crypto import encrypt_json
        self.whatsapp_credentials_encrypted = encrypt_json({
            "account_sid": (account_sid or "").strip(),
            "auth_token": (auth_token or "").strip(),
            "whatsapp_number": (whatsapp_number or "").strip(),
        })

    @property
    def whatsapp_connected(self):
        return bool(self.whatsapp_credentials_encrypted)


class UserChatbotMessage(db.Model):
    """One message in a widget conversation — powers the real "History"
    view on both WhatsApp Bot and AI Chatbot's own dashboard pages
    (previously neither had any conversation history at all, only a raw
    message_count). Grouped by session_id (a random id the browser
    generates once per visit and sends with every request in that
    session — see chatbot_embed.html) so a page shows real distinct
    conversations, not just a flat message firehose."""
    __tablename__ = "user_chatbot_messages"
    id          = db.Column(db.Integer, primary_key=True)
    bot_id      = db.Column(db.Integer, db.ForeignKey("user_chatbots.id", ondelete="CASCADE"), nullable=False)
    session_id  = db.Column(db.String(64), nullable=False)
    sender      = db.Column(db.String(8), nullable=False)   # "user" | "bot"
    text        = db.Column(db.Text, nullable=False)
    source      = db.Column(db.String(16))                   # "keyword" | "ai" | "fallback" | "handoff" | None (for the user's own messages)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    bot = db.relationship("UserChatbot")

    __table_args__ = (db.Index("ix_user_chatbot_messages_bot_session", "bot_id", "session_id"),)


class UserWhatsAppWidget(db.Model):
    """A simple click-to-chat WhatsApp widget — NOT the WhatsApp Business
    API bot (UserChatbot above). No API keys, no Meta app, no webhooks —
    this just generates a wa.me link and a floating button, wrapped in a
    real embed script / hosted page / WordPress plugin download. Its own
    product, its own slug (whatsapp-widget), deliberately kept separate
    from whatsapp-bot per the user's explicit spec."""
    __tablename__ = "user_whatsapp_widgets"
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name            = db.Column(db.String(128), nullable=False, default="My WhatsApp Widget")
    slug            = db.Column(db.String(64), unique=True, nullable=False, index=True)
    phone_number    = db.Column(db.String(32), nullable=False)   # E.164-ish, digits only after +
    business_name   = db.Column(db.String(128))
    welcome_message = db.Column(db.Text)      # shown in the chat-preview bubble before click
    default_message = db.Column(db.Text)      # pre-filled into the WhatsApp chat box
    profile_image   = db.Column(db.String(512))
    active          = db.Column(db.Boolean, default=True)
    settings        = db.Column(db.JSON, default=dict)  # {position, button_color, icon, animation, show_label,
                                                          #  desktop_visible, mobile_visible, button_text}
    view_count      = db.Column(db.Integer, default=0)
    click_count     = db.Column(db.Integer, default=0)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user            = db.relationship("User")

    def to_dict(self):
        s = self.settings or {}
        return {
            "id": self.id, "name": self.name, "slug": self.slug, "phone_number": self.phone_number,
            "business_name": self.business_name, "welcome_message": self.welcome_message,
            "default_message": self.default_message, "profile_image": self.profile_image,
            "active": self.active, "settings": s,
            "view_count": self.view_count or 0, "click_count": self.click_count or 0,
            "click_rate": round((self.click_count or 0) / self.view_count * 100, 1) if self.view_count else 0,
        }


class UserWhatsAppWidgetEvent(db.Model):
    """One view or click event, timestamped — view_count/click_count on
    the widget itself stay as the fast running totals, but neither could
    ever answer "when" — no way to show a real trend over time, only an
    ever-growing number. This is what actually powers the Analytics
    page's daily chart."""
    __tablename__ = "user_whatsapp_widget_events"
    id          = db.Column(db.Integer, primary_key=True)
    widget_id   = db.Column(db.Integer, db.ForeignKey("user_whatsapp_widgets.id", ondelete="CASCADE"), nullable=False)
    event_type  = db.Column(db.String(8), nullable=False)  # "view" | "click"
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.Index("ix_user_whatsapp_widget_events_widget", "widget_id", "event_type"),)


# ── Premium Workspace Add-on Modules ───────────────────────────────────

class PremiumModule(db.Model):
    """Configuration for dashboard premium add-on modules (Pricing, Status)."""
    __tablename__ = "premium_modules"
    id            = db.Column(db.Integer, primary_key=True)
    slug          = db.Column(db.String(64), unique=True, index=True, nullable=False)
    name          = db.Column(db.String(128), nullable=False)
    price         = db.Column(db.Numeric(10, 2), default=0.0)
    active        = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


class VoiceGeneration(db.Model):
    """A persistent, user-owned Text-to-Speech generation."""
    __tablename__ = "voice_generations"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    text         = db.Column(db.Text, nullable=False)
    voice_id     = db.Column(db.String(64), nullable=False)
    voice_name   = db.Column(db.String(128))
    file_path    = db.Column(db.String(512), nullable=False)
    file_format  = db.Column(db.String(8), default="mp3")
    duration_sec = db.Column(db.Float)
    char_count   = db.Column(db.Integer)
    credits_used = db.Column(db.Integer, default=1)
    is_favorite  = db.Column(db.Boolean, default=False)
    title        = db.Column(db.String(256))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User")

    def to_dict(self):
        from flask import url_for
        return {
            "id": self.id, "text": self.text, "title": self.title or (self.text[:60] + ("…" if len(self.text) > 60 else "")),
            "voice_id": self.voice_id, "voice_name": self.voice_name,
            "url": url_for("static", filename=self.file_path), "format": self.file_format,
            "duration_sec": self.duration_sec, "char_count": self.char_count,
            "credits_used": self.credits_used, "is_favorite": bool(self.is_favorite),
            "created_at": self.created_at.strftime("%b %d, %Y %H:%M") if self.created_at else "",
        }


class UserVoiceSample(db.Model):
    """A user's own recorded voice clip, saved to their personal 'My
    Voices' library in Voice Studio (favorited by default since saving
    it is an explicit action). This is a personal audio-clip library —
    playback, download, rename, delete — NOT voice cloning: turning a
    recorded sample into a new synthesized voice needs a paid cloning
    provider (e.g. ElevenLabs, if ELEVENLABS_API_KEY is configured) and
    isn't something free CPU-only hosting can do reliably."""
    __tablename__ = "user_voice_samples"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name         = db.Column(db.String(128), nullable=False, default="My Recording")
    file_path    = db.Column(db.String(512), nullable=False)
    file_format  = db.Column(db.String(8), default="webm")
    duration_sec = db.Column(db.Float)
    is_favorite  = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name,
            "url": f"/static/{self.file_path}", "format": self.file_format,
            "duration_sec": self.duration_sec, "is_favorite": bool(self.is_favorite),
            "created_at": self.created_at.strftime("%b %d, %Y %H:%M") if self.created_at else "",
        }


# ── AI Credit Store ─────────────────────────────────────────────────────
# Admin-configurable packages users can buy to top up User.credits (the
# existing flat balance every AI tool already deducts from — see
# credits_used on VoiceGeneration above). Deliberately NOT a rebuild of
# credit accounting itself (no free/purchased split, no refill timer) —
# scoped to the purchase side: packages, pricing, and a real ledger so
# every addition is traceable to an order or an admin action.

class CreditPackage(db.Model):
    """One row per purchasable credit bundle. Admin manages these under
    Admin -> Credit Packages; users see the active ones on the dashboard
    Buy Credits page."""
    __tablename__ = "credit_packages"
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(128), nullable=False)
    credits      = db.Column(db.Integer, nullable=False)
    price        = db.Column(db.Numeric(10, 2), nullable=False)
    currency     = db.Column(db.String(8), default=default_site_currency)
    description  = db.Column(db.String(256))
    is_popular   = db.Column(db.Boolean, default=False)
    active       = db.Column(db.Boolean, default=True)
    sort_order   = db.Column(db.Integer, default=0)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "credits": self.credits,
            "price": float(self.price or 0), "currency": self.currency,
            "description": self.description, "is_popular": bool(self.is_popular),
            "active": bool(self.active), "sort_order": self.sort_order or 0,
        }


class CreditPurchase(db.Model):
    """One row per attempted credit purchase — mirrors the marketplace
    Order/gateway-callback pattern (see app/payments/routes.py) but kept
    separate from the `orders` table since credit packages aren't
    marketplace Products. `status` moves pending -> paid exactly once;
    grant_purchased_credits() is guarded on that so a webhook/redirect
    race can never double-credit."""
    __tablename__ = "credit_purchases"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    package_id    = db.Column(db.Integer, db.ForeignKey("credit_packages.id"), nullable=True)  # NULL = bought via the quantity stepper, not a fixed package
    credits       = db.Column(db.Integer, nullable=False)   # snapshot at purchase time — admin changing the package later must not alter a past order
    amount        = db.Column(db.Numeric(10, 2), nullable=False)
    currency      = db.Column(db.String(8), default=default_site_currency)
    status        = db.Column(db.String(32), default="pending", index=True)  # pending | paid | failed
    gateway       = db.Column(db.String(32))
    gateway_ref   = db.Column(db.String(256))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user    = db.relationship("User")
    package = db.relationship("CreditPackage")

    @property
    def label(self):
        return self.package.name if self.package else f"{self.credits:,} Credits"


class CreditTransaction(db.Model):
    """The credit ledger. Every balance change — purchase, AI usage, admin
    adjustment, refund — writes one row here, so the balance is always
    reconstructable and never just silently overwritten."""
    __tablename__ = "credit_transactions"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type         = db.Column(db.String(32), nullable=False)   # purchase | usage | admin_adjustment | refund
    amount       = db.Column(db.Integer, nullable=False)      # positive = credit, negative = debit
    balance_after = db.Column(db.Integer)
    reason       = db.Column(db.String(256))
    reference    = db.Column(db.String(128))   # e.g. "credit_purchase:<id>", "voice_generation:<id>"
    created_by   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # admin id for manual adjustments
    created_at   = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User", foreign_keys=[user_id])

    def to_dict(self):
        return {
            "id": self.id, "type": self.type, "amount": self.amount,
            "balance_after": self.balance_after, "reason": self.reason,
            "reference": self.reference,
            "created_at": self.created_at.strftime("%b %d, %Y %H:%M") if self.created_at else "",
        }
