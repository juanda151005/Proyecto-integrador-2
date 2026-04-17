"""
Django production settings.

Uses PostgreSQL, DEBUG=False, strict security.
"""

import dj_database_url
from decouple import config

from .base import *  # noqa: F401, F403

# =============================================================================
# DEBUG
# =============================================================================

DEBUG = False

# =============================================================================
# DATABASE — PostgreSQL for production
# =============================================================================

DATABASES = {
    "default": dj_database_url.config(
        default=config(
            "DATABASE_URL",
            default="postgres://postgres:postgres@db:5432/smart_migration_db",
        ),
        conn_max_age=600,
    )
}

# =============================================================================
# CORS — Restrict in production
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:8001,http://127.0.0.1:8001",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# =============================================================================
# SECURITY
# =============================================================================

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
