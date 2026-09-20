import os
from datetime import timedelta
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def get_database_uri() -> str:
    """Resolve database URI with strict priority: DATABASE_URL -> SQLALCHEMY_DATABASE_URI -> SQLite fallback."""
    uri = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or "sqlite:///database.db"
    # Normalize legacy postgres:// to postgresql:// for SQLAlchemy 1.4+ (Heroku/Render/AWS RDS)
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    return uri


def validate_database_driver(database_uri: str) -> bool:
    """Verify that a supported SQLAlchemy driver is installed when connecting to PostgreSQL."""
    if database_uri.startswith("postgresql://") or database_uri.startswith("postgres://"):
        supported_drivers = ["psycopg2", "psycopg", "pg8000", "asyncpg"]
        has_driver = False
        for driver in supported_drivers:
            try:
                __import__(driver)
                has_driver = True
                break
            except ImportError:
                continue
        if not has_driver:
            raise RuntimeError(
                "PostgreSQL driver is not installed. "
                "Install a documented PostgreSQL dependency (e.g. 'psycopg2-binary' or 'pg8000') "
                "to use PostgreSQL in production."
            )
        return True
    return True


def get_engine_options(database_uri: str) -> dict:
    """Return dialect-aware engine connection pooling options without exposing credentials."""
    if database_uri.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False},
        }
    return {
        "pool_pre_ping": True,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
    }


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key")

    # Database Configuration (SQLite dev, PostgreSQL prod)
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = get_engine_options(SQLALCHEMY_DATABASE_URI)

    # Session & Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "yes")
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "yes")
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max payload limit

    # External APIs
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

    # Mail configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = os.getenv("MAIL_PORT", "587")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    # LLM Model Fallback & Reliability Configuration
    LLM_PRIMARY_MODEL = os.getenv("LLM_PRIMARY_MODEL", "openai/gpt-4o-mini")
    LLM_FALLBACK_MODELS = os.getenv("LLM_FALLBACK_MODELS", "anthropic/claude-3.5-haiku,google/gemini-2.5-flash,openai/gpt-4o")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "12"))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))
