import logging

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core_business.models import Client
from apps.users.permissions import IsAdmin, IsAdminOrAnalyst

from .models import Conversation, NotificationLog
from .serializers import (
    BulkNotificationSerializer,
    ConversationSerializer,
    ConversationUpdateSerializer,
    NotificationLogSerializer,
    SendNotificationSerializer,
    SendOfferSerializer,
)
from .services import ExternalAPIService, TwilioService

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Notification logs
# ─────────────────────────────────────────────────────────────────────────────


class NotificationLogListView(generics.ListAPIView):
    """GET — Lista logs de notificaciones enviadas."""

    queryset = NotificationLog.objects.select_related("client").all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["channel", "status", "client"]


# ─────────────────────────────────────────────────────────────────────────────
# Send notifications
# ─────────────────────────────────────────────────────────────────────────────


class SendNotificationView(APIView):
    """
    POST — Envía una notificación a un cliente específico (RF15).
    Body: { "client_id": <int>, "channel": "WHATSAPP"|"SMS", "message": "..." }
    """

    permission_classes = [IsAdminOrAnalyst]

    def post(self, request):
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client = Client.objects.get(pk=serializer.validated_data["client_id"])
        except Client.DoesNotExist:
            return Response(
                {"detail": "Cliente no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        channel = serializer.validated_data["channel"]
        message = serializer.validated_data["message"]

        twilio = TwilioService()
        if channel == "WHATSAPP":
            result = twilio.send_whatsapp(client.phone_number, message)
        else:
            result = twilio.send_sms(client.phone_number, message)

        log = NotificationLog.objects.create(
            client=client,
            message=message,
            channel=channel,
            status="SENT" if result["success"] else "FAILED",
            external_id=result.get("sid", ""),
        )

        return Response(
            NotificationLogSerializer(log).data,
            status=status.HTTP_201_CREATED,
        )


class SendOfferView(APIView):
    """
    POST — RF15: Envía la oferta personalizada de migración a un cliente.
    Usa la plantilla del Plan del cliente (o la predefinida si no tiene Plan).
    Body: { "client_id": <int>, "channel": "WHATSAPP"|"SMS" }
    """

    permission_classes = [IsAdminOrAnalyst]

    def post(self, request):
        serializer = SendOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client = Client.objects.select_related("plan").get(
                pk=serializer.validated_data["client_id"]
            )
        except Client.DoesNotExist:
            return Response(
                {"detail": "Cliente no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        channel = serializer.validated_data["channel"]
        twilio = TwilioService()
        result = twilio.send_offer(client, channel=channel)

        if not result["success"]:
            return Response(
                {"detail": f"Error al enviar oferta: {result.get('error')}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        log = NotificationLog.objects.get(pk=result["log_id"])

        Conversation.objects.get_or_create(
            notification=log,
            defaults={"client": client, "status": Conversation.StatusChoices.OPEN},
        )

        return Response(
            {
                "detail": "Oferta enviada exitosamente.",
                "notification": NotificationLogSerializer(log).data,
            },
            status=status.HTTP_201_CREATED,
        )


class BulkNotifyEligibleView(APIView):
    """
    POST — Envío masivo de ofertas a todos los clientes elegibles (RF15).
    Body: { "channel": "WHATSAPP"|"SMS" }
    """

    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = BulkNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        channel = serializer.validated_data["channel"]

        eligible_clients = Client.objects.select_related("plan").filter(
            is_eligible=True,
            status=Client.StatusChoices.ACTIVE,
        )

        if not eligible_clients.exists():
            return Response(
                {"detail": "No hay clientes elegibles activos."},
                status=status.HTTP_404_NOT_FOUND,
            )

        results = {"sent": 0, "failed": 0}
        twilio = TwilioService()
        for client in eligible_clients:
            result = twilio.send_offer(client, channel=channel)
            if result["success"]:
                results["sent"] += 1
                log = NotificationLog.objects.filter(pk=result.get("log_id")).first()
                if log:
                    Conversation.objects.get_or_create(
                        notification=log,
                        defaults={"client": client, "status": Conversation.StatusChoices.OPEN},
                    )
            else:
                results["failed"] += 1

        return Response(
            {
                "detail": (
                    f"Envío masivo completado. "
                    f"Enviados: {results['sent']}, Fallidos: {results['failed']}"
                ),
                **results,
            }
        )


# ─────────────────────────────────────────────────────────────────────────────
# Twilio Webhook — captura respuestas del cliente (Sí / No)
# ─────────────────────────────────────────────────────────────────────────────

_YES_KEYWORDS = frozenset({"si", "sí", "yes", "me interesa", "si me interesa", "acepto", "quiero"})
_NO_KEYWORDS = frozenset({"no", "no gracias", "no, gracias", "rechazar", "cancelar"})


@method_decorator(csrf_exempt, name="dispatch")
class TwilioWebhookView(APIView):
    """
    POST — Webhook que recibe respuestas de clientes vía Twilio (WhatsApp/SMS).

    Twilio envía:
        From  — número del cliente (ej: whatsapp:+573001234567)
        Body  — texto del mensaje

    El sistema:
        1. Identifica al cliente por número de celular.
        2. Localiza la última notificación SENT para ese cliente.
        3. "SI" → ACCEPTED + Conversation(response=YES, status=OPEN para asesor).
        4. "NO" → REJECTED + Conversation(response=NO, status=CLOSED).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        raw_from = request.data.get("From", "")
        body = request.data.get("Body", "").strip().lower()

        # Normalizar número: quitar prefijos whatsapp: y código de país
        phone = raw_from.replace("whatsapp:", "").strip()
        if phone.startswith("+57"):
            phone = phone[3:]
        elif phone.startswith("+"):
            phone = phone[1:]

        logger.info("[Webhook Twilio] De: %s | Mensaje: '%s'", phone, body)

        try:
            client = Client.objects.select_related("plan").get(phone_number=phone)
        except Client.DoesNotExist:
            logger.warning("[Webhook Twilio] Cliente no encontrado: %s", phone)
            return Response({"detail": "ok"}, status=status.HTTP_200_OK)

        notification = (
            NotificationLog.objects.filter(
                client=client, status=NotificationLog.StatusChoices.SENT
            )
            .order_by("-sent_at")
            .first()
        )

        if notification is None:
            logger.info("[Webhook Twilio] Sin notificación pendiente para %s", phone)
            return Response({"detail": "ok"}, status=status.HTTP_200_OK)

        if any(kw in body for kw in _YES_KEYWORDS):
            response_choice = Conversation.ResponseChoices.YES
            notif_status = NotificationLog.StatusChoices.ACCEPTED
            conv_status = Conversation.StatusChoices.OPEN
        elif any(kw in body for kw in _NO_KEYWORDS):
            response_choice = Conversation.ResponseChoices.NO
            notif_status = NotificationLog.StatusChoices.REJECTED
            conv_status = Conversation.StatusChoices.CLOSED
        else:
            logger.info("[Webhook Twilio] Respuesta no reconocida de %s: '%s'", phone, body)
            return Response({"detail": "ok"}, status=status.HTTP_200_OK)

        notification.status = notif_status
        notification.save(update_fields=["status", "updated_at"])

        conversation, _ = Conversation.objects.get_or_create(
            notification=notification,
            defaults={"client": client},
        )
        conversation.client_response = response_choice
        conversation.had_response = True
        conversation.status = conv_status
        if conv_status == Conversation.StatusChoices.CLOSED:
            conversation.closed_at = timezone.now()
        conversation.save()

        logger.info(
            "[Webhook Twilio] Conversación %s → respuesta=%s estado=%s",
            conversation.pk,
            response_choice,
            conv_status,
        )

        # Enviar respuesta de confirmación al cliente
        first_name = client.full_name.split()[0]
        if response_choice == Conversation.ResponseChoices.YES:
            reply = (
                f"¡Gracias {first_name}! 🎉 Registramos tu interés. "
                f"Un asesor se comunicará contigo pronto para completar tu migración."
            )
        else:
            reply = (
                f"Entendido, {first_name}. Hemos registrado tu respuesta. "
                f"Si cambias de opinión en el futuro, con gusto te atendemos. ¡Hasta pronto!"
            )

        channel = notification.channel
        twilio = TwilioService()
        try:
            if channel == "WHATSAPP":
                twilio.send_whatsapp(client.phone_number, reply)
            else:
                twilio.send_sms(client.phone_number, reply)
        except Exception as exc:
            logger.warning("[Webhook Twilio] No se pudo enviar confirmación a %s: %s", phone, exc)

        return Response({"detail": "ok"}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# Conversations (flujo asesor / chat)
# ─────────────────────────────────────────────────────────────────────────────


class ConversationListView(generics.ListAPIView):
    """
    GET — Lista conversaciones filtradas por estado, respuesta, asesor.
    """

    serializer_class = ConversationSerializer
    permission_classes = [IsAdminOrAnalyst]
    filterset_fields = ["status", "client_response", "had_response", "advisor"]

    def get_queryset(self):
        return Conversation.objects.select_related(
            "client", "notification", "advisor"
        ).all()


class ConversationDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   — Detalle de una conversación.
    PATCH — Asesor actualiza estado, notas o cierra la conversación.
    """

    permission_classes = [IsAdminOrAnalyst]

    def get_queryset(self):
        return Conversation.objects.select_related(
            "client", "notification", "advisor"
        ).all()

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ConversationUpdateSerializer
        return ConversationSerializer

    def perform_update(self, serializer):
        if self.request.data.get("assign_self"):
            serializer.save(advisor=self.request.user)
        else:
            serializer.save()


# ─────────────────────────────────────────────────────────────────────────────
# External API (RF20)
# ─────────────────────────────────────────────────────────────────────────────


class ExternalAPIQueryView(APIView):
    """
    GET — Consulta datos de un cliente en la API REST externa (RF20).
    Query param: ?phone_number=<str>
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        phone_number = request.query_params.get("phone_number")
        if not phone_number:
            return Response(
                {"detail": "Se requiere el parámetro phone_number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = ExternalAPIService()
        result = service.get_client_data(phone_number)
        return Response(result)
