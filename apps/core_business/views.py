import csv
import io

from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.management.audit import log_critical_action, snapshot_client
from apps.management.models import AuditLog
from apps.users.permissions import IsAdmin, IsAdminOrAnalyst

from .filters import ClientFilter
from .models import Client, Plan
from .serializers import (
    ClientCreateSerializer,
    ClientImportRowSerializer,
    ClientSerializer,
    ClientUpdateSerializer,
    PlanSerializer,
)


# ─────────────────────────────────────────────────────────────────────────────
# Plan CRUD
# ─────────────────────────────────────────────────────────────────────────────


class PlanListCreateView(generics.ListCreateAPIView):
    """
    GET  — Lista planes configurados.
    POST — Crea un nuevo plan (solo ADMIN).
    """

    queryset = Plan.objects.all()
    serializer_class = PlanSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return [IsAuthenticated()]


class PlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET / PUT / PATCH / DELETE un plan (solo ADMIN para escritura).
    """

    queryset = Plan.objects.all()
    serializer_class = PlanSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdmin()]


# ─────────────────────────────────────────────────────────────────────────────
# Client CRUD
# ─────────────────────────────────────────────────────────────────────────────


class ClientListCreateView(generics.ListCreateAPIView):
    """
    GET  — Lista de clientes con filtros de negocio (RF07).
    POST — Registro de nuevo cliente prepago (RF06).
    """

    queryset = Client.objects.select_related("plan").all()
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

    queryset = Client.objects.select_related("plan").all()

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


# ─────────────────────────────────────────────────────────────────────────────
# Export CSV
# ─────────────────────────────────────────────────────────────────────────────


class ClientExportCSVView(APIView):
    """
    GET — Exporta la lista de clientes a CSV (RF10).
    Respeta los mismos filtros de ClientFilter via query params.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Client.objects.select_related("plan").all()
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
                "Plan Actual",
                "Código Plan Migración",
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
                    client.plan.code if client.plan else "",
                    "Sí" if client.is_eligible else "No",
                    client.average_spending,
                    client.get_status_display(),
                ]
            )

        return response


# ─────────────────────────────────────────────────────────────────────────────
# Import CSV / Excel
# ─────────────────────────────────────────────────────────────────────────────


class ClientImportView(APIView):
    """
    POST — Importación masiva de clientes desde CSV o Excel (RF06 extendido).

    Estructura del archivo (primera fila = encabezado):
        numero_celular    — 10 dígitos, empieza en 3
        nombre_completo   — texto libre
        numero_documento  — máx 20 caracteres
        correo            — email (opcional)
        fecha_activacion  — YYYY-MM-DD o DD/MM/YYYY
        codigo_plan       — referencia a Plan.code (opcional)

    Clientes existentes (identificados por numero_celular) se actualizan.
    """

    permission_classes = [IsAdminOrAnalyst]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"detail": "Se requiere un archivo (campo 'file')."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        filename = file_obj.name.lower()
        if filename.endswith(".csv"):
            result = self._parse_csv(file_obj)
        elif filename.endswith((".xlsx", ".xls")):
            result = self._parse_excel(file_obj)
        else:
            return Response(
                {"detail": "Formato no soportado. Use .csv o .xlsx"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(result, Response):
            return result

        rows = result
        created = 0
        updated = 0
        errors = []

        for idx, row in enumerate(rows, start=2):
            serializer = ClientImportRowSerializer(data=row)
            if not serializer.is_valid():
                errors.append({"fila": idx, "errores": serializer.errors})
                continue

            data = serializer.validated_data
            plan = None
            if data["codigo_plan"]:
                try:
                    plan = Plan.objects.get(code=data["codigo_plan"], is_active=True)
                except Plan.DoesNotExist:
                    errors.append(
                        {
                            "fila": idx,
                            "errores": {
                                "codigo_plan": f"No existe un plan activo con código '{data['codigo_plan']}'"
                            },
                        }
                    )
                    continue

            defaults = {
                "full_name": data["nombre_completo"],
                "document_number": data["numero_documento"],
                "email": data.get("correo", ""),
                "activation_date": data["fecha_activacion"],
                "plan": plan,
            }

            _client, is_new = Client.objects.update_or_create(
                phone_number=data["numero_celular"],
                defaults=defaults,
            )

            if is_new:
                created += 1
            else:
                updated += 1

        return Response(
            {
                "detail": (
                    f"Importación completada. "
                    f"Creados: {created}, Actualizados: {updated}, Errores: {len(errors)}."
                ),
                "created": created,
                "updated": updated,
                "error_count": len(errors),
                "errors": errors,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _parse_csv(file_obj):
        try:
            content = file_obj.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
            return [ClientImportView._normalize_row(row) for row in reader]
        except Exception as exc:
            return Response(
                {"detail": f"Error al leer el CSV: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @staticmethod
    def _parse_excel(file_obj):
        try:
            import openpyxl

            wb = openpyxl.load_workbook(file_obj, data_only=True)
            ws = wb.active
            rows_iter = ws.iter_rows(values_only=True)
            headers = [str(h).strip().lower() if h else "" for h in next(rows_iter)]
            rows = []
            for row in rows_iter:
                if all(cell is None for cell in row):
                    continue
                row_dict = {h: (str(v).strip() if v is not None else "") for h, v in zip(headers, row)}
                rows.append(ClientImportView._normalize_row(row_dict))
            return rows
        except Exception as exc:
            return Response(
                {"detail": f"Error al leer el Excel: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @staticmethod
    def _normalize_row(row):
        """Mapea nombres de columnas alternativos al nombre canónico del serializer."""
        alias = {
            "telefono": "numero_celular",
            "teléfono": "numero_celular",
            "phone": "numero_celular",
            "nombre": "nombre_completo",
            "name": "nombre_completo",
            "documento": "numero_documento",
            "document": "numero_documento",
            "email": "correo",
            "fecha activacion": "fecha_activacion",
            "fecha_de_activacion": "fecha_activacion",
            "activation_date": "fecha_activacion",
            "plan": "codigo_plan",
            "plan_code": "codigo_plan",
        }
        normalized = {}
        for key, value in row.items():
            clean = key.strip().lower()
            normalized[alias.get(clean, clean)] = str(value).strip() if value else ""
        return normalized
