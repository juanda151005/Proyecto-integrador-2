from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.communications.models import NotificationLog
from apps.core_business.models import Client
from apps.users.permissions import IsAdmin, IsAdminOrAnalyst

from .audit import log_critical_action, snapshot_business_rule
from .models import AuditLog, BusinessRule, GlobalSystemSettings
from .serializers import (
    AuditLogSerializer,
    BusinessRuleSerializer,
    ConversionReportSerializer,
    GlobalSystemSettingsSerializer,
)


class GlobalSystemSettingsView(generics.RetrieveUpdateAPIView):
    """
    GET / PATCH — Configuración global del sistema (solo ADMIN).
    """

    serializer_class = GlobalSystemSettingsSerializer
    permission_classes = [IsAdmin]

    def get_object(self):
        return GlobalSystemSettings.get_solo()


class BusinessRuleListCreateView(generics.ListCreateAPIView):
    """
    GET  — Lista reglas de negocio (RF16).
    POST — Crea una nueva regla (solo ADMIN).
    """

    queryset = BusinessRule.objects.all()
    serializer_class = BusinessRuleSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        rule = serializer.save()
        log_critical_action(
            user=self.request.user,
            action=AuditLog.ActionChoices.CREATE,
            model_name="BusinessRule",
            object_id=str(rule.pk),
            before=None,
            after=snapshot_business_rule(rule),
            request=self.request,
        )


class BusinessRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET / PUT / PATCH / DELETE regla de negocio (solo ADMIN).
    """

    queryset = BusinessRule.objects.all()
    serializer_class = BusinessRuleSerializer
    permission_classes = [IsAdmin]

    def perform_update(self, serializer):
        before = snapshot_business_rule(serializer.instance)
        rule = serializer.save()
        log_critical_action(
            user=self.request.user,
            action=AuditLog.ActionChoices.UPDATE,
            model_name="BusinessRule",
            object_id=str(rule.pk),
            before=before,
            after=snapshot_business_rule(rule),
            request=self.request,
        )

    def perform_destroy(self, instance):
        object_id = str(instance.pk)
        before = snapshot_business_rule(instance)
        instance.delete()
        log_critical_action(
            user=self.request.user,
            action=AuditLog.ActionChoices.DELETE,
            model_name="BusinessRule",
            object_id=object_id,
            before=before,
            after=None,
            request=self.request,
        )


class AuditLogListView(generics.ListAPIView):
    """
    GET — Lista registros de auditoría (RF14).
    Solo rol Administrador (issue #14).
    """

    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["action", "model_name", "user"]
    ordering_fields = ["timestamp"]


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

        accepted = NotificationLog.objects.filter(status="ACCEPTED").count()
        rejected = NotificationLog.objects.filter(status="REJECTED").count()
        pending = NotificationLog.objects.filter(status="SENT").count()

        data = {
            "total_clients": total,
            "eligible_clients": eligible,
            "migrated_clients": migrated,
            "conversion_rate": round(conversion_rate, 2),
            "accepted": accepted,
            "rejected": rejected,
            "pending": pending,
        }

        serializer = ConversionReportSerializer(data)
        return Response(serializer.data)
