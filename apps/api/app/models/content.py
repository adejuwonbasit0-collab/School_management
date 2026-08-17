from datetime import datetime
from app.extensions import db

class Page(db.Model):
    __tablename__ = "pages"
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(256), nullable=False)
    slug        = db.Column(db.String(256), unique=True, nullable=False, index=True)
    content     = db.Column(db.JSON)
    template    = db.Column(db.String(64), default="default")
    published   = db.Column(db.Boolean, default=False)
    seo_title   = db.Column(db.String(256))
    seo_desc    = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Profile(db.Model):
    __tablename__ = "profiles"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    full_name     = db.Column(db.String(128))
    title         = db.Column(db.String(256))
    subtitle      = db.Column(db.String(256))
    bio           = db.Column(db.Text)
    about         = db.Column(db.Text)
    profile_image = db.Column(db.String(512))
    cover_image   = db.Column(db.String(512))
    intro_video_url = db.Column(db.String(512))
    seo_title     = db.Column(db.String(256))
    seo_desc      = db.Column(db.Text)
    resume_url    = db.Column(db.String(512))
    twitter       = db.Column(db.String(128))
    github        = db.Column(db.String(128))
    linkedin      = db.Column(db.String(128))
    instagram     = db.Column(db.String(128))
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user          = db.relationship("User", back_populates="profile")

class Skill(db.Model):
    __tablename__ = "skills"
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(128), nullable=False)
    category   = db.Column(db.String(64))
    level      = db.Column(db.String(32))
    percentage = db.Column(db.Integer, default=0)
    icon       = db.Column(db.String(256))
    order      = db.Column(db.Integer, default=0)

class Experience(db.Model):
    __tablename__ = "experiences"
    id          = db.Column(db.Integer, primary_key=True)
    company     = db.Column(db.String(256))
    role        = db.Column(db.String(256))
    description = db.Column(db.Text)
    start_date  = db.Column(db.String(32))
    end_date    = db.Column(db.String(32))
    current     = db.Column(db.Boolean, default=False)
    logo        = db.Column(db.String(512))
    order       = db.Column(db.Integer, default=0)

class Education(db.Model):
    __tablename__ = "educations"
    id          = db.Column(db.Integer, primary_key=True)
    institution = db.Column(db.String(256))
    degree      = db.Column(db.String(256))
    field       = db.Column(db.String(256))
    start_year  = db.Column(db.String(16))
    end_year    = db.Column(db.String(16))
    logo        = db.Column(db.String(512))
    order       = db.Column(db.Integer, default=0)

class Certification(db.Model):
    __tablename__ = "certifications"
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(256))
    issuer     = db.Column(db.String(256))
    issue_date = db.Column(db.String(32))
    url        = db.Column(db.String(512))
    badge      = db.Column(db.String(512))
    order      = db.Column(db.Integer, default=0)

class Award(db.Model):
    __tablename__ = "awards"
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(256))
    issuer      = db.Column(db.String(256))
    year        = db.Column(db.String(16))
    description = db.Column(db.Text)
    order       = db.Column(db.Integer, default=0)

class Project(db.Model):
    __tablename__ = "projects"
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(256), nullable=False)
    slug        = db.Column(db.String(256), unique=True, index=True)
    description = db.Column(db.Text)
    image_url   = db.Column(db.String(512))
    gallery     = db.Column(db.JSON, default=list)
    live_url    = db.Column(db.String(512))
    github_url  = db.Column(db.String(512))
    tags        = db.Column(db.JSON, default=list)
    tech_stack  = db.Column(db.JSON, default=list)
    client_name = db.Column(db.String(256))
    featured    = db.Column(db.Boolean, default=False)
    order       = db.Column(db.Integer, default=0)
    seo_title   = db.Column(db.String(256))
    seo_desc    = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Service(db.Model):
    __tablename__ = "services"
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    icon        = db.Column(db.String(256))
    price       = db.Column(db.String(64))
    features    = db.Column(db.JSON, default=list)
    active      = db.Column(db.Boolean, default=True)
    order       = db.Column(db.Integer, default=0)

class Partner(db.Model):
    """Real partner/client-logo records for the homepage 'Trusted by' strip.
    Previously this only existed as a raw JSON blob in SiteSetting
    (site_partners_json) with NO admin UI to add/edit/remove/upload one —
    an admin literally couldn't manage this without editing a database
    value by hand. This table + a real CRUD page replaces that."""
    __tablename__ = "partners"
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(128), nullable=False)
    logo_url   = db.Column(db.String(512), nullable=False)
    website    = db.Column(db.String(512))
    active     = db.Column(db.Boolean, default=True)
    order      = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Testimonial(db.Model):
    __tablename__ = "testimonials"
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(128), nullable=False)
    role       = db.Column(db.String(128))
    company    = db.Column(db.String(128))
    avatar     = db.Column(db.String(512))
    content    = db.Column(db.Text)
    rating     = db.Column(db.Integer, default=5)
    featured   = db.Column(db.Boolean, default=True)
    approved   = db.Column(db.Boolean, default=True)
    order      = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(512), nullable=False)
    slug        = db.Column(db.String(512), unique=True, index=True)
    excerpt     = db.Column(db.Text)
    content     = db.Column(db.Text)
    cover_image = db.Column(db.String(512))
    author_id   = db.Column(db.Integer, db.ForeignKey("users.id"))
    category    = db.Column(db.String(128))
    tags        = db.Column(db.JSON, default=list)
    published   = db.Column(db.Boolean, default=False)
    featured    = db.Column(db.Boolean, default=False)
    views       = db.Column(db.Integer, default=0)
    seo_title   = db.Column(db.String(256))
    seo_desc    = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author      = db.relationship("User", back_populates="blog_posts")
    comments    = db.relationship("Comment", back_populates="post", lazy="dynamic", cascade="all, delete-orphan")

class Comment(db.Model):
    __tablename__ = "comments"
    id         = db.Column(db.Integer, primary_key=True)
    post_id    = db.Column(db.Integer, db.ForeignKey("blog_posts.id", ondelete="CASCADE"))
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"))
    content    = db.Column(db.Text)
    approved   = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post       = db.relationship("BlogPost", back_populates="comments")
    user       = db.relationship("User")

class MediaFile(db.Model):
    __tablename__ = "media_files"
    id            = db.Column(db.Integer, primary_key=True)
    filename      = db.Column(db.String(512))
    original_name = db.Column(db.String(512))
    file_type     = db.Column(db.String(32))
    mime_type     = db.Column(db.String(128))
    size          = db.Column(db.Integer)
    url           = db.Column(db.String(1024))
    folder        = db.Column(db.String(256), default="general")
    tags          = db.Column(db.JSON, default=list)
    alt_text      = db.Column(db.String(512))
    uploaded_by   = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
