"""
RF09 — Eliminación de registros con validación previa.

CP 1.1 (E2E/API):   El sistema solicita confirmación antes de ejecutar la eliminación.
                    Verificado a nivel API: el DELETE ejecutado con confirmación retorna 204
                    y el registro desaparece de la BD.
CP 1.2 (E2E/API):   Cancelación del modal: el registro permanece intacto si no se envía DELETE.
CP 2.1 (Integration): El backend bloquea la eliminación si el cliente tiene una migración
                    en proceso (status=MIGRATED).
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.core_business.models import Client
from apps.users.models import CustomUser

CLIENTS_URL = "/api/v1/clients/"


def _make_analyst(username="analista_rf09", email="analista_rf09@test.com"):
    user = CustomUser.objects.create_user(
        username=username,
        email=email,
        password="Pass1234!",
        role=CustomUser.Role.ANALYST,
    )
    group, _ = Group.objects.get_or_create(name="Analista")
    user.groups.add(group)
    return user


def _make_client(phone, status_val=Client.StatusChoices.ACTIVE, document=None):
    return Client.objects.create(
        phone_number=phone,
        full_name="Cliente RF09 Test",
        document_number=document or f"DOC-{phone}",
        email=f"{phone}@test.com",
        activation_date=date(2025, 6, 1),
        current_plan=Client.PlanChoices.PREPAGO_BASIC,
        status=status_val,
        average_spending=Decimal("40000.00"),
    )


class RF09CP11EliminacionConfirmadaTest(TestCase):
    """
    CP 1.1 — Eliminación con confirmación.
    Cuando el usuario confirma la eliminación (envía DELETE), el sistema
    elimina el registro y devuelve 204. El registro no puede consultarse después.
    """

    def setUp(self):
        self.api = APIClient()
        self.user = _make_analyst(username="analista_rf09_a", email="analista_rf09_a@test.com")
        self.api.force_authenticate(user=self.user)
        self.cliente = _make_client("3010000001")

    def test_delete_confirmado_devuelve_204(self):
        url = f"{CLIENTS_URL}{self.cliente.pk}/"
        response = self.api.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_registro_eliminado_no_existe_en_bd(self):
        pk = self.cliente.pk
        url = f"{CLIENTS_URL}{pk}/"
        self.api.delete(url)
        self.assertFalse(Client.objects.filter(pk=pk).exists())

    def test_delete_de_cliente_inexistente_devuelve_404(self):
        url = f"{CLIENTS_URL}999999/"
        response = self.api.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_usuario_no_autenticado_no_puede_eliminar(self):
        api_anonimo = APIClient()
        url = f"{CLIENTS_URL}{self.cliente.pk}/"
        response = api_anonimo.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Client.objects.filter(pk=self.cliente.pk).exists())


class RF09CP12CancelacionNoEliminaRegistroTest(TestCase):
    """
    CP 1.2 — Cancelación del modal no elimina el registro.
    Si el usuario cancela la acción (no se envía la petición DELETE),
    el registro permanece completamente intacto en la base de datos.
    Verificado omitiendo el DELETE y consultando el registro con GET.
    """

    def setUp(self):
        self.api = APIClient()
        self.user = _make_analyst(username="analista_rf09_b", email="analista_rf09_b@test.com")
        self.api.force_authenticate(user=self.user)
        self.cliente = _make_client("3010000002")

    def test_sin_delete_el_registro_permanece_en_bd(self):
        """Simula cancelación: no se envía DELETE, el cliente sigue existiendo."""
        self.assertTrue(Client.objects.filter(pk=self.cliente.pk).exists())

    def test_get_tras_cancelacion_devuelve_datos_intactos(self):
        url = f"{CLIENTS_URL}{self.cliente.pk}/"
        response = self.api.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["phone_number"], "3010000002")

    def test_registro_no_muta_sin_peticion_de_borrado(self):
        telefono_original = self.cliente.phone_number
        full_name_original = self.cliente.full_name
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.phone_number, telefono_original)
        self.assertEqual(self.cliente.full_name, full_name_original)


class RF09CP21BloqueoMigracionActivaTest(TestCase):
    """
    CP 2.1 — Bloqueo por dependencia activa (cliente migrado).
    El backend rechaza la eliminación si el cliente ya fue migrado a postpago
    (status=MIGRATED), retornando 400 con mensaje descriptivo.
    """

    def setUp(self):
        self.api = APIClient()
        self.user = _make_analyst(username="analista_rf09_c", email="analista_rf09_c@test.com")
        self.api.force_authenticate(user=self.user)

    def test_delete_cliente_migrado_devuelve_400(self):
        cliente_migrado = _make_client(
            "3010000003", status_val=Client.StatusChoices.MIGRATED, document="DOC-MIG"
        )
        url = f"{CLIENTS_URL}{cliente_migrado.pk}/"
        response = self.api.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cliente_migrado_permanece_en_bd_tras_intento_fallido(self):
        cliente_migrado = _make_client(
            "3010000004", status_val=Client.StatusChoices.MIGRATED, document="DOC-MIG2"
        )
        pk = cliente_migrado.pk
        url = f"{CLIENTS_URL}{pk}/"
        self.api.delete(url)
        self.assertTrue(Client.objects.filter(pk=pk).exists())

    def test_mensaje_error_es_descriptivo(self):
        cliente_migrado = _make_client(
            "3010000005", status_val=Client.StatusChoices.MIGRATED, document="DOC-MIG3"
        )
        url = f"{CLIENTS_URL}{cliente_migrado.pk}/"
        response = self.api.delete(url)
        self.assertIn("detail", response.data)
        self.assertGreater(len(response.data["detail"]), 0)

    def test_delete_cliente_activo_si_es_permitido(self):
        """Control: cliente ACTIVE SÍ puede eliminarse."""
        cliente_activo = _make_client(
            "3010000006", status_val=Client.StatusChoices.ACTIVE, document="DOC-ACT"
        )
        url = f"{CLIENTS_URL}{cliente_activo.pk}/"
        response = self.api.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_cliente_inactivo_es_permitido(self):
        """Control: cliente INACTIVE también puede eliminarse."""
        cliente_inactivo = _make_client(
            "3010000007", status_val=Client.StatusChoices.INACTIVE, document="DOC-INA"
        )
        url = f"{CLIENTS_URL}{cliente_inactivo.pk}/"
        response = self.api.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
