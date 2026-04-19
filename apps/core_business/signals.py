"""
Señales de core_business — RF15: Disparador automático de oferta.

Cuando un cliente pasa a is_eligible=True, se dispara automáticamente
el envío de la oferta por WhatsApp (canal por defecto).

Conexión con RF12:
    El motor de reglas del RF12 solo necesita hacer:
        client.is_eligible = True
        client.save()
    ...y esta señal se encargará del envío sin ninguna otra intervención.

Conexión con RF14:
    El TwilioService ya crea un NotificationLog por cada envío.
    Cuando el módulo de bitácora del RF14 esté listo, reemplaza el
    print/logger.info en services.py por la función del RF14.
"""

import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(pre_save, sender="core_business.Client")
def auto_send_offer_on_eligible(sender, instance, **kwargs):
    """
    RF15 — Señal automática.

    Dispara el envío de la oferta de migración cuando un cliente
    pasa de is_eligible=False → is_eligible=True.

    El envío se hace por defecto a WhatsApp. Si necesitas SMS,
    cambia channel="SMS" abajo o agrega un campo de preferencia al modelo.
    """
    if not instance.pk:
        # Registro nuevo; is_eligible=True en creación no dispara oferta
        return

    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    eligibility_just_activated = not previous.is_eligible and instance.is_eligible

    if not eligibility_just_activated:
        return

    # ── Enviar oferta ────────────────────────────────────────────────────
    logger.info(
        "[RF15-signal] Cliente %s (%s) acaba de ser marcado elegible. "
        "Disparando envío automático de oferta...",
        instance.pk,
        instance.phone_number,
    )
    print(
        f"[RF15-signal] Disparo automático → cliente={instance.pk} "
        f"({instance.phone_number})"
    )

    # Import diferido para evitar importaciones circulares
    from apps.communications.services import TwilioService

    try:
        twilio = TwilioService()
        result = twilio.send_offer(instance, channel="WHATSAPP")

        if result["success"]:
            logger.info(
                "[RF15-signal] Oferta enviada exitosamente a %s | SID: %s | log_id: %s",
                instance.phone_number,
                result.get("sid"),
                result.get("log_id"),
            )
        else:
            logger.error(
                "[RF15-signal] Fallo al enviar oferta a %s | Error: %s",
                instance.phone_number,
                result.get("error"),
            )
    except Exception as exc:
        # La señal nunca debe bloquear el guardado del cliente
        logger.error(
            "[RF15-signal] Excepción al enviar oferta a %s: %s",
            instance.phone_number,
            exc,
        )
