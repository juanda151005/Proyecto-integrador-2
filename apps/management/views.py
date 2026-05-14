from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.communications.models import Conversation, NotificationLog
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

    Incluye tasas de aceptación (Sí) y rechazo (No) sobre respuestas registradas,
    contadores de clientes únicos contactados vs ofertas enviadas (envíos exitosos),
    y porcentaje de migración respecto al universo contactado.
    """

    permission_classes = [IsAdminOrAnalyst]

    def get(self, request):
        from django.db.models import Avg, Count

        total = Client.objects.count()
        active = Client.objects.filter(status=Client.StatusChoices.ACTIVE).count()
        inactive = Client.objects.filter(status=Client.StatusChoices.INACTIVE).count()
        eligible = Client.objects.filter(is_eligible=True).count()
        migrated = Client.objects.filter(status=Client.StatusChoices.MIGRATED).count()

        avg_spending = Client.objects.aggregate(Avg("average_spending"))["average_spending__avg"]
        avg_spending = float(avg_spending) if avg_spending else 0.0

        # Notificaciones
        total_notifications = NotificationLog.objects.count()
        accepted = NotificationLog.objects.filter(
            status=NotificationLog.StatusChoices.ACCEPTED
        ).count()
        rejected = NotificationLog.objects.filter(
            status=NotificationLog.StatusChoices.REJECTED
        ).count()
        pending = NotificationLog.objects.filter(
            status=NotificationLog.StatusChoices.SENT
        ).count()
        failed = NotificationLog.objects.filter(
            status=NotificationLog.StatusChoices.FAILED
        ).count()

        # RF17 — Ofertas enviadas con éxito (excluye FAILED): un registro = un envío
        sent_offer_statuses = [
            NotificationLog.StatusChoices.SENT,
            NotificationLog.StatusChoices.ACCEPTED,
            NotificationLog.StatusChoices.REJECTED,
        ]
        offers_qs = NotificationLog.objects.filter(status__in=sent_offer_statuses)
        offers_sent = offers_qs.count()
        customers_contacted = offers_qs.aggregate(n=Count("client", distinct=True))["n"] or 0

        contacted_ids = offers_qs.values_list("client_id", flat=True).distinct()
        migrated_among_contacted = Client.objects.filter(
            status=Client.StatusChoices.MIGRATED,
            pk__in=contacted_ids,
        ).count()
        migration_rate_vs_contacted = (
            round(migrated_among_contacted / customers_contacted * 100, 2)
            if customers_contacted > 0
            else 0.0
        )

        # Conversaciones
        open_conversations = Conversation.objects.filter(
            status=Conversation.StatusChoices.OPEN
        ).count()
        closed_conversations = Conversation.objects.filter(
            status=Conversation.StatusChoices.CLOSED
        ).count()
        interested = Conversation.objects.filter(
            client_response=Conversation.ResponseChoices.YES
        ).count()
        not_interested = Conversation.objects.filter(
            client_response=Conversation.ResponseChoices.NO
        ).count()

        responses_total = interested + not_interested
        acceptance_rate = (
            round(interested / responses_total * 100, 2) if responses_total > 0 else 0.0
        )
        rejection_rate = (
            round(not_interested / responses_total * 100, 2) if responses_total > 0 else 0.0
        )

        response_rate = (
            round((accepted + rejected) / total_notifications * 100, 2)
            if total_notifications > 0
            else 0
        )

        data = {
            "total_clients": total,
            "active_clients": active,
            "inactive_clients": inactive,
            "eligible_clients": eligible,
            "migrated_clients": migrated,
            # Misma métrica que migration_rate_vs_contacted (KPI RF17)
            "conversion_rate": migration_rate_vs_contacted,
            "migrated_among_contacted": migrated_among_contacted,
            "migration_rate_vs_contacted": migration_rate_vs_contacted,
            "customers_contacted": customers_contacted,
            "offers_sent": offers_sent,
            "acceptance_rate": acceptance_rate,
            "rejection_rate": rejection_rate,
            "responses_total": responses_total,
            "average_spending_global": avg_spending,
            "total_notifications": total_notifications,
            "accepted": accepted,
            "rejected": rejected,
            "pending": pending,
            "failed": failed,
            "response_rate": response_rate,
            "open_conversations": open_conversations,
            "closed_conversations": closed_conversations,
            "interested": interested,
            "not_interested": not_interested,
        }

        serializer = ConversionReportSerializer(data)
        return Response(serializer.data)
