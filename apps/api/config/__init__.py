import os
from datetime import timedelta

class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    APP_NAME   = os.environ.get("APP_NAME", "Bazillin Studio")
    APP_URL    = os.environ.get("APP_URL", "http://localhost:5000")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///bazillin_dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 300}
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    UPLOAD_FOLDER      = os.environ.get("UPLOAD_FOLDER", "static/uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    ALLOWED_IMAGE_EXT  = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
    ALLOWED_DOC_EXT    = {"pdf", "docx", "xlsx", "pptx", "txt", "zip"}
    MAIL_SERVER   = os.environ.get("MAIL_SERVER",   "smtp.gmail.com")
    MAIL_PORT     = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS  = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "")
    STRIPE_PUBLIC_KEY   = os.environ.get("STRIPE_PUBLIC_KEY", "")
    STRIPE_SECRET_KEY   = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
    PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
    FLUTTERWAVE_SECRET_KEY = os.environ.get("FLUTTERWAVE_SECRET_KEY", "")
    ACTIVE_GATEWAY      = os.environ.get("ACTIVE_GATEWAY", "stripe")
    ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY      = os.environ.get("GEMINI_API_KEY", "")
    OPENAI_API_KEY      = os.environ.get("OPENAI_API_KEY", "")
    REMOVEBG_API_KEY    = os.environ.get("REMOVEBG_API_KEY", "")
    RATELIMIT_STORAGE_URL = os.environ.get("REDIS_URL", "memory://")
    ITEMS_PER_PAGE = 12

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = False

class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True

class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    @classmethod
    def init_app(cls, app):
        assert os.environ.get("SECRET_KEY"), "SECRET_KEY must be set in production!"
        assert os.environ.get("DATABASE_URL"), "DATABASE_URL must be set in production!"

config_map = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
