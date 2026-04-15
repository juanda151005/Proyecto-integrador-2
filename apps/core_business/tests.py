from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Client

User = get_user_model()


class ClientBaseTestCase(TestCase):
    """Base con usuario autenticado y cliente de ejemplo."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="analista",
            email="analista@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

        self.client_data = {
            "phone_number": "3001234567",
            "full_name": "Juan Pérez",
            "document_number": "1234567890",
            "email": "juan@example.com",
            "activation_date": "2026-01-15",
            "current_plan": "PREPAGO_BASIC",
        }

        self.client_obj = Client.objects.create(
            phone_number="3009999999",
            full_name="María García",
            document_number="9876543210",
            email="maria@example.com",
            activation_date=date(2026, 1, 10),
            current_plan=Client.PlanChoices.PREPAGO_PLUS,
            status=Client.StatusChoices.ACTIVE,
            average_spending=Decimal("55000.00"),
        )


# ═════════════════════════════════════════════════════════════════════════════
# RF06 — Registro de clientes prepago
# ═════════════════════════════════════════════════════════════════════════════


class ClientCreateTests(ClientBaseTestCase):
    """Tests para POST /api/v1/clients/ (RF06)."""

    def test_create_client_success(self):
        """POST con datos válidos → 201."""
        response = self.api.post("/api/v1/clients/", self.client_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["phone_number"], "3001234567")
        self.assertEqual(response.data["full_name"], "Juan Pérez")
        self.assertTrue(Client.objects.filter(phone_number="3001234567").exists())

    def test_create_client_duplicate_phone(self):
        """POST con teléfono duplicado → 400."""
        self.client_data["phone_number"] = self.client_obj.phone_number
        response = self.api.post("/api/v1/clients/", self.client_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_client_invalid_phone_format(self):
        """POST con teléfono que no cumple regex → 400."""
        self.client_data["phone_number"] = "12345"
        response = self.api.post("/api/v1/clients/", self.client_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_create_client_phone_no_starts_with_3(self):
        """POST con teléfono que no empieza con 3 → 400."""
        self.client_data["phone_number"] = "5001234567"
        response = self.api.post("/api/v1/clients/", self.client_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ═════════════════════════════════════════════════════════════════════════════
# RF07 — Consulta y filtros
# ═════════════════════════════════════════════════════════════════════════════


class ClientListFilterTests(ClientBaseTestCase):
    """Tests para GET /api/v1/clients/ con filtros (RF07)."""

    def test_list_clients(self):
        """GET lista paginada → 200 con resultados."""
        response = self.api.get("/api/v1/clients/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_filter_by_plan(self):
        """GET ?current_plan=PREPAGO_PLUS → solo ese plan."""
        response = self.api.get("/api/v1/clients/?current_plan=PREPAGO_PLUS")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertEqual(item["current_plan"], "PREPAGO_PLUS")

    def test_filter_by_search(self):
        """GET ?search=María → filtra por nombre parcial."""
        response = self.api.get("/api/v1/clients/?search=María")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_filter_by_spending_range(self):
        """GET ?min_spending=50000&max_spending=60000 → clientes en rango."""
        response = self.api.get(
            "/api/v1/clients/?min_spending=50000&max_spending=60000"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)


# ═════════════════════════════════════════════════════════════════════════════
# RF08 — Actualización de registros
# ═════════════════════════════════════════════════════════════════════════════


class ClientUpdateTests(ClientBaseTestCase):
    """Tests para PUT/PATCH /api/v1/clients/<id>/ (RF08)."""

    def test_update_client_patch(self):
        """PATCH actualiza campos permitidos → 200."""
        url = f"/api/v1/clients/{self.client_obj.pk}/"
        response = self.api.patch(url, {"full_name": "María López"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.full_name, "María López")

    def test_update_blocks_phone_change(self):
        """PATCH phone_number → campo no cambia (read_only en update)."""
        url = f"/api/v1/clients/{self.client_obj.pk}/"
        original_phone = self.client_obj.phone_number
        response = self.api.patch(url, {"phone_number": "3111111111"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.phone_number, original_phone)

    def test_update_blocks_document_change(self):
        """PATCH document_number → campo no cambia (read_only en update)."""
        url = f"/api/v1/clients/{self.client_obj.pk}/"
        original_doc = self.client_obj.document_number
        response = self.api.patch(url, {"document_number": "0000000000"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.document_number, original_doc)


# ═════════════════════════════════════════════════════════════════════════════
# RF09 — Eliminación con validación
# ═════════════════════════════════════════════════════════════════════════════


class ClientDeleteTests(ClientBaseTestCase):
    """Tests para DELETE /api/v1/clients/<id>/ (RF09)."""

    def test_delete_active_client(self):
        """DELETE cliente ACTIVE → 204."""
        url = f"/api/v1/clients/{self.client_obj.pk}/"
        response = self.api.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Client.objects.filter(pk=self.client_obj.pk).exists())

    def test_delete_migrated_client_rejected(self):
        """DELETE cliente MIGRATED → 400 con mensaje de error."""
        self.client_obj.status = Client.StatusChoices.MIGRATED
        self.client_obj.save()
        url = f"/api/v1/clients/{self.client_obj.pk}/"
        response = self.api.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        # Cliente sigue existiendo
        self.assertTrue(Client.objects.filter(pk=self.client_obj.pk).exists())


# ═════════════════════════════════════════════════════════════════════════════
# RF10 — Exportación CSV
# ═════════════════════════════════════════════════════════════════════════════


class ClientCSVExportTests(ClientBaseTestCase):
    """Tests para GET /api/v1/clients/export/csv/ (RF10)."""

    def test_csv_export(self):
        """GET export/csv/ → content-type text/csv."""
        response = self.api.get("/api/v1/clients/export/csv/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        self.assertIn("Teléfono", content)
        self.assertIn(self.client_obj.phone_number, content)

    def test_csv_export_with_filter(self):
        """GET export/csv/?status=ACTIVE → solo clientes activos en CSV."""
        # Crear un cliente inactivo
        Client.objects.create(
            phone_number="3112223344",
            full_name="Pedro Inactivo",
            document_number="1111111111",
            activation_date=date(2026, 2, 1),
            status=Client.StatusChoices.INACTIVE,
        )
        response = self.api.get("/api/v1/clients/export/csv/?status=ACTIVE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode("utf-8")
        self.assertIn(self.client_obj.phone_number, content)
        self.assertNotIn("Pedro Inactivo", content)


# ═════════════════════════════════════════════════════════════════════════════
# Autenticación
# ═════════════════════════════════════════════════════════════════════════════


class ClientAuthenticationTests(TestCase):
    """Tests de acceso sin autenticación."""

    def test_unauthenticated_list(self):
        """GET /api/v1/clients/ sin token → 401."""
        api = APIClient()
        response = api.get("/api/v1/clients/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_export(self):
        """GET /api/v1/clients/export/csv/ sin token → 401."""
        api = APIClient()
        response = api.get("/api/v1/clients/export/csv/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
