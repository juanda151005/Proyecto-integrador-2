from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core_business.models import Client

from .authentication import ApiKeyAuthentication
from .permissions import HasValidApiKey
from .serializers import ProspectSerializer

_AUTH_NOTE = "**Autenticación:** header `X-API-Key: <tu_key>`."


@extend_schema(
    tags=["External API — RF20"],
    summary="Estado de la API externa",
    description="Health-check público para verificar que la API externa está activa. No requiere API Key.",
    responses={200: {"type": "object", "properties": {"status": {"type": "string"}, "version": {"type": "string"}}}},
)
class ExternalStatusView(APIView):
    """GET /api/v1/external/status/ — health-check público (no requiere API Key)."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok", "version": "1.0.0"}, status=status.HTTP_200_OK)


@extend_schema(
    tags=["External API — RF20"],
    summary="Listar prospectos elegibles",
    description=(
        "Retorna la lista paginada de clientes con `is_eligible=True`. " + _AUTH_NOTE
    ),
    parameters=[
        OpenApiParameter(
            "status",
            str,
            description="Filtrar por estado del cliente: ACTIVE, INACTIVE, MIGRATED.",
            required=False,
        ),
    ],
    examples=[
        OpenApiExample(
            "Respuesta exitosa",
            value={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": 1,
                        "phone_number": "3001234567",
                        "full_name": "Juan Pérez",
                        "current_plan": "PREPAGO_BASIC",
                        "plan_code": "PLAN_BASICO",
                        "plan_name": "Plan Básico Postpago",
                        "is_eligible": True,
                        "average_spending": "45000.00",
                        "seniority_days": 90,
                        "status": "ACTIVE",
                        "activation_date": "2025-02-10",
                        "created_at": "2025-02-10T10:00:00Z",
                    }
                ],
            },
            response_only=True,
        )
    ],
)
class ExternalProspectListView(generics.ListAPIView):
    """GET /api/v1/external/prospects/ — lista de prospectos elegibles para CRM."""

    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [HasValidApiKey]
    serializer_class = ProspectSerializer

    def get_queryset(self):
        qs = Client.objects.filter(is_eligible=True).select_related("plan")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return qs


@extend_schema(
    tags=["External API — RF20"],
    summary="Detalle de un prospecto",
    description="Retorna el detalle de un cliente elegible por su ID. " + _AUTH_NOTE,
)
class ExternalProspectDetailView(generics.RetrieveAPIView):
    """GET /api/v1/external/prospects/{id}/ — detalle de un prospecto."""

    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [HasValidApiKey]
    serializer_class = ProspectSerializer
    queryset = Client.objects.filter(is_eligible=True).select_related("plan")
