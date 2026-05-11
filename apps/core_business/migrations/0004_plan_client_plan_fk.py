import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core_business", "0003_remove_is_test_eligible_rf15"),
    ]

    operations = [
        migrations.CreateModel(
            name="Plan",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        help_text="Identificador único del plan (ej: PLAN_BASICO)",
                        max_length=50,
                        unique=True,
                        verbose_name="Código",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=100, verbose_name="Nombre del plan"),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="Descripción"),
                ),
                (
                    "target_plan_name",
                    models.CharField(
                        blank=True,
                        help_text="Nombre del plan al que se invita a migrar (ej: Plan Plus de Tigo)",
                        max_length=200,
                        verbose_name="Plan postpago objetivo",
                    ),
                ),
                (
                    "target_plan_price",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=12,
                        verbose_name="Precio del plan objetivo (COP)",
                    ),
                ),
                (
                    "min_seniority_days",
                    models.PositiveIntegerField(
                        default=60,
                        help_text="Al llegar al día siguiente se habilita el envío de notificación.",
                        verbose_name="Días mínimos de antigüedad",
                    ),
                ),
                (
                    "message_template_whatsapp",
                    models.TextField(
                        blank=True,
                        help_text="Variables disponibles: {name}, {plan}, {price}",
                        verbose_name="Plantilla WhatsApp",
                    ),
                ),
                (
                    "message_template_sms",
                    models.TextField(
                        blank=True,
                        help_text="Variables disponibles: {name}, {plan}, {price}",
                        verbose_name="Plantilla SMS",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="¿Activo?"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Plan",
                "verbose_name_plural": "Planes",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="client",
            name="plan",
            field=models.ForeignKey(
                blank=True,
                help_text="Plan postpago al que se invitará a migrar al cliente",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="clients",
                to="core_business.plan",
                verbose_name="Plan de migración objetivo",
            ),
        ),
    ]
