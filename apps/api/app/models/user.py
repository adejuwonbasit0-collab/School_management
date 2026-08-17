from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class Role(db.Model):
    __tablename__ = "roles"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256))
    permissions = db.Column(db.JSON, default=list)
    is_system   = db.Column(db.Boolean, default=False)
    users       = db.relationship("User", back_populates="role", lazy="dynamic")
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def has_permission(self, perm):
        return perm in (self.permissions or []) or "all" in (self.permissions or [])

    @classmethod
    def seed_defaults(cls):
        defaults = [
            ("admin",      ["all"],                          True),
            ("user",       ["read"],                         True),
            ("freelancer", ["read", "freelance.apply"],      True),
            ("client",     ["read", "freelance.post"],       True),
        ]
        for name, perms, system in defaults:
            if not cls.query.filter_by(name=name).first():
                db.session.add(cls(name=name, permissions=perms, is_system=system))
        db.session.commit()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id               = db.Column(db.Integer, primary_key=True)
    name             = db.Column(db.String(128))
    email            = db.Column(db.String(256), unique=True, nullable=False, index=True)
    password_hash    = db.Column(db.String(512))
    role_id          = db.Column(db.Integer, db.ForeignKey("roles.id"))
    role             = db.relationship("Role", back_populates="users")
    avatar           = db.Column(db.String(512))
    bio              = db.Column(db.Text)
    website          = db.Column(db.String(256))
    location         = db.Column(db.String(128))
    phone            = db.Column(db.String(32))
    is_active        = db.Column(db.Boolean, default=True)
    is_banned        = db.Column(db.Boolean, default=False)
    email_verified   = db.Column(db.Boolean, default=False)
    credits          = db.Column(db.Integer, default=10)
    # Free-credit refill bookkeeping (see app/utils/credits.py). `credits`
    # above stays the single TOTAL balance every AI tool already deducts
    # from — free_credits_available just tracks how much of that total is
    # currently "free allotment" (max 2, refills every 12h), so free vs
    # purchased can be displayed and free is spent first, without a
    # second balance to keep in sync. Defaults to 0, NOT 2 — the initial
    # free grant is applied by ensure_free_refill() on first check (which
    # ADDS 2 to whatever `credits` already is), so it never double-counts
    # against the pre-existing `credits` signup bonus above.
    free_credits_available = db.Column(db.Integer, default=0)
    last_free_credit_refill = db.Column(db.DateTime, nullable=True)
    email_notifications = db.Column(db.Boolean, default=True)
    timezone         = db.Column(db.String(64), default="UTC")
    stripe_customer_id = db.Column(db.String(128))
    last_login_at    = db.Column(db.DateTime)
    last_login_ip    = db.Column(db.String(64))
    known_ips        = db.Column(db.JSON, default=list)
    totp_secret      = db.Column(db.String(64))
    totp_enabled     = db.Column(db.Boolean, default=False)
    email_2fa_enabled = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders               = db.relationship("Order",               back_populates="user", lazy="dynamic")
    downloads            = db.relationship("Download",            back_populates="user", lazy="dynamic")
    notifications        = db.relationship("Notification",        back_populates="user", lazy="dynamic")
    api_usage            = db.relationship("ApiUsage",            back_populates="user", lazy="dynamic")
    code_projects        = db.relationship("CodeProject",         back_populates="user", lazy="dynamic")
    hosting_subs         = db.relationship("HostingSubscription", back_populates="user", lazy="dynamic")
    freelancer_profile   = db.relationship("FreelancerProfile",   back_populates="user", uselist=False)
    client_profile       = db.relationship("ClientProfile",       back_populates="user", uselist=False)
    profile              = db.relationship("Profile",             back_populates="user", uselist=False)
    wishlist_items       = db.relationship("WishlistItem",        back_populates="user", lazy="dynamic")
    proposals            = db.relationship("Proposal",            back_populates="user", lazy="dynamic")
    jobs_posted          = db.relationship("JobPost",             back_populates="client", lazy="dynamic")
    blog_posts           = db.relationship("BlogPost",            back_populates="author", lazy="dynamic")
    audit_logs           = db.relationship("AuditLog",            back_populates="user",  lazy="dynamic")
    transactions         = db.relationship("Transaction",         back_populates="user",  lazy="dynamic")
    sent_messages        = db.relationship("Message", foreign_keys="Message.sender_id",   back_populates="sender",   lazy="dynamic")
    received_messages    = db.relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, perm):
        return self.role.has_permission(perm) if self.role else False

    def is_admin(self):
        return bool(self.role and self.role.name == "admin")

    def is_freelancer(self):
        return bool(self.role and self.role.name == "freelancer")

    def is_client(self):
        return bool(self.role and self.role.name == "client")

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar
        return f"https://ui-avatars.com/api/?name={self.name or self.email}&background=0f172a&color=00f5ff&bold=true"

    def __repr__(self):
        return f"<User {self.email}>"
