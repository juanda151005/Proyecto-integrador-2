from django.db import models


class BusinessRule(models.Model):
    """
    RF16 — Configuración de parámetros generales.
    Almacena reglas de negocio como clave-valor (ej: umbral de gasto mínimo).
    """

    key = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Clave",
        help_text="Identificador único de la regla (ej: MIN_AVERAGE_SPENDING)",
    )
    value = models.CharField(
        max_length=500,
        verbose_name="Valor",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="¿Activa?",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Regla de negocio"
        verbose_name_plural = "Reglas de negocio"
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} = {self.value}"


class AuditLog(models.Model):
    """
    RF14 — Bitácora de operaciones críticas.
    Registra acciones importantes del sistema.
    """

    class ActionChoices(models.TextChoices):
        CREATE = "CREATE", "Creación"
        UPDATE = "UPDATE", "Actualización"
        DELETE = "DELETE", "Eliminación"
        LOGIN = "LOGIN", "Inicio de sesión"
        EXPORT = "EXPORT", "Exportación"
        ELIGIBILITY_CHECK = "ELIGIBILITY_CHECK", "Evaluación de elegibilidad"
        NOTIFICATION_SENT = "NOTIFICATION_SENT", "Notificación enviada"

    user = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Usuario",
    )
    action = models.CharField(
        max_length=30,
        choices=ActionChoices.choices,
        verbose_name="Acción",
    )
    model_name = models.CharField(
        max_length=100,
        verbose_name="Modelo/Entidad",
    )
    object_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="ID del objeto",
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Detalles/Cambios",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dirección IP",
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha/Hora")

    class Meta:
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Registros de auditoría"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.get_action_display()}] {self.model_name} #{self.object_id} — {self.timestamp:%Y-%m-%d %H:%M}"
