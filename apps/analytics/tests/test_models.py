"""
Tests de modelo para RF11 - Registro de recargas.
Verifica que el modelo TopUp persiste y se comporta correctamente.
"""

import datetime

from django.test import TestCase

from apps.core_business.models import Client

from ..models import TopUp

BASE_DATE = datetime.date(2026, 1, 15)


def make_client(phone="3001234567"):
    return Client.objects.create(
        phone_number=phone,
        full_name="Cliente Test",
        document_number=f"DOC{phone}",
        activation_date=datetime.date(2025, 1, 1),
        current_plan=Client.PlanChoices.PREPAGO_BASIC,
        status=Client.StatusChoices.ACTIVE,
    )


class TopUpModelTest(TestCase):
    """Pruebas unitarias sobre el modelo TopUp."""

    def setUp(self):
        self.client_obj = make_client()

    def test_crear_topup_guarda_correctamente(self):
        """RF11: Un TopUp creado persiste con los campos correctos."""
        topup = TopUp.objects.create(
            client=self.client_obj,
            amount=20000,
            date=BASE_DATE,
            channel=TopUp.ChannelChoices.APP,
        )
        self.assertEqual(TopUp.objects.count(), 1)
        self.assertEqual(topup.client, self.client_obj)
        self.assertEqual(topup.amount, 20000)
        self.assertEqual(topup.date, BASE_DATE)
        self.assertEqual(topup.channel, "APP")

    def test_str_representation(self):
        """RF11: __str__ incluye el telefono del cliente y el monto."""
        topup = TopUp.objects.create(
            client=self.client_obj,
            amount=15000,
            date=BASE_DATE,
            channel=TopUp.ChannelChoices.STORE,
        )
        self.assertIn("3001234567", str(topup))
        self.assertIn("15000", str(topup))

    def test_topup_vinculado_al_cliente_correcto(self):
        """RF11: La FK al cliente queda correctamente registrada."""
        topup = TopUp.objects.create(
            client=self.client_obj,
            amount=10000,
            date=BASE_DATE,
            channel=TopUp.ChannelChoices.ONLINE,
        )
        self.assertEqual(topup.client.phone_number, "3001234567")

    def test_ordering_por_fecha_descendente(self):
        """RF11: Los registros se ordenan por fecha descendente por defecto."""
        TopUp.objects.create(
            client=self.client_obj,
            amount=10000,
            date=datetime.date(2026, 1, 1),
            channel=TopUp.ChannelChoices.APP,
        )
        TopUp.objects.create(
            client=self.client_obj,
            amount=20000,
            date=datetime.date(2026, 3, 1),
            channel=TopUp.ChannelChoices.APP,
        )
        primero = TopUp.objects.first()
        self.assertEqual(primero.date, datetime.date(2026, 3, 1))

    def test_created_at_se_genera_automaticamente(self):
        """RF11: created_at se asigna automaticamente al crear el registro."""
        topup = TopUp.objects.create(
            client=self.client_obj,
            amount=5000,
            date=BASE_DATE,
            channel=TopUp.ChannelChoices.ATM,
        )
        self.assertIsNotNone(topup.created_at)
