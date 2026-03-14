from django.apps import AppConfig


class ManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.management'
    verbose_name = 'Gestión y Configuración'
    label = 'app_management'
