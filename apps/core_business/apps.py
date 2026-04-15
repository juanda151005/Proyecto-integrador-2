from django.apps import AppConfig


class CoreBusinessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core_business"
    verbose_name = "Clientes Prepago"

    def ready(self):
        # RF15 — Registrar señales de disparador automático de oferta
        import apps.core_business.signals  # noqa: F401
