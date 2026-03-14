import csv
from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Client
from .serializers import ClientSerializer, ClientCreateSerializer, ClientExportSerializer
from .filters import ClientFilter


class ClientListCreateView(generics.ListCreateAPIView):
    """
    GET  — Lista de clientes con filtros de negocio (RF07).
    POST — Registro de nuevo cliente prepago (RF06).
    """
    queryset = Client.objects.all()
    filterset_class = ClientFilter
    search_fields = ['full_name', 'phone_number', 'document_number']
    ordering_fields = ['created_at', 'average_spending', 'activation_date']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ClientCreateSerializer
        return ClientSerializer


class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET / PUT / PATCH / DELETE un cliente (RF08, RF09).
    DELETE requiere validación previa (RF09).
    """
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    def destroy(self, request, *args, **kwargs):
        client = self.get_object()
        # RF09 — Validación previa: no eliminar clientes migrados
        if client.status == Client.StatusChoices.MIGRATED:
            return Response(
                {'detail': 'No se puede eliminar un cliente que ya fue migrado a postpago.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class ClientExportCSVView(APIView):
    """
    GET — Exporta la lista de clientes a CSV (RF10).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="clientes.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Teléfono', 'Nombre', 'Documento', 'Fecha Activación',
            'Plan', 'Elegible', 'Gasto Promedio', 'Estado',
        ])

        clients = Client.objects.all()
        for client in clients:
            writer.writerow([
                client.phone_number,
                client.full_name,
                client.document_number,
                client.activation_date,
                client.get_current_plan_display(),
                'Sí' if client.is_eligible else 'No',
                client.average_spending,
                client.get_status_display(),
            ])

        return response
