from django.core.validators import RegexValidator
from django.db import models

# ── Validador reutilizable para número celular colombiano ──
phone_regex = RegexValidator(
    regex=r"^3\d{9}$",
    message="El número debe tener 10 dígitos y empezar con 3. Ej: 3001234567",
)


class Plan(models.Model):
    """
    Plan de migración parametrizable.
    Permite configurar: días de elegibilidad, plantillas de mensaje y precio destino.
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Código",
        help_text="Identificador único del plan (ej: PLAN_BASICO)",
    )
    name = models.CharField(max_length=100, verbose_name="Nombre del plan")
    description = models.TextField(blank=True, verbose_name="Descripción")
    target_plan_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Plan postpago objetivo",
        help_text="Nombre del plan al que se invita a migrar (ej: Plan Plus de Tigo)",
    )
    target_plan_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Precio del plan objetivo (COP)",
    )
    min_seniority_days = models.PositiveIntegerField(
        default=60,
        verbose_name="Días mínimos de antigüedad",
        help_text="Al llegar al día siguiente se habilita el envío de notificación.",
    )
    message_template_whatsapp = models.TextField(
        blank=True,
        verbose_name="Plantilla WhatsApp",
        help_text="Variables disponibles: {name}, {plan}, {price}",
    )
    message_template_sms = models.TextField(
        blank=True,
        verbose_name="Plantilla SMS",
        help_text="Variables disponibles: {name}, {plan}, {price}",
    )
    is_active = models.BooleanField(default=True, verbose_name="¿Activo?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plan"
        verbose_name_plural = "Planes"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


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
    plan = models.ForeignKey(
        Plan,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clients",
        verbose_name="Plan de migración objetivo",
        help_text="Plan postpago al que se invitará a migrar al cliente",
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
