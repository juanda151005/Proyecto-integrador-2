"""
Management command: send_offers
RF15 — Dispara el envío masivo de ofertas a clientes elegibles.

Uso:
    # Enviar a todos los marcados con is_eligible (motor RF13 real)
    python manage.py send_offers

    # Elegir canal: WHATSAPP (default) o SMS
    python manage.py send_offers --channel SMS

    # Dry-run: muestra quién recibiría la oferta sin enviar nada
    python manage.py send_offers --dry-run
"""

from django.core.management.base import BaseCommand, CommandError

from apps.communications.services import TwilioService
from apps.core_business.models import Client


class Command(BaseCommand):
    help = (
        "RF15 — Envía ofertas de migración a postpago a clientes elegibles "
        "vía WhatsApp o SMS usando Twilio. Utiliza el motor RF13 (is_eligible)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--channel",
            type=str,
            default="WHATSAPP",
            choices=["WHATSAPP", "SMS"],
            help="Canal de envío: WHATSAPP (default) o SMS.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Muestra los clientes que recibirían la oferta sin enviar nada.",
        )

    def handle(self, *args, **options):
        channel = options["channel"]
        dry_run = options["dry_run"]

        # ── Seleccionar elegibles por motor RF13 ─────────────────────────────
        eligible_clients = Client.objects.filter(
            is_eligible=True,
            status=Client.StatusChoices.ACTIVE,
        )

        total = eligible_clients.count()

        self.stdout.write(
            self.style.HTTP_INFO(
                f"\n{'='*60}\n"
                f"  RF15 — Envío de Ofertas\n"
                f"  Canal:    {channel}\n"
                f"  Criterio: is_eligible (motor RF13)\n"
                f"  Clientes: {total} encontrado(s)\n"
                f"  Dry-run:  {'SÍ — no se enviará nada' if dry_run else 'NO — envío real'}\n"
                f"{'='*60}\n"
            )
        )

        if total == 0:
            self.stdout.write(
                self.style.WARNING(
                    "No hay clientes elegibles activos. "
                    "El motor de elegibilidad (RF13) debe evaluar clientes primero."
                )
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS("\n[DRY-RUN] Clientes que recibirían la oferta:")
            )
            for client in eligible_clients:
                self.stdout.write(
                    f"  • {client.full_name} | {client.phone_number} | "
                    f"Plan: {client.get_current_plan_display()} | "
                    f"Gasto prom: ${client.average_spending:,.0f}"
                )
            self.stdout.write(
                self.style.SUCCESS(f"\nTotal: {total} cliente(s). Nada fue enviado.\n")
            )
            return

        # ── Envío real ─────────────────────────────────────────────────────
        twilio = TwilioService()
        results = {"sent": 0, "failed": 0}

        for client in eligible_clients:
            self.stdout.write(
                f"  Enviando oferta a {client.full_name} ({client.phone_number})..."
            )
            try:
                result = twilio.send_offer(client, channel=channel)
                if result["success"]:
                    results["sent"] += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"    ✅ Enviado | SID: {result.get('sid')} | log_id: {result.get('log_id')}"
                        )
                    )
                else:
                    results["failed"] += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"    ❌ Fallido | Error: {result.get('error')}"
                        )
                    )
            except Exception as exc:
                results["failed"] += 1
                self.stdout.write(
                    self.style.ERROR(f"    ❌ Excepción inesperada: {exc}")
                )

        # ── Resumen final ─────────────────────────────────────────────────
        self.stdout.write(
            self.style.HTTP_INFO(
                f"\n{'='*60}\n"
                f"  Resumen:\n"
                f"  ✅ Enviados exitosamente: {results['sent']}\n"
                f"  ❌ Fallidos:              {results['failed']}\n"
                f"{'='*60}\n"
            )
        )

        if results["failed"] > 0:
            raise CommandError(
                f"{results['failed']} oferta(s) no pudieron ser enviadas. "
                "Revisa los logs de NotificationLog para más detalles."
            )
