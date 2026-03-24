from django.core.validators import RegexValidator
from django.db import models

# ── Validador reutilizable para número celular colombiano ──
phone_regex = RegexValidator(
    regex=r"^3\d{9}$",
    message="El número debe tener 10 dígitos y empezar con 3. Ej: 3001234567",
)


class Client(models.Model):
    """
    Cliente prepago.
    RF06 — Registro de clientes prepago.
    RF08 — Actualización de registros existentes.
    """

    class PlanChoices(models.TextChoices):
        PREPAGO_BASIC = "PREPAGO_BASIC", "Prepago Básico"
        PREPAGO_PLUS = "PREPAGO_PLUS", "Prepago Plus"
        PREPAGO_PREMIUM = "PREPAGO_PREMIUM", "Prepago Premium"

    class StatusChoices(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        INACTIVE = "INACTIVE", "Inactivo"
        MIGRATED = "MIGRATED", "Migrado a Postpago"

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[phone_regex],
        verbose_name="Número de celular",
        help_text="Número celular colombiano de 10 dígitos (ej: 3001234567)",
    )
    full_name = models.CharField(max_length=200, verbose_name="Nombre completo")
    document_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Número de documento",
    )
    email = models.EmailField(blank=True, verbose_name="Correo electrónico")
    activation_date = models.DateField(verbose_name="Fecha de activación")
    current_plan = models.CharField(
        max_length=20,
        choices=PlanChoices.choices,
        default=PlanChoices.PREPAGO_BASIC,
        verbose_name="Plan actual",
    )
    is_eligible = models.BooleanField(
        default=False,
        verbose_name="¿Elegible para postpago?",
    )
    average_spending = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Gasto promedio mensual",
    )
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
        verbose_name="Estado",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de registro"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Última actualización"
    )

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} — {self.phone_number}"
