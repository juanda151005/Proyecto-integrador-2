from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ExternalAPIKey",
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
                    "name",
                    models.CharField(
                        help_text="Descripción de quién usa esta key (ej: CRM Corporativo Tigo)",
                        max_length=100,
                        verbose_name="Nombre / integración",
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        editable=False,
                        max_length=64,
                        unique=True,
                        verbose_name="API Key",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="¿Activa?"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Creada el"),
                ),
                (
                    "last_used_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Último uso"
                    ),
                ),
            ],
            options={
                "verbose_name": "API Key externa",
                "verbose_name_plural": "API Keys externas",
                "ordering": ["-created_at"],
            },
        ),
    ]
