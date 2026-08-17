from datetime import datetime
from app.extensions import db


class SiteSetting(db.Model):
    __tablename__ = "site_settings"
    id         = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=True)
    key        = db.Column(db.String(128), nullable=False, index=True)
    value      = db.Column(db.Text)
    value_type = db.Column(db.String(32), default="string")
    group      = db.Column(db.String(64), default="general")
    label      = db.Column(db.String(128))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("organization_id", "key", name="uq_setting_org_key"),)

    def typed_value(self):
        import json
        if self.value_type == "bool":
            return str(self.value).lower() in ("true", "1", "yes")
        if self.value_type == "int":
            return int(self.value or 0)
        if self.value_type == "json":
            try: return json.loads(self.value)
            except: return {}
        return self.value


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action     = db.Column(db.String(128), nullable=False)
    target     = db.Column(db.String(256))
    detail     = db.Column(db.Text)
    ip_address = db.Column(db.String(64))
    user_agent = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user       = db.relationship("User", back_populates="audit_logs")


class Notification(db.Model):
    __tablename__ = "notifications"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type       = db.Column(db.String(64))
    title      = db.Column(db.String(256))
    body       = db.Column(db.Text)
    read       = db.Column(db.Boolean, default=False)
    link       = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user       = db.relationship("User", back_populates="notifications")


class Agent(db.Model):
    """One configured 'AI employee' — a named persona with its own system
    prompt/instructions, run through the SAME tool-calling engine as the
    AI Console (app/utils/ai_agent_tools.py — create blog drafts, todos,
    workflows, popups, etc), so an agent can actually do things, not just
    talk. This is intentionally a single-persona MVP, not the full
    scheduling/knowledge-base system described in the master prompt — no
    per-agent tool permission scoping (all admin-side agents share the
    same tool set today), no scheduled/autonomous runs (an agent only
    acts when a message is sent to it).

    If `customer_facing` is on, the agent gets a public chat widget
    (app/cms/routes.py agent_widget/agent_widget_send) — but that public
    path deliberately runs the agent through plain chat only (_call_ai),
    NOT the tool-calling engine. A public visitor triggering "send a real
    email" or "create a CRM lead" with no rate limiting or review is a
    real abuse vector, so customer-facing = conversation only, never
    action-taking, until real per-agent permission scoping exists."""
    __tablename__ = "agents"
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(128), nullable=False)
    avatar_emoji = db.Column(db.String(8), default="🤖")
    role         = db.Column(db.String(128))       # e.g. "Marketing Manager"
    department   = db.Column(db.String(64))        # e.g. "Marketing", "Support"
    instructions = db.Column(db.Text, nullable=False)  # the agent's system prompt / personality / goals
    active       = db.Column(db.Boolean, default=True)
    customer_facing = db.Column(db.Boolean, default=False)  # exposes a public chat widget — see note below
    public_greeting = db.Column(db.String(400))  # shown as the first message on the public widget
    created_by   = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    tools_permissions = db.Column(db.JSON, default=list)  # list of allowed tools, e.g. ["create_blog_draft"]
    model_name   = db.Column(db.String(128), default="claude-3-5-sonnet")
    temperature  = db.Column(db.Float, default=0.7)
    context_window = db.Column(db.Integer, default=4000)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship("AgentMessage", back_populates="agent",
                                order_by="AgentMessage.created_at", cascade="all, delete-orphan")


class AgentMessage(db.Model):
    """One continuous conversation log per agent — unlike the AI Console's
    multiple named threads, each agent here is a single ongoing employee
    you keep talking to, so there's one running history rather than
    separate saved conversations."""
    __tablename__ = "agent_messages"
    id          = db.Column(db.Integer, primary_key=True)
    agent_id    = db.Column(db.Integer, db.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    role        = db.Column(db.String(16), nullable=False)  # user | assistant
    content     = db.Column(db.Text, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    agent = db.relationship("Agent", back_populates="messages")


class AIConsoleThread(db.Model):
    """A saved conversation in the Admin AI Console — separate from the
    public-facing, credit-gated 'Chat' dev tool. This one is admin-only,
    has no credit cost, and keeps real history across sessions so a
    conversation can be picked back up later."""
    __tablename__ = "ai_console_threads"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title       = db.Column(db.String(256), default="New Conversation")
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship("AIConsoleMessage", back_populates="thread",
                                order_by="AIConsoleMessage.created_at", cascade="all, delete-orphan")


class AIConsoleMessage(db.Model):
    __tablename__ = "ai_console_messages"
    id          = db.Column(db.Integer, primary_key=True)
    thread_id   = db.Column(db.Integer, db.ForeignKey("ai_console_threads.id", ondelete="CASCADE"), nullable=False)
    role        = db.Column(db.String(16), nullable=False)  # user | assistant
    content     = db.Column(db.Text, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    thread = db.relationship("AIConsoleThread", back_populates="messages")


class PromptTemplate(db.Model):
    """A reusable, categorized prompt for the AI Console / Content Studio /
    Developer AI tools. Seeded with starter templates on first migration;
    admins can add their own. `variables` is a simple comma-separated list
    of {placeholder} names found in body, shown as fill-in fields in the UI
    so a template isn't just static text pasted in verbatim every time."""
    __tablename__ = "prompt_templates"
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    category    = db.Column(db.String(64), nullable=False, default="General", index=True)
    body        = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(400))
    is_builtin  = db.Column(db.Boolean, default=False)  # seeded, not user-deletable via UI safety net
    created_by  = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    use_count   = db.Column(db.Integer, default=0)

    def variables(self):
        import re
        return sorted(set(re.findall(r"\{(\w+)\}", self.body)))


class Message(db.Model):
    __tablename__ = "messages"
    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content     = db.Column(db.Text, nullable=False)
    read        = db.Column(db.Boolean, default=False)
    thread_id   = db.Column(db.String(128), index=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    sender      = db.relationship("User", foreign_keys=[sender_id],   back_populates="sent_messages")
    receiver    = db.relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")


class EmailTemplate(db.Model):
    __tablename__ = "email_templates"
    id          = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.String(128), unique=True, nullable=False)
    name        = db.Column(db.String(256))
    subject     = db.Column(db.String(512))
    body        = db.Column(db.Text)
    active      = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NewsletterSubscriber(db.Model):
    __tablename__ = "newsletter_subscribers"
    id           = db.Column(db.Integer, primary_key=True)
    email        = db.Column(db.String(256), unique=True, nullable=False)
    name         = db.Column(db.String(128))
    confirmed    = db.Column(db.Boolean, default=False)
    unsubscribed = db.Column(db.Boolean, default=False)
    unsub_token  = db.Column(db.String(64), unique=True, index=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def ensure_token(self):
        if not self.unsub_token:
            import secrets
            self.unsub_token = secrets.token_urlsafe(32)
        return self.unsub_token


class SitePopup(db.Model):
    """Website Automation: a popup shown to visitors on a trigger (delay,
    exit-intent, or scroll depth), optionally scoped to a URL path. Client-
    side JS in partials/popup_loader.html decides WHEN to show it (using
    localStorage for the frequency rule); this table just holds what it
    says and the rules for when it's eligible at all."""
    __tablename__ = "site_popups"
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(128), nullable=False)  # internal label only, never shown to visitors
    headline      = db.Column(db.String(256), nullable=False)
    body_html     = db.Column(db.Text)
    cta_text      = db.Column(db.String(64))
    cta_url       = db.Column(db.String(512))
    trigger_type  = db.Column(db.String(16), default="delay")   # delay | exit_intent | scroll
    trigger_value = db.Column(db.Integer, default=5)            # seconds for delay, % for scroll, unused for exit_intent
    path_pattern  = db.Column(db.String(256))                   # empty/null = all pages; e.g. "/blog" matches any path starting with that
    frequency     = db.Column(db.String(24), default="once_per_session")  # once_per_session | once_per_visitor | always
    active        = db.Column(db.Boolean, default=True)
    impressions   = db.Column(db.Integer, default=0)
    clicks        = db.Column(db.Integer, default=0)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


class NewsletterCampaign(db.Model):
    __tablename__ = "newsletter_campaigns"
    id           = db.Column(db.Integer, primary_key=True)
    subject      = db.Column(db.String(256), nullable=False)
    body_html    = db.Column(db.Text, nullable=False)
    status       = db.Column(db.String(16), default="draft")  # draft | sending | sent | failed
    recipient_count = db.Column(db.Integer, default=0)
    sent_count   = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at      = db.Column(db.DateTime)


class EmailSequence(db.Model):
    """A multi-step drip campaign (Welcome Series, Follow-Up, Abandoned
    Cart, etc.) — different from NewsletterCampaign above, which is a
    single one-off blast. Each subscriber enrolled gets step 1, then step
    2 some days later, and so on, tracked per-subscriber so nobody gets
    the same step twice or gets skipped if a cron run is missed."""
    __tablename__ = "email_sequences"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(128), nullable=False)
    trigger     = db.Column(db.String(64), default="manual")  # manual | newsletter_signup
    active      = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    steps = db.relationship("EmailSequenceStep", back_populates="sequence",
                             order_by="EmailSequenceStep.step_order", cascade="all, delete-orphan")


class EmailSequenceStep(db.Model):
    __tablename__ = "email_sequence_steps"
    id           = db.Column(db.Integer, primary_key=True)
    sequence_id  = db.Column(db.Integer, db.ForeignKey("email_sequences.id", ondelete="CASCADE"), nullable=False)
    step_order   = db.Column(db.Integer, default=0)
    delay_days   = db.Column(db.Integer, default=0)  # days after ENROLLMENT (not after previous step) — simpler to reason about, avoids compounding drift if a cron run gets missed
    subject      = db.Column(db.String(256), nullable=False)
    body_html    = db.Column(db.Text, nullable=False)

    sequence = db.relationship("EmailSequence", back_populates="steps")


class EmailSequenceEnrollment(db.Model):
    __tablename__ = "email_sequence_enrollments"
    id             = db.Column(db.Integer, primary_key=True)
    sequence_id    = db.Column(db.Integer, db.ForeignKey("email_sequences.id", ondelete="CASCADE"), nullable=False)
    subscriber_id  = db.Column(db.Integer, db.ForeignKey("newsletter_subscribers.id", ondelete="CASCADE"), nullable=False)
    current_step   = db.Column(db.Integer, default=0)  # index of the NEXT step still to send
    enrolled_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_sent_at   = db.Column(db.DateTime)
    completed      = db.Column(db.Boolean, default=False)

    sequence   = db.relationship("EmailSequence")
    subscriber = db.relationship("NewsletterSubscriber")

    __table_args__ = (db.UniqueConstraint("sequence_id", "subscriber_id", name="uq_sequence_subscriber"),)


class CmsBlock(db.Model):
    __tablename__ = "cms_blocks"
    id         = db.Column(db.Integer, primary_key=True)
    key        = db.Column(db.String(128), unique=True, nullable=False)
    label      = db.Column(db.String(128))
    type       = db.Column(db.String(64))
    content    = db.Column(db.JSON)
    active     = db.Column(db.Boolean, default=True)
    order      = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ShortenedUrl(db.Model):
    __tablename__ = 'shortened_urls'
    id = db.Column(db.Integer, primary_key=True)
    original = db.Column(db.Text, nullable=False)
    code = db.Column(db.String(16), unique=True, index=True, nullable=False)
    clicks = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='shortened_urls')
