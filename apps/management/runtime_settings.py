"""
Lectura en caliente de la configuración global (sin reiniciar el servidor).
"""

from django.core.cache import cache

from .models import GlobalSystemSettings

_CACHE_KEY = "global_system_settings_v1"


def get_runtime_settings():
    """
    Retorna dict con analysis_interval_minutes y twilio_daily_message_limit.
    Usa caché de Django invalidada al guardar GlobalSystemSettings.
    """
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return cached
    s = GlobalSystemSettings.get_solo()
    data = {
        "analysis_interval_minutes": s.analysis_interval_minutes,
        "twilio_daily_message_limit": s.twilio_daily_message_limit,
    }
    cache.set(_CACHE_KEY, data, timeout=None)
    return data


def invalidate_runtime_settings_cache():
    cache.delete(_CACHE_KEY)
