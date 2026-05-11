from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("communications", "0001_initial"),
        ("core_business", "0004_plan_client_plan_fk"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
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
                    "status",
                    models.CharField(
                        choices=[("OPEN", "Abierta"), ("CLOSED", "Cerrada")],
                        default="OPEN",
                        max_length=10,
                        verbose_name="Estado del chat",
                    ),
                ),
                (
                    "client_response",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("YES", "Sí me interesa"),
                            ("NO", "No, gracias"),
                        ],
                        max_length=5,
                        verbose_name="Respuesta del cliente",
                    ),
                ),
                (
                    "had_response",
                    models.BooleanField(
                        default=False, verbose_name="¿El cliente respondió?"
                    ),
                ),
                (
                    "notes",
                    models.TextField(blank=True, verbose_name="Notas del asesor"),
                ),
                (
                    "opened_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Abierta el"
                    ),
                ),
                (
                    "closed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Cerrada el"
                    ),
                ),
                (
                    "advisor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_conversations",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Asesor asignado",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversations",
                        to="core_business.client",
                        verbose_name="Cliente",
                    ),
                ),
                (
                    "notification",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversation",
                        to="communications.notificationlog",
                        verbose_name="Notificación origen",
                    ),
                ),
            ],
            options={
                "verbose_name": "Conversación",
                "verbose_name_plural": "Conversaciones",
                "ordering": ["-opened_at"],
            },
        ),
    ]
