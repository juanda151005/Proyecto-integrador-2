"""
Lectura en caliente de configuración global sin reiniciar el servidor.
"""

from django.core.cache import cache

_CACHE_KEY = "global_system_settings_v1"


def get_runtime_settings():
    from .models import GlobalSystemSettings

    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    settings_obj = GlobalSystemSettings.get_solo()
    data = {
        "analysis_interval_minutes": settings_obj.analysis_interval_minutes,
        "twilio_daily_message_limit": settings_obj.twilio_daily_message_limit,
    }
    cache.set(_CACHE_KEY, data, timeout=None)
    return data


def invalidate_runtime_settings_cache():
    cache.delete(_CACHE_KEY)
