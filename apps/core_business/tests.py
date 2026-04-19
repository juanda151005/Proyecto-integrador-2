from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
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
        # RF06/RF08 requieren que el creador/editor sea un Analista
        analista_group, _ = Group.objects.get_or_create(name="Analista")
        self.user.groups.add(analista_group)

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

    def test_admin_crea_cliente_exito(self):
        """Privilegio de Administrador: también deben poder crear un nuevo cliente."""
        admin_user = User.objects.create_superuser(
            username="adminroot", email="adminroot@test.com", password="Pass123"
        )
        api_admin = APIClient()
        api_admin.force_authenticate(user=admin_user)
        self.client_data["phone_number"] = "3007777777"
        response = api_admin.post("/api/v1/clients/", self.client_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cp_1_1_registro_exitoso_datos_basicos(self):
        """
        CP 1.1: Registro exitoso de datos básicos.
        El sistema permite guardar la fecha de activación y el plan actual del cliente.
        """
        response = self.api.post("/api/v1/clients/", self.client_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["phone_number"], "3001234567")
        self.assertEqual(response.data["full_name"], "Juan Pérez")

        # Validación de que la fecha y el plan se guardan correctamente en DB
        client = Client.objects.get(phone_number="3001234567")
        self.assertEqual(str(client.activation_date), "2026-01-15")
        self.assertEqual(client.current_plan, "PREPAGO_BASIC")

    def test_cp_1_2_validacion_campos_obligatorios(self):
        """
        CP 1.2: Validación de campos obligatorios.
        Se intenta guardar la información dejando vacía la fecha de activación o el tipo de plan.
        El sistema impide el registro y resalta los campos obligatorios.
        """
        # Testing con values empty que fallarán con el validador de forms
        self.client_data["activation_date"] = ""
        self.client_data["current_plan"] = ""
        response = self.api.post("/api/v1/clients/", self.client_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("activation_date", response.data)
        # Nota: current_plan tiene "PREPAGO_BASIC" como default en el modelo,
        # pero si es required=True en frontend se validará. Mandar vacío debería lanzar error en serializador si es choice.
        self.assertIn("current_plan", response.data)

    def test_cp_2_1_validacion_unicidad_telefono(self):
        """
        CP 2.1: Validación de unicidad de teléfono.
        Se intenta crear un nuevo cliente utilizando ese mismo número telefónico.
        El backend bloquea la operación y muestra una alerta indicando que el número ya está vinculado a otro registro.
        """
        self.client_data["phone_number"] = self.client_obj.phone_number
        response = self.api.post("/api/v1/clients/", self.client_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_cp_2_2_validacion_formato_telefono(self):
        """
        CP 2.2: Validación de formato de teléfono.
        Se ingresa un valor inválido en el campo de teléfono (ej. letras o menos de 10 dígitos).
        El sistema activa el mensaje de error de formato.
        """
        # Prueba menos de 10 dígitos
        self.client_data["phone_number"] = "12345"
        response = self.api.post("/api/v1/clients/", self.client_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

        # Prueba con letras
        self.client_data["phone_number"] = "300ABCDEF1"
        response2 = self.api.post("/api/v1/clients/", self.client_data, format="json")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response2.data)


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

    def test_cp_1_1_persistencia_relaciones_tras_edicion(self):
        """
        CP 1.1: Persistencia de relaciones tras edición.
        Se actualiza el tipo de plan en su perfil.
        El sistema guarda el cambio correctamente y mantiene los demás datos intactos.
        """
        url = f"/api/v1/clients/{self.client_obj.pk}/"
        response = self.api.patch(
            url, {"current_plan": "PREPAGO_PREMIUM"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.current_plan, "PREPAGO_PREMIUM")
        # Asegurar integridad de campos asociados
        self.assertEqual(self.client_obj.phone_number, "3009999999")

    def test_cp_1_2_validacion_integridad_campos_criticos(self):
        """
        CP 1.2: Validación de integridad en campos críticos.
        Se intenta guardar una modificación con datos inválidos (ej. teléfono con formato erróneo).
        El sistema bloquea la actualización y mantiene la información original.
        """
        url = f"/api/v1/clients/{self.client_obj.pk}/"
        original_phone = self.client_obj.phone_number
        # El serializer de Update tiene phone_number como read_only_fields (se ignora).
        response = self.api.patch(
            url,
            {"phone_number": "formato-erroneo", "activation_date": "10-01-2026"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("activation_date", response.data)

        # Validar que no mutó nada en la BD
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.phone_number, original_phone)

    def test_cp_2_1_restriccion_edicion_por_rol(self):
        """
        CP 2.1: Restricción de edición por rol.
        El usuario está autenticado con rol "Asesor". Intenta enviar petición PATCH al sistema.
        La plataforma deniega la acción y muestra un mensaje de acceso restringido.
        """
        asesor_user = User.objects.create_user(
            username="asesor", email="asesor@test.com", password="Pass123"
        )
        from django.contrib.auth.models import Group

        asesor_group, _ = Group.objects.get_or_create(name="Asesor")
        asesor_user.groups.add(asesor_group)

        api_asesor = APIClient()
        api_asesor.force_authenticate(user=asesor_user)

        url = f"/api/v1/clients/{self.client_obj.pk}/"
        response = api_asesor.patch(url, {"full_name": "Hack"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cp_2_2_ejecucion_edicion_autorizada(self):
        """
        CP 2.2: Ejecución de edición autorizada.
        El usuario está autenticado como 'Analista'. Se corrige un dato y se guarda el cambio.
        El sistema valida permiso y aplica actualización.
        """
        # self.user es nuestro analista creado en setUp
        from django.contrib.auth.models import Group

        analista_group, _ = Group.objects.get_or_create(name="Analista")
        self.user.groups.add(analista_group)

        url = f"/api/v1/clients/{self.client_obj.pk}/"
        response = self.api.patch(
            url, {"full_name": "María López (Corregido)"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.full_name, "María López (Corregido)")


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
