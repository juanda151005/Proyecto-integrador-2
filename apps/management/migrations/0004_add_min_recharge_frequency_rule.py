"""
Data migration — RF13: Crear la BusinessRule MIN_RECHARGE_FREQUENCY.

Agrega el parámetro de frecuencia mínima de recargas para el motor
de elegibilidad. Solo el ADMIN puede modificar este valor (RF16).
"""

from django.db import migrations


def create_min_recharge_frequency_rule(apps, schema_editor):
    BusinessRule = apps.get_model("app_management", "BusinessRule")
    BusinessRule.objects.get_or_create(
        key="MIN_RECHARGE_FREQUENCY",
        defaults={
            "value": "3",
            "description": (
                "Cantidad mínima de recargas que un cliente debe tener "
                "registradas para ser considerado elegible para migración "
                "a postpago. Solo modificable por el Administrador."
            ),
            "is_active": True,
        },
    )


def remove_min_recharge_frequency_rule(apps, schema_editor):
    BusinessRule = apps.get_model("app_management", "BusinessRule")
    BusinessRule.objects.filter(key="MIN_RECHARGE_FREQUENCY").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app_management", "0003_globalsystemsettings"),
    ]

    operations = [
        migrations.RunPython(
            create_min_recharge_frequency_rule,
            remove_min_recharge_frequency_rule,
        ),
    ]
