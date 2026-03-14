from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import BusinessRule, AuditLog
from .serializers import (
    BusinessRuleSerializer,
    AuditLogSerializer,
    ConversionReportSerializer,
)
from apps.users.permissions import IsAdmin, IsAdminOrAnalyst
from apps.core_business.models import Client
from apps.communications.models import NotificationLog


class BusinessRuleListCreateView(generics.ListCreateAPIView):
    """
    GET  — Lista reglas de negocio (RF16).
    POST — Crea una nueva regla (solo ADMIN).
    """
    queryset = BusinessRule.objects.all()
    serializer_class = BusinessRuleSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return [IsAuthenticated()]


class BusinessRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET / PUT / PATCH / DELETE regla de negocio (solo ADMIN).
    """
    queryset = BusinessRule.objects.all()
    serializer_class = BusinessRuleSerializer
    permission_classes = [IsAdmin]


class AuditLogListView(generics.ListAPIView):
    """
    GET — Lista registros de auditoría (RF14).
    Solo ADMIN y ANALYST.
    """
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminOrAnalyst]
    filterset_fields = ['action', 'model_name', 'user']
    ordering_fields = ['timestamp']


class ConversionReportView(APIView):
    """
    GET — Dashboard de reportes de conversión (RF17).
    """
    permission_classes = [IsAdminOrAnalyst]

    def get(self, request):
        total = Client.objects.count()
        eligible = Client.objects.filter(is_eligible=True).count()
        migrated = Client.objects.filter(status=Client.StatusChoices.MIGRATED).count()
        conversion_rate = (migrated / total * 100) if total > 0 else 0

        accepted = NotificationLog.objects.filter(status='ACCEPTED').count()
        rejected = NotificationLog.objects.filter(status='REJECTED').count()
        pending = NotificationLog.objects.filter(status='SENT').count()

        data = {
            'total_clients': total,
            'eligible_clients': eligible,
            'migrated_clients': migrated,
            'conversion_rate': round(conversion_rate, 2),
            'accepted': accepted,
            'rejected': rejected,
            'pending': pending,
        }

        serializer = ConversionReportSerializer(data)
        return Response(serializer.data)
