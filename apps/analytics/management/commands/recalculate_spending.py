"""
Management command — RF12: Recálculo masivo de gasto promedio.

Recalcula el gasto promedio mensual de todos los clientes activos.
Diseñado para ser ejecutado como tarea programada (Cron Job).

Uso manual:
    python manage.py recalculate_spending

Uso con cron (ejemplo: cada hora):
    0 * * * * cd /ruta/al/proyecto && python manage.py recalculate_spending

La periodicidad recomendada se puede consultar en GlobalSystemSettings
(campo analysis_interval_minutes), pero la ejecución real depende
de la configuración del cron del servidor.
"""

from django.core.management.base import BaseCommand

from apps.analytics.services import EligibilityEngine
from apps.core_business.models import Client


class Command(BaseCommand):
    help = (
        "RF12 — Recalcula el gasto promedio mensual de todos los "
        "clientes activos y persiste el resultado en su perfil."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--client-id",
            type=int,
            help="Recalcular solo para un cliente específico (por ID).",
        )

    def handle(self, *args, **options):
        client_id = options.get("client_id")

        if client_id:
            self._recalculate_single(client_id)
        else:
            self._recalculate_all()

    def _recalculate_single(self, client_id):
        """Recalcula el gasto promedio de un solo cliente."""
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f"Cliente con ID {client_id} no encontrado.")
            )
            return

        average, total_topups, months = EligibilityEngine.calculate_average_spending(
            client
        )
        client.average_spending = average
        client.save(update_fields=["average_spending"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Cliente {client.phone_number}: "
                f"promedio=${average:,.2f} "
                f"({total_topups} recargas en {months} meses)"
            )
        )

    def _recalculate_all(self):
        """Recalcula el gasto promedio de todos los clientes activos."""
        clients = Client.objects.filter(status=Client.StatusChoices.ACTIVE)
        total = clients.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("No hay clientes activos."))
            return

        self.stdout.write(f"Recalculando gasto promedio para {total} clientes...")

        updated = 0
        for client in clients:
            average, total_topups, months = (
                EligibilityEngine.calculate_average_spending(client)
            )
            client.average_spending = average
            client.save(update_fields=["average_spending"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Recálculo completado: {updated}/{total} clientes actualizados."
            )
        )
