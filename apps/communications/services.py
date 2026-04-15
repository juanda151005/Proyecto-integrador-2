"""
Servicios de comunicación externa.
Persona 5 — RF15, RF20.
"""

import logging

from django.conf import settings
from django.utils import timezone

from apps.management.runtime_settings import get_runtime_settings

from .models import NotificationLog

logger = logging.getLogger(__name__)


class TwilioService:
    """
    Integración con Twilio para envío de WhatsApp y SMS (RF15).
    Stub listo para conectar con las credenciales reales.
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
        try:
            client = self._get_client()
            msg = client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_number,
            )
            logger.info(f"SMS enviado a {to_number} — SID: {msg.sid}")
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            logger.error(f"Error al enviar SMS a {to_number}: {e}")
            return {"success": False, "error": str(e)}

    def send_whatsapp(self, to_number, message):
        """Envía un mensaje de WhatsApp al número indicado."""
        ok, err = self._twilio_daily_limit_ok()
        if not ok:
            return {"success": False, "error": err}
        try:
            client = self._get_client()
            msg = client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=f"whatsapp:{to_number}",
            )
            logger.info(f"WhatsApp enviado a {to_number} — SID: {msg.sid}")
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            logger.error(f"Error al enviar WhatsApp a {to_number}: {e}")
            return {"success": False, "error": str(e)}


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
