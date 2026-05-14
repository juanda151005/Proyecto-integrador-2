import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app_management", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="GlobalSystemSettings",
            fields=[
                (
                    "id",
                    models.PositiveIntegerField(
                        default=1,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "analysis_interval_minutes",
                    models.PositiveIntegerField(
                        default=60,
                        help_text="Intervalo para re-ejecutar el motor de elegibilidad.",
                        validators=[
                            django.core.validators.MinValueValidator(5),
                            django.core.validators.MaxValueValidator(10080),
                        ],
                        verbose_name="Periodicidad de análisis (minutos)",
                    ),
                ),
                (
                    "twilio_daily_message_limit",
                    models.PositiveIntegerField(
                        default=500,
                        help_text="Máximo de notificaciones SMS/WhatsApp enviadas por día.",
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(1000000),
                        ],
                        verbose_name="Límite diario de mensajes Twilio",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Última actualización"
                    ),
                ),
            ],
            options={
                "verbose_name": "Configuración global del sistema",
                "verbose_name_plural": "Configuración global del sistema",
            },
        ),
    ]
