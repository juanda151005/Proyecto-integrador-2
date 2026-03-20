from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import TopUp, ClientChangeLog
from .serializers import (
    TopUpSerializer,
    EligibilityResultSerializer,
    ClientChangeLogSerializer,
    AverageSpendingSerializer,
)
from .services import EligibilityEngine
from apps.core_business.models import Client


class TopUpListCreateView(generics.ListCreateAPIView):
    """
    GET  — Lista recargas (con filtro por cliente).
    POST — Registra una nueva recarga (RF11).
    """

    queryset = TopUp.objects.select_related("client").all()
    serializer_class = TopUpSerializer
    filterset_fields = ["client", "channel"]
    ordering_fields = ["date", "amount"]


class TopUpDetailView(generics.RetrieveAPIView):
    """GET — Detalle de una recarga."""

    queryset = TopUp.objects.select_related("client").all()
    serializer_class = TopUpSerializer


class CalculateAverageSpendingView(APIView):
    """
    POST — Calcula el gasto promedio para un cliente (RF12).
    Body: { "client_id": <int> }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        client_id = request.data.get("client_id")
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            return Response(
                {"detail": "Cliente no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        average, total_topups, months = EligibilityEngine.calculate_average_spending(
            client
        )

        # Actualizar gasto promedio en el cliente
        client.average_spending = average
        client.save(update_fields=["average_spending"])

        serializer = AverageSpendingSerializer(
            {
                "client_id": client.id,
                "phone_number": client.phone_number,
                "average_spending": average,
                "total_topups": total_topups,
                "months_analyzed": months,
            }
        )
        return Response(serializer.data)


class EvaluateEligibilityView(APIView):
    """
    POST — Evalúa elegibilidad de un cliente o de todos (RF13).
    Body: { "client_id": <int> }  o  { "evaluate_all": true }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.data.get("evaluate_all"):
            results = EligibilityEngine.evaluate_all_clients()
            serializer = EligibilityResultSerializer(results, many=True)
            return Response(serializer.data)

        client_id = request.data.get("client_id")
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            return Response(
                {"detail": "Cliente no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = EligibilityEngine.evaluate_client(client)
        serializer = EligibilityResultSerializer(result)
        return Response(serializer.data)


class ClientChangeLogListView(generics.ListAPIView):
    """
    GET — Historial de cambios de un cliente (RF18).
    Filtrar por client_id via query param.
    """

    serializer_class = ClientChangeLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ClientChangeLog.objects.select_related("client", "changed_by").all()
        client_id = self.request.query_params.get("client_id")
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset
