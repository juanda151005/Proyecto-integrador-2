from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
    verbose_name = "Analítica y Recargas"

    def ready(self):
        # RF12 — Registrar señal de recálculo automático de gasto promedio
        import apps.analytics.signals  # noqa: F401
