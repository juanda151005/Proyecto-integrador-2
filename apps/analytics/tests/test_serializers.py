"""
Tests de serializer para RF11 - Registro de recargas.
Verifica las validaciones de negocio del TopUpSerializer.
"""

import datetime

from django.test import TestCase

from apps.core_business.models import Client

from ..serializers import TopUpSerializer


def make_client(phone="3001234567", client_status=Client.StatusChoices.ACTIVE):
    return Client.objects.create(
        phone_number=phone,
        full_name="Cliente Test",
        document_number=f"DOC{phone}",
        activation_date=datetime.date(2025, 1, 1),
        current_plan=Client.PlanChoices.PREPAGO_BASIC,
        status=client_status,
    )


class TopUpSerializerValidationTest(TestCase):
    """Pruebas de validacion del TopUpSerializer."""

    def setUp(self):
        self.client_activo = make_client(phone="3001111111")
        self.client_inactivo = make_client(
            phone="3002222222",
            client_status=Client.StatusChoices.INACTIVE,
        )
        self.client_migrado = make_client(
            phone="3003333333",
            client_status=Client.StatusChoices.MIGRATED,
        )

    def _serializer(self, data):
        return TopUpSerializer(data=data)

    def test_datos_validos_pasan_validacion(self):
        """RF11: Datos correctos pasan todas las validaciones."""
        s = self._serializer(
            {
                "client": self.client_activo.id,
                "amount": "20000.00",
                "date": "2026-01-15",
                "channel": "APP",
            }
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_monto_cero_es_rechazado(self):
        """RF11: Un monto de 0 debe ser rechazado."""
        s = self._serializer(
            {
                "client": self.client_activo.id,
                "amount": "0.00",
                "date": "2026-01-15",
                "channel": "APP",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("amount", s.errors)

    def test_monto_negativo_es_rechazado(self):
        """RF11: Un monto negativo debe ser rechazado."""
        s = self._serializer(
            {
                "client": self.client_activo.id,
                "amount": "-5000.00",
                "date": "2026-01-15",
                "channel": "APP",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("amount", s.errors)

    def test_fecha_futura_es_rechazada(self):
        """RF11: Una fecha futura debe ser rechazada."""
        fecha_futura = datetime.date.today() + datetime.timedelta(days=10)
        s = self._serializer(
            {
                "client": self.client_activo.id,
                "amount": "20000.00",
                "date": fecha_futura.isoformat(),
                "channel": "APP",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("date", s.errors)

    def test_fecha_hoy_es_valida(self):
        """RF11: La fecha de hoy debe ser aceptada."""
        s = self._serializer(
            {
                "client": self.client_activo.id,
                "amount": "20000.00",
                "date": datetime.date.today().isoformat(),
                "channel": "APP",
            }
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_cliente_inactivo_es_rechazado(self):
        """RF11: No se puede registrar recarga para cliente INACTIVE."""
        s = self._serializer(
            {
                "client": self.client_inactivo.id,
                "amount": "20000.00",
                "date": "2026-01-15",
                "channel": "APP",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("client", s.errors)

    def test_cliente_migrado_es_rechazado(self):
        """RF11: No se puede registrar recarga para cliente MIGRATED."""
        s = self._serializer(
            {
                "client": self.client_migrado.id,
                "amount": "20000.00",
                "date": "2026-01-15",
                "channel": "APP",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("client", s.errors)

    def test_channel_invalido_es_rechazado(self):
        """RF11: Un canal fuera de los choices definidos es rechazado."""
        s = self._serializer(
            {
                "client": self.client_activo.id,
                "amount": "20000.00",
                "date": "2026-01-15",
                "channel": "INVALIDO",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("channel", s.errors)

    def test_todos_los_channels_validos_son_aceptados(self):
        """RF11: ONLINE, STORE, ATM, APP son canales validos."""
        for canal in ["ONLINE", "STORE", "ATM", "APP"]:
            s = self._serializer(
                {
                    "client": self.client_activo.id,
                    "amount": "10000.00",
                    "date": "2026-01-15",
                    "channel": canal,
                }
            )
            self.assertTrue(s.is_valid(), f"Canal {canal} fallo: {s.errors}")
