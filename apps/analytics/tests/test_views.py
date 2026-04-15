"""
Tests de vistas para RF11 - Registro de recargas.
Verifica el comportamiento HTTP del endpoint /api/v1/analytics/topups/.
"""

import datetime

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.core_business.models import Client
from apps.users.models import CustomUser

from ..models import TopUp

TOPUPS_URL = "/api/v1/analytics/topups/"


def make_client(phone="3001234567", client_status=Client.StatusChoices.ACTIVE):
    return Client.objects.create(
        phone_number=phone,
        full_name="Cliente Test",
        document_number=f"DOC{phone}",
        activation_date=datetime.date(2025, 1, 1),
        current_plan=Client.PlanChoices.PREPAGO_BASIC,
        status=client_status,
    )


def make_user(username="analyst_test", role=CustomUser.Role.ANALYST):
    return CustomUser.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="TestPass123*",
        role=role,
    )


class TopUpEndpointTest(TestCase):
    """Pruebas de integracion para el endpoint de recargas (RF11)."""

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client_activo = make_client(phone="3009999999")
        self.client_inactivo = make_client(
            phone="3008888888",
            client_status=Client.StatusChoices.INACTIVE,
        )
        self.client_migrado = make_client(
            phone="3007777777",
            client_status=Client.StatusChoices.MIGRATED,
        )

    # -------------------------------------------------------------------------
    # Autenticacion
    # -------------------------------------------------------------------------

    def test_post_sin_autenticacion_retorna_401(self):
        """RF11: Sin token JWT el endpoint retorna 401."""
        response = self.client.post(
            TOPUPS_URL,
            {
                "client": self.client_activo.id,
                "amount": "20000.00",
                "date": "2026-01-15",
                "channel": "APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_sin_autenticacion_retorna_401(self):
        """RF11: GET sin token JWT retorna 401."""
        response = self.client.get(TOPUPS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -------------------------------------------------------------------------
    # Casos exitosos
    # -------------------------------------------------------------------------

    def test_post_crea_recarga_y_retorna_201(self):
        """RF11: POST valido crea el registro y retorna 201 Created."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            TOPUPS_URL,
            {
                "client": self.client_activo.id,
                "amount": "20000.00",
                "date": "2026-01-15",
                "channel": "APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TopUp.objects.count(), 1)

    def test_post_retorna_campos_del_criterio_de_aceptacion(self):
        """
        RF11 - Criterio de aceptacion:
        El registro devuelto incluye monto exacto, fecha y cliente asociado.
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            TOPUPS_URL,
            {
                "client": self.client_activo.id,
                "amount": "35000.00",
                "date": "2026-02-10",
                "channel": "STORE",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertIn("amount", data)
        self.assertIn("date", data)
        self.assertIn("client", data)
        self.assertEqual(data["amount"], "35000.00")
        self.assertEqual(data["date"], "2026-02-10")
        self.assertEqual(data["client"], self.client_activo.id)

    def test_get_lista_recargas_retorna_200(self):
        """RF11: GET retorna la lista de recargas registradas."""
        TopUp.objects.create(
            client=self.client_activo,
            amount=10000,
            date=datetime.date(2026, 1, 5),
            channel=TopUp.ChannelChoices.APP,
        )
        TopUp.objects.create(
            client=self.client_activo,
            amount=15000,
            date=datetime.date(2026, 1, 20),
            channel=TopUp.ChannelChoices.ONLINE,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(TOPUPS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 2)

    def test_multiples_recargas_mismo_cliente_permitidas(self):
        """RF11: Un cliente puede acumular multiples recargas."""
        self.client.force_authenticate(user=self.user)
        for monto in [10000, 15000, 20000]:
            response = self.client.post(
                TOPUPS_URL,
                {
                    "client": self.client_activo.id,
                    "amount": str(monto),
                    "date": "2026-01-15",
                    "channel": "APP",
                },
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TopUp.objects.filter(client=self.client_activo).count(), 3)

    # -------------------------------------------------------------------------
    # Casos de error — validaciones de negocio
    # -------------------------------------------------------------------------

    def test_monto_cero_retorna_400(self):
        """RF11: Monto de 0 retorna 400 Bad Request."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            TOPUPS_URL,
            {
                "client": self.client_activo.id,
                "amount": "0.00",
                "date": "2026-01-15",
                "channel": "APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", response.data)

    def test_monto_negativo_retorna_400(self):
        """RF11: Monto negativo retorna 400 Bad Request."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            TOPUPS_URL,
            {
                "client": self.client_activo.id,
                "amount": "-1000.00",
                "date": "2026-01-15",
                "channel": "APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", response.data)

    def test_fecha_futura_retorna_400(self):
        """RF11: Fecha futura retorna 400 Bad Request."""
        self.client.force_authenticate(user=self.user)
        fecha_futura = datetime.date.today() + datetime.timedelta(days=5)
        response = self.client.post(
            TOPUPS_URL,
            {
                "client": self.client_activo.id,
                "amount": "20000.00",
                "date": fecha_futura.isoformat(),
                "channel": "APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", response.data)

    def test_cliente_inactivo_retorna_400(self):
        """RF11: Cliente INACTIVE retorna 400 Bad Request."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            TOPUPS_URL,
            {
                "client": self.client_inactivo.id,
                "amount": "20000.00",
                "date": "2026-01-15",
                "channel": "APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("client", response.data)

    def test_cliente_migrado_retorna_400(self):
        """RF11: Cliente MIGRATED retorna 400 Bad Request."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            TOPUPS_URL,
            {
                "client": self.client_migrado.id,
                "amount": "20000.00",
                "date": "2026-01-15",
                "channel": "APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("client", response.data)

    def test_cliente_inexistente_retorna_400(self):
        """RF11: ID de cliente que no existe retorna 400 Bad Request."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            TOPUPS_URL,
            {
                "client": 99999,
                "amount": "20000.00",
                "date": "2026-01-15",
                "channel": "APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("client", response.data)
