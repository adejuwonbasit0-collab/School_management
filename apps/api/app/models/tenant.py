"""
Multi-tenancy foundation. An Organization is the tenant boundary: bots,
automation workflows, broadcasts, and settings (AI keys, integration
credentials) all belong to exactly one Organization, and one org's data
is never visible to another org's members.

The pre-existing site (portfolio, blog, hire-me flow, etc.) is NOT tenant-
scoped by this first pass — those stay platform-wide, owned by you. Only
the modules clients were actually blocked on (Social Channels, Automation
Studio, Content Studio's channels, and their own integration keys in
Settings) are scoped so far. Everything else (CRM, Financials, Inbox
depth, etc.) gets the same treatment in a follow-up batch.
"""
from datetime import datetime
from app.extensions import db


class Organization(db.Model):
    __tablename__ = "organizations"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(128), nullable=False)
    slug        = db.Column(db.String(64), unique=True, nullable=False, index=True)
    plan        = db.Column(db.String(32), default="free")
    active      = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")

    @staticmethod
    def generate_slug(base: str) -> str:
        import re
        base_slug = re.sub(r'[^a-z0-9]+', '-', (base or "org").lower()).strip('-') or "org"
        slug = base_slug
        n = 1
        while Organization.query.filter_by(slug=slug).first():
            n += 1
            slug = f"{base_slug}-{n}"
        return slug


class OrganizationMember(db.Model):
    """Links a User to an Organization with a role WITHIN that org.
    Separate from the platform-wide User.role (admin/user/freelancer/
    client) — a user can be an 'owner' of their own org while still just
    being a plain 'client'-role user at the platform level."""
    __tablename__ = "organization_members"
    id              = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_role        = db.Column(db.String(32), default="owner")  # owner, admin, staff
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    organization = db.relationship("Organization", back_populates="members")
    user         = db.relationship("User")

    __table_args__ = (db.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),)
