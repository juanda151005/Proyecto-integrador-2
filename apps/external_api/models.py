import secrets

from django.db import models


class ExternalAPIKey(models.Model):
    """
    RF20 — API Key para autenticar sistemas externos (ej: CRM corporativo).
    La clave se genera automáticamente al crear el registro.
    """

    name = models.CharField(
        max_length=100,
        verbose_name="Nombre / integración",
        help_text="Descripción de quién usa esta key (ej: CRM Corporativo Tigo)",
    )
    key = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
        verbose_name="API Key",
    )
    is_active = models.BooleanField(default=True, verbose_name="¿Activa?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creada el")
    last_used_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Último uso"
    )

    class Meta:
        verbose_name = "API Key externa"
        verbose_name_plural = "API Keys externas"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({'activa' if self.is_active else 'inactiva'})"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = secrets.token_hex(32)
        super().save(*args, **kwargs)
