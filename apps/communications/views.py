from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import NotificationLog
from .serializers import (
    NotificationLogSerializer,
    SendNotificationSerializer,
    BulkNotificationSerializer,
)
from .services import TwilioService, ExternalAPIService
from apps.core_business.models import Client
from apps.users.permissions import IsAdmin, IsAdminOrAnalyst


class NotificationLogListView(generics.ListAPIView):
    """
    GET — Lista logs de notificaciones enviadas.
    """
    queryset = NotificationLog.objects.select_related('client').all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['channel', 'status', 'client']


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
            client = Client.objects.get(pk=serializer.validated_data['client_id'])
        except Client.DoesNotExist:
            return Response(
                {'detail': 'Cliente no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        channel = serializer.validated_data['channel']
        message = serializer.validated_data['message']

        # Enviar via Twilio
        twilio = TwilioService()
        if channel == 'WHATSAPP':
            result = twilio.send_whatsapp(client.phone_number, message)
        else:
            result = twilio.send_sms(client.phone_number, message)

        # Registrar en log
        log = NotificationLog.objects.create(
            client=client,
            message=message,
            channel=channel,
            status='SENT' if result['success'] else 'FAILED',
            external_id=result.get('sid', ''),
        )

        return Response(
            NotificationLogSerializer(log).data,
            status=status.HTTP_201_CREATED,
        )


class BulkNotifyEligibleView(APIView):
    """
    POST — Envío masivo de ofertas a todos los clientes elegibles (RF15).
    Body: { "channel": "WHATSAPP"|"SMS", "message": "..." }
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = BulkNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        eligible_clients = Client.objects.filter(
            is_eligible=True,
            status=Client.StatusChoices.ACTIVE,
        )

        if not eligible_clients.exists():
            return Response(
                {'detail': 'No hay clientes elegibles activos.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        channel = serializer.validated_data['channel']
        message = serializer.validated_data['message']
        results = {'sent': 0, 'failed': 0}

        twilio = TwilioService()
        for client in eligible_clients:
            if channel == 'WHATSAPP':
                result = twilio.send_whatsapp(client.phone_number, message)
            else:
                result = twilio.send_sms(client.phone_number, message)

            NotificationLog.objects.create(
                client=client,
                message=message,
                channel=channel,
                status='SENT' if result['success'] else 'FAILED',
                external_id=result.get('sid', ''),
            )

            if result['success']:
                results['sent'] += 1
            else:
                results['failed'] += 1

        return Response({
            'detail': f'Envío masivo completado. Enviados: {results["sent"]}, Fallidos: {results["failed"]}',
            **results,
        })


class ExternalAPIQueryView(APIView):
    """
    GET — Consulta datos de un cliente en la API REST externa (RF20).
    Query param: ?phone_number=<str>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        phone_number = request.query_params.get('phone_number')
        if not phone_number:
            return Response(
                {'detail': 'Se requiere el parámetro phone_number.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = ExternalAPIService()
        result = service.get_client_data(phone_number)
        return Response(result)
