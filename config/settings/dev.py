"""
Django development settings.

Uses SQLite for local development, DEBUG=True, CORS open.
"""

import dj_database_url
from decouple import config

from .base import *  # noqa: F401, F403

# =============================================================================
# DEBUG
# =============================================================================

DEBUG = True

# =============================================================================
# DATABASE — SQLite for local development
# =============================================================================

DATABASES = {
    "default": dj_database_url.config(
        default=config(
            "DATABASE_URL",
            default="sqlite:///" + str(BASE_DIR / "db.sqlite3"),
        ),
        conn_max_age=600,
    )
}

# =============================================================================
# CORS — Allow all in development
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = True
