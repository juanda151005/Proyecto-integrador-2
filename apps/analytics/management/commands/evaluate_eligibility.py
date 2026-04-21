"""
Management command — RF13: Evaluación masiva de elegibilidad por antigüedad.

Evalúa todos los clientes activos y marca como elegibles a los que llevan
>= 60 días con la línea (activation_date). Diseñado para ejecutarse como
tarea programada (Cron Job) una vez al día.

Uso manual:
    python manage.py evaluate_eligibility

Solo un cliente:
    python manage.py evaluate_eligibility --client-id 5

Ver resultados sin persistir:
    python manage.py evaluate_eligibility --dry-run

Uso con cron (ejemplo: todos los dias a las 2 AM):
    0 2 * * * cd /ruta/al/proyecto && python manage.py evaluate_eligibility
"""

from django.core.management.base import BaseCommand

from apps.analytics.services import EligibilityEngine
from apps.core_business.models import Client


class Command(BaseCommand):
    help = (
        "RF13 — Evalua la elegibilidad de clientes activos basandose en "
        "su antiguedad (activation_date >= 60 dias). Disenado para cron diario."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--client-id",
            type=int,
            help="Evaluar solo un cliente especifico (por ID).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Muestra los resultados sin persistir cambios en la BD.",
        )

    def handle(self, *args, **options):
        client_id = options.get("client_id")
        dry_run = options["dry_run"]

        if client_id:
            self._evaluate_single(client_id, dry_run)
        else:
            self._evaluate_all(dry_run)

    def _evaluate_single(self, client_id, dry_run):
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Cliente con ID {client_id} no encontrado."))
            return

        resultado = self._evaluar(client, dry_run)
        self._imprimir_resultado(resultado)

    def _evaluate_all(self, dry_run):
        clients = Client.objects.filter(status=Client.StatusChoices.ACTIVE)
        total = clients.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("No hay clientes activos."))
            return

        modo = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            self.style.HTTP_INFO(
                f"\n{'='*60}\n"
                f"  RF13 — Evaluacion de elegibilidad\n"
                f"  {modo}Clientes activos: {total}\n"
                f"  Criterio: antiguedad >= 60 dias desde activation_date\n"
                f"{'='*60}\n"
            )
        )

        nuevos_elegibles = 0
        ya_elegibles = 0
        no_elegibles = 0

        for client in clients:
            era_elegible = client.is_eligible
            resultado = self._evaluar(client, dry_run)
            self._imprimir_resultado(resultado)

            if resultado["is_eligible"] and not era_elegible:
                nuevos_elegibles += 1
            elif resultado["is_eligible"]:
                ya_elegibles += 1
            else:
                no_elegibles += 1

        self.stdout.write(
            self.style.HTTP_INFO(
                f"\n{'='*60}\n"
                f"  Resumen:\n"
                f"  Recien marcados elegibles: {nuevos_elegibles}\n"
                f"  Ya eran elegibles:         {ya_elegibles}\n"
                f"  No elegibles:              {no_elegibles}\n"
                f"{'='*60}\n"
            )
        )

    def _evaluar(self, client, dry_run):
        if dry_run:
            from datetime import date
            min_days = EligibilityEngine.get_min_seniority_days()
            seniority = (date.today() - client.activation_date).days
            is_eligible = seniority >= min_days
            return {
                "client_id": client.pk,
                "phone_number": client.phone_number,
                "full_name": client.full_name,
                "is_eligible": is_eligible,
                "reason": (
                    f"Antiguedad de {seniority} dias "
                    + ("supera" if is_eligible else "no alcanza")
                    + f" el minimo de {min_days} dias."
                ),
            }
        return EligibilityEngine.evaluate_client(client)

    def _imprimir_resultado(self, r):
        icono = "OK" if r["is_eligible"] else "--"
        estilo = self.style.SUCCESS if r["is_eligible"] else self.style.WARNING
        self.stdout.write(
            estilo(
                f"  [{icono}] {r['full_name']} ({r['phone_number']}) | {r['reason']}"
            )
        )
