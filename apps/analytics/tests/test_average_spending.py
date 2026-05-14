"""
Tests del cálculo automático de gasto promedio — RF12.

Criterios de aceptación:
- CP 1.1: Al registrar una nueva recarga, el sistema recalcula
  automáticamente el gasto promedio incluyendo el nuevo valor.
- CP 1.2: Al registrar la primera recarga, el sistema calcula
  el promedio sin errores por división o historial vacío.
"""

import datetime
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.core_business.models import Client
from apps.users.models import CustomUser

from ..models import TopUp
from ..services import EligibilityEngine

# =============================================================================
# Helpers
# =============================================================================


def make_client(phone="3001234567", client_status=Client.StatusChoices.ACTIVE):
    """Crea un cliente de prueba."""
    return Client.objects.create(
        phone_number=phone,
        full_name="Cliente Test",
        document_number=f"DOC{phone}",
        activation_date=datetime.date(2025, 1, 1),
        current_plan=Client.PlanChoices.PREPAGO_BASIC,
        status=client_status,
    )


def make_user(username="analyst_rf12", role=CustomUser.Role.ANALYST):
    """Crea un usuario de prueba."""
    return CustomUser.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="TestPass123*",
        role=role,
    )


TOPUPS_URL = "/api/v1/analytics/topups/"


# =============================================================================
# Tests — Lógica matemática de calculate_average_spending
# =============================================================================


class AverageSpendingCalculationTest(TestCase):
    """Verifica la lógica matemática del cálculo de gasto promedio."""

    def setUp(self):
        self.client_obj = make_client(phone="3007771111")

    def test_promedio_con_un_solo_mes(self):
        """RF12: Con recargas en un solo mes, el promedio es la suma de ese mes."""
        TopUp.objects.create(
            client=self.client_obj,
            amount=Decimal("20000.00"),
            date=datetime.date(2026, 1, 10),
            channel=TopUp.ChannelChoices.APP,
        )
        TopUp.objects.create(
            client=self.client_obj,
            amount=Decimal("30000.00"),
            date=datetime.date(2026, 1, 20),
            channel=TopUp.ChannelChoices.APP,
        )

        average, total_topups, months = EligibilityEngine.calculate_average_spending(
            self.client_obj
        )

        # Un solo mes: promedio = suma total / 1
        self.assertEqual(average, Decimal("50000.00"))
        self.assertEqual(total_topups, 2)
        self.assertEqual(months, 1)

    def test_promedio_con_multiples_meses(self):
        """RF12: El promedio se calcula agrupando por mes."""
        TopUp.objects.create(
            client=self.client_obj,
            amount=Decimal("30000.00"),
            date=datetime.date(2026, 1, 15),
            channel=TopUp.ChannelChoices.APP,
        )
        TopUp.objects.create(
            client=self.client_obj,
            amount=Decimal("60000.00"),
            date=datetime.date(2026, 2, 15),
            channel=TopUp.ChannelChoices.APP,
        )

        average, total_topups, months = EligibilityEngine.calculate_average_spending(
            self.client_obj
        )

        # (30000 + 60000) / 2 meses = 45000
        self.assertEqual(average, Decimal("45000.00"))
        self.assertEqual(months, 2)

    def test_promedio_sin_recargas_retorna_cero(self):
        """RF12 CP 1.2: Sin recargas, retorna 0 sin errores de división."""
        average, total_topups, months = EligibilityEngine.calculate_average_spending(
            self.client_obj
        )

        self.assertEqual(average, Decimal("0.00"))
        self.assertEqual(total_topups, 0)
        self.assertEqual(months, 0)


# =============================================================================
# Tests — CP 1.1: Recálculo automático tras nueva recarga (signal)
# =============================================================================


class AutoRecalculateOnTopUpTest(TestCase):
    """
    CP 1.1 — Dado que un cliente ya tiene un historial de recargas,
    cuando se registra una nueva recarga, entonces el sistema recalcula
    automáticamente el gasto promedio mensual.
    """

    def setUp(self):
        self.client_obj = make_client(phone="3007772222")
        # Recarga previa en enero
        TopUp.objects.create(
            client=self.client_obj,
            amount=Decimal("40000.00"),
            date=datetime.date(2026, 1, 15),
            channel=TopUp.ChannelChoices.APP,
        )

    def test_promedio_se_recalcula_al_crear_topup(self):
        """RF12 CP 1.1: El gasto promedio se actualiza tras nueva recarga."""
        # Antes de la nueva recarga: promedio = 40000 (1 mes)
        self.client_obj.refresh_from_db()
        promedio_antes = self.client_obj.average_spending

        # Registrar nueva recarga en febrero (dispara la signal)
        TopUp.objects.create(
            client=self.client_obj,
            amount=Decimal("60000.00"),
            date=datetime.date(2026, 2, 15),
            channel=TopUp.ChannelChoices.APP,
        )

        # Después: promedio = (40000 + 60000) / 2 = 50000
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.average_spending, Decimal("50000.00"))

    def test_promedio_se_recalcula_via_endpoint(self):
        """RF12 CP 1.1: POST /api/v1/analytics/topups/ dispara recálculo."""
        api_client = APIClient()
        user = make_user()
        api_client.force_authenticate(user=user)

        # Crear recarga vía endpoint
        response = api_client.post(
            TOPUPS_URL,
            {
                "client": self.client_obj.id,
                "amount": "60000.00",
                "date": "2026-02-15",
                "channel": "APP",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verificar que el promedio se actualizó automáticamente
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.average_spending, Decimal("50000.00"))

    def test_promedio_incluye_nueva_recarga_mismo_mes(self):
        """RF12 CP 1.1: Una recarga en el mismo mes actualiza el promedio."""
        # Segunda recarga en enero
        TopUp.objects.create(
            client=self.client_obj,
            amount=Decimal("20000.00"),
            date=datetime.date(2026, 1, 20),
            channel=TopUp.ChannelChoices.APP,
        )

        # Solo 1 mes, promedio = (40000 + 20000) / 1 = 60000
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.average_spending, Decimal("60000.00"))


# =============================================================================
# Tests — CP 1.2: Primera recarga sin errores
# =============================================================================


class FirstTopUpAverageTest(TestCase):
    """
    CP 1.2 — Dado que un cliente no tiene recargas previas,
    cuando se registra su primera recarga, entonces el sistema
    calcula el gasto promedio tomando ese único valor como base,
    sin generar errores por división o historial vacío.
    """

    def setUp(self):
        self.client_obj = make_client(phone="3007773333")

    def test_primera_recarga_calcula_promedio_sin_error(self):
        """RF12 CP 1.2: La primera recarga no genera errores de división."""
        # Verificar que no hay recargas previas
        self.assertEqual(TopUp.objects.filter(client=self.client_obj).count(), 0)
        self.assertEqual(self.client_obj.average_spending, Decimal("0"))

        # Registrar primera recarga (dispara la signal)
        TopUp.objects.create(
            client=self.client_obj,
            amount=Decimal("35000.00"),
            date=datetime.date(2026, 1, 15),
            channel=TopUp.ChannelChoices.APP,
        )

        # El promedio debe ser exactamente el monto de la primera recarga
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.average_spending, Decimal("35000.00"))

    def test_primera_recarga_via_endpoint_sin_error(self):
        """RF12 CP 1.2: Primera recarga vía POST no genera errores."""
        api_client = APIClient()
        user = make_user(username="analyst_cp12")
        api_client.force_authenticate(user=user)

        response = api_client.post(
            TOPUPS_URL,
            {
                "client": self.client_obj.id,
                "amount": "25000.00",
                "date": "2026-03-10",
                "channel": "STORE",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Promedio = 25000 (único valor)
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.average_spending, Decimal("25000.00"))


# =============================================================================
# Tests — Management command: recalculate_spending
# =============================================================================


class RecalculateSpendingCommandTest(TestCase):
    """Tests para el management command de recálculo masivo."""

    def setUp(self):
        self.client_obj = make_client(phone="3007774444")
        TopUp.objects.create(
            client=self.client_obj,
            amount=Decimal("50000.00"),
            date=datetime.date(2026, 1, 15),
            channel=TopUp.ChannelChoices.APP,
        )
        TopUp.objects.create(
            client=self.client_obj,
            amount=Decimal("70000.00"),
            date=datetime.date(2026, 2, 15),
            channel=TopUp.ChannelChoices.APP,
        )

    def test_command_recalcula_todos_los_activos(self):
        """RF12: El command recalcula el promedio de todos los clientes activos."""
        # Forzar promedio incorrecto para verificar que se recalcula
        self.client_obj.average_spending = Decimal("0.00")
        self.client_obj.save(update_fields=["average_spending"])

        out = StringIO()
        call_command("recalculate_spending", stdout=out)

        self.client_obj.refresh_from_db()
        # (50000 + 70000) / 2 meses = 60000
        self.assertEqual(self.client_obj.average_spending, Decimal("60000.00"))
        self.assertIn("completado", out.getvalue().lower())

    def test_command_recalcula_cliente_especifico(self):
        """RF12: El command acepta --client-id para recalcular uno solo."""
        self.client_obj.average_spending = Decimal("0.00")
        self.client_obj.save(update_fields=["average_spending"])

        out = StringIO()
        call_command(
            "recalculate_spending",
            client_id=self.client_obj.id,
            stdout=out,
        )

        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.average_spending, Decimal("60000.00"))

    def test_command_ignora_clientes_inactivos(self):
        """RF12: El command no recalcula clientes inactivos."""
        inactive = make_client(
            phone="3007775555", client_status=Client.StatusChoices.INACTIVE
        )
        TopUp.objects.create(
            client=inactive,
            amount=Decimal("80000.00"),
            date=datetime.date(2026, 1, 15),
            channel=TopUp.ChannelChoices.APP,
        )
        inactive.average_spending = Decimal("0.00")
        inactive.save(update_fields=["average_spending"])

        call_command("recalculate_spending", stdout=StringIO())

        inactive.refresh_from_db()
        # No se recalculó porque es inactivo
        self.assertEqual(inactive.average_spending, Decimal("0.00"))

    def test_command_sin_clientes_activos(self):
        """RF12: El command maneja gracefully cuando no hay clientes activos."""
        Client.objects.all().delete()

        out = StringIO()
        call_command("recalculate_spending", stdout=out)

        self.assertIn("no hay clientes activos", out.getvalue().lower())

    def test_command_cliente_inexistente(self):
        """RF12: El command muestra error si el --client-id no existe."""
        err = StringIO()
        call_command("recalculate_spending", client_id=99999, stderr=err)

        self.assertIn("no encontrado", err.getvalue().lower())
