from django.db import models


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
        verbose_name="Número de celular",
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
    is_test_eligible = models.BooleanField(
        default=False,
        verbose_name="[TEST] ¿Elegible para oferta? (RF15)",
        help_text=(
            "Campo temporal para pruebas del RF15. "
            "Marca al cliente para recibir la oferta sin depender del RF12. "
            "Reemplazar por is_eligible cuando el motor de reglas esté listo."
        ),
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
