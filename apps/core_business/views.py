import csv

from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.management.audit import log_critical_action, snapshot_client
from apps.management.models import AuditLog

from .filters import ClientFilter
from .models import Client
from .serializers import (
    ClientCreateSerializer,
    ClientSerializer,
    ClientUpdateSerializer,
)


class ClientListCreateView(generics.ListCreateAPIView):
    """
    GET  — Lista de clientes con filtros de negocio (RF07).
    POST — Registro de nuevo cliente prepago (RF06).
    """

    queryset = Client.objects.all()
    filterset_class = ClientFilter
    search_fields = ["full_name", "phone_number", "document_number"]
    ordering_fields = ["created_at", "average_spending", "activation_date"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ClientCreateSerializer
        return ClientSerializer


class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET / PUT / PATCH / DELETE un cliente (RF08, RF09).
    DELETE requiere validación previa (RF09).
    """

    queryset = Client.objects.all()

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ClientUpdateSerializer
        return ClientSerializer

    def perform_update(self, serializer):
        before = snapshot_client(serializer.instance)
        client = serializer.save()
        log_critical_action(
            user=self.request.user,
            action=AuditLog.ActionChoices.UPDATE,
            model_name="Client",
            object_id=str(client.pk),
            before=before,
            after=snapshot_client(client),
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        client = self.get_object()
        # RF09 — Validación previa: no eliminar clientes migrados
        if client.status == Client.StatusChoices.MIGRATED:
            return Response(
                {
                    "detail": "No se puede eliminar un cliente que ya fue migrado a postpago."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        object_id = str(client.pk)
        before = snapshot_client(client)
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == status.HTTP_204_NO_CONTENT:
            log_critical_action(
                user=request.user,
                action=AuditLog.ActionChoices.DELETE,
                model_name="Client",
                object_id=object_id,
                before=before,
                after=None,
                request=request,
            )
        return response


class ClientExportCSVView(APIView):
    """
    GET — Exporta la lista de clientes a CSV (RF10).
    Respeta los mismos filtros de ClientFilter via query params.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Aplicar filtros del negocio al queryset
        queryset = Client.objects.all()
        filterset = ClientFilter(request.query_params, queryset=queryset)
        clients = filterset.qs

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="clientes.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Teléfono",
                "Nombre",
                "Documento",
                "Email",
                "Fecha Activación",
                "Plan",
                "Elegible",
                "Gasto Promedio",
                "Estado",
            ]
        )

        for client in clients:
            writer.writerow(
                [
                    client.phone_number,
                    client.full_name,
                    client.document_number,
                    client.email,
                    client.activation_date,
                    client.get_current_plan_display(),
                    "Sí" if client.is_eligible else "No",
                    client.average_spending,
                    client.get_status_display(),
                ]
            )

        return response
