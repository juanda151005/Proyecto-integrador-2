"""
Servicios de comunicación externa.
Persona 5 — RF15, RF20.
"""

import logging

from django.conf import settings
from django.utils import timezone

from apps.management.audit import log_critical_action
from apps.management.models import AuditLog
from apps.management.runtime_settings import get_runtime_settings

from .models import NotificationLog

logger = logging.getLogger(__name__)

# ── Plantilla de mensaje de oferta (RF15) ──────────────────────────────────
OFFER_TEMPLATE_WHATSAPP = (
    "🎉 *¡Hola, {name}!*\n\n"
    "Tenemos una oferta especial para ti. Tu historial como cliente {plan} "
    "te hace elegible para migrar a un *plan postpago* con beneficios exclusivos:\n\n"
    "✅ Minutos ilimitados\n"
    "✅ Datos 5G sin límite\n"
    "✅ Sin cargos adicionales\n\n"
    "📞 Llama al *#611* o visita nuestra página para activarlo hoy.\n"
    "_SmartMigration — Tu operadora inteligente_"
)

OFFER_TEMPLATE_SMS = (
    "Hola {name}, eres elegible para migrar a postpago. "
    "Llama al #611 o visita smartmigration.co para conocer tu oferta personalizada. "
    "SmartMigration."
)


class TwilioService:
    """
    Integración con Twilio para envío de WhatsApp y SMS (RF15).
    Cada envío registra automáticamente una entrada en AuditLog (RF14).
    """

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.phone_number = settings.TWILIO_PHONE_NUMBER
        self.whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER
        self._client = None

    def _twilio_daily_limit_ok(self):
        limit = get_runtime_settings()["twilio_daily_message_limit"]
        today = timezone.localdate()
        sent_today = NotificationLog.objects.filter(sent_at__date=today).count()
        if sent_today >= limit:
            return (
                False,
                f"Límite diario de Twilio alcanzado ({limit}).",
            )
        return True, None

    def _get_client(self):
        """Inicializa el cliente de Twilio. Lazy loading."""
        if self._client is None:
            try:
                from twilio.rest import Client

                self._client = Client(self.account_sid, self.auth_token)
            except Exception as e:
                logger.error(f"Error al inicializar Twilio: {e}")
                raise
        return self._client

    def send_sms(self, to_number, message):
        """Envía un SMS al número indicado."""
        ok, err = self._twilio_daily_limit_ok()
        if not ok:
            return {"success": False, "error": err}

        # Asegurar formato E.164 (Añadir +57 si es número colombiano de 10 dígitos)
        clean_number = str(to_number).strip()
        if len(clean_number) == 10 and not clean_number.startswith("+"):
            clean_number = f"+57{clean_number}"
        try:
            client = self._get_client()
            msg = client.messages.create(
                body=message,
                from_=self.phone_number,
                to=clean_number,
            )
            logger.info(f"SMS enviado a {clean_number} — SID: {msg.sid}")
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            logger.error(f"Error al enviar SMS a {clean_number}: {e}")
            return {"success": False, "error": str(e)}

    def send_whatsapp(self, to_number, message):
        """Envía un mensaje de WhatsApp al número indicado."""
        ok, err = self._twilio_daily_limit_ok()
        if not ok:
            return {"success": False, "error": err}

        # Asegurar formato E.164 (Añadir +57 si es número colombiano de 10 dígitos)
        clean_number = str(to_number).strip()
        if len(clean_number) == 10 and not clean_number.startswith("+"):
            clean_number = f"+57{clean_number}"
        try:
            client = self._get_client()
            msg = client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=f"whatsapp:{clean_number}",
            )
            logger.info(f"WhatsApp enviado a {clean_number} — SID: {msg.sid}")
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            logger.error(f"Error al enviar WhatsApp a {clean_number}: {e}")
            return {"success": False, "error": str(e)}

    # ── RF15: Disparadores de oferta ──────────────────────────────────────────

    def send_whatsapp_offer(self, client):
        """
        RF15 — Envía una oferta personalizada por WhatsApp a un cliente.
        RF14 — Registra la operación en la bitácora de auditoría.

        Parámetros:
            client: instancia de apps.core_business.models.Client

        Retorna:
            dict con keys 'success' (bool), 'sid' (str) o 'error' (str),
            y 'log_id' con el ID del NotificationLog creado.
        """
        plan_label = client.get_current_plan_display()
        message = OFFER_TEMPLATE_WHATSAPP.format(
            name=client.full_name.split()[0],  # primer nombre
            plan=plan_label,
        )

        result = self.send_whatsapp(client.phone_number, message)

        # Registrar en NotificationLog
        log = NotificationLog.objects.create(
            client=client,
            message=message,
            channel=NotificationLog.ChannelChoices.WHATSAPP,
            status=(
                NotificationLog.StatusChoices.SENT
                if result["success"]
                else NotificationLog.StatusChoices.FAILED
            ),
            external_id=result.get("sid", ""),
        )

        # RF14 — Registrar en bitácora de auditoría
        status_label = (
            "Enviado exitosamente" if result["success"] else f"Fallido: {result.get('error', '')}"
        )
        log_critical_action(
            user=None,
            action=AuditLog.ActionChoices.NOTIFICATION_SENT,
            model_name="NotificationLog",
            object_id=str(log.pk),
            before=None,
            after={
                "client_id": client.pk,
                "phone_number": client.phone_number,
                "channel": NotificationLog.ChannelChoices.WHATSAPP,
                "status": status_label,
                "twilio_sid": result.get("sid", ""),
                "notification_log_id": log.pk,
            },
        )

        logger.info(
            "[RF15 | RF14] Oferta WhatsApp → cliente=%s | numero=%s | "
            "estado=%s | twilio_sid=%s | log_id=%s",
            client.pk,
            client.phone_number,
            status_label,
            result.get("sid", "N/A"),
            log.pk,
        )

        return {**result, "log_id": log.pk}

    def send_sms_offer(self, client):
        """
        RF15 — Envía una oferta personalizada por SMS a un cliente.
        RF14 — Registra la operación en la bitácora de auditoría.

        Parámetros:
            client: instancia de apps.core_business.models.Client

        Retorna:
            dict con keys 'success' (bool), 'sid' (str) o 'error' (str),
            y 'log_id' con el ID del NotificationLog creado.
        """
        message = OFFER_TEMPLATE_SMS.format(
            name=client.full_name.split()[0],
        )

        result = self.send_sms(client.phone_number, message)

        # Registrar en NotificationLog
        log = NotificationLog.objects.create(
            client=client,
            message=message,
            channel=NotificationLog.ChannelChoices.SMS,
            status=(
                NotificationLog.StatusChoices.SENT
                if result["success"]
                else NotificationLog.StatusChoices.FAILED
            ),
            external_id=result.get("sid", ""),
        )

        # RF14 — Registrar en bitácora de auditoría
        status_label = (
            "Enviado exitosamente" if result["success"] else f"Fallido: {result.get('error', '')}"
        )
        log_critical_action(
            user=None,
            action=AuditLog.ActionChoices.NOTIFICATION_SENT,
            model_name="NotificationLog",
            object_id=str(log.pk),
            before=None,
            after={
                "client_id": client.pk,
                "phone_number": client.phone_number,
                "channel": NotificationLog.ChannelChoices.SMS,
                "status": status_label,
                "twilio_sid": result.get("sid", ""),
                "notification_log_id": log.pk,
            },
        )

        logger.info(
            "[RF15 | RF14] Oferta SMS → cliente=%s | numero=%s | "
            "estado=%s | twilio_sid=%s | log_id=%s",
            client.pk,
            client.phone_number,
            status_label,
            result.get("sid", "N/A"),
            log.pk,
        )

        return {**result, "log_id": log.pk}

    def send_offer(self, client, channel="WHATSAPP"):
        """
        RF15 — Dispatcher genérico. Enruta la oferta al canal correcto.

        Parámetros:
            client:  instancia Client
            channel: 'WHATSAPP' (default) o 'SMS'

        Retorna el dict de resultado del canal utilizado.
        """
        if channel == NotificationLog.ChannelChoices.SMS:
            return self.send_sms_offer(client)
        return self.send_whatsapp_offer(client)


class ExternalAPIService:
    """
    Consulta a API REST externa para CRM (RF20).
    Stub listo para conectar con el endpoint real.
    """

    def __init__(self):
        self.base_url = settings.EXTERNAL_API_BASE_URL
        self.api_key = settings.EXTERNAL_API_KEY

    def get_client_data(self, phone_number):
        """Consulta datos de un cliente en el sistema externo."""
        # TODO: Implementar con requests cuando esté disponible el endpoint
        logger.info(f"Consultando API externa para {phone_number}")
        return {
            "success": True,
            "data": {
                "phone_number": phone_number,
                "external_status": "active",
                "message": "Stub — Implementar conexión real con la API externa.",
            },
        }
