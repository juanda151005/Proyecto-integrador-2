"""
RF12 — Cálculo de gasto promedio mensual.

CP 1.1 (Unit): Recálculo correcto del gasto promedio al incorporar una nueva
               recarga al historial existente.
CP 1.2 (Unit): Primera recarga de un cliente con historial vacío — el sistema
               calcula el promedio sin errores por división por cero.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase

from apps.analytics.models import TopUp
from apps.analytics.services import EligibilityEngine
from apps.core_business.models import Client
from apps.users.models import CustomUser


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_analyst(username="analista_rf12", email="analista_rf12@test.com"):
    user = CustomUser.objects.create_user(
        username=username,
        email=email,
        password="Pass1234!",
        role=CustomUser.Role.ANALYST,
    )
    group, _ = Group.objects.get_or_create(name="Analista")
    user.groups.add(group)
    return user


def _make_client(phone, document=None, average_spending=Decimal("0.00")):
    return Client.objects.create(
        phone_number=phone,
        full_name="Cliente RF12 Test",
        document_number=document or f"DOC-RF12-{phone}",
        email=f"{phone}@rf12test.com",
        activation_date=date(2025, 1, 1),
        current_plan=Client.PlanChoices.PREPAGO_BASIC,
        status=Client.StatusChoices.ACTIVE,
        average_spending=average_spending,
    )


def _make_topup(client, amount, topup_date):
    return TopUp.objects.create(
        client=client,
        amount=Decimal(str(amount)),
        date=topup_date,
        channel=TopUp.ChannelChoices.ONLINE,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CP 1.1 — Recálculo de gasto promedio tras nueva recarga
# ══════════════════════════════════════════════════════════════════════════════


class RF12CP11RecalculoTraNuevaRecargaTest(TestCase):
    """
    CP 1.1 — Recálculo de gasto promedio tras nueva recarga.

    Dado que un cliente ya tiene un historial de recargas registrado,
    cuando se registra una nueva recarga,
    entonces el sistema recalcula automáticamente el gasto promedio mensual
    incluyendo el nuevo valor.

    Tipo: Prueba Unitaria sobre la lógica matemática de EligibilityEngine.
    """

    def setUp(self):
        self.cliente = _make_client("3120000001")

        # Historial previo: 3 recargas en enero 2025 (total mes: $90_000)
        _make_topup(self.cliente, 30_000, date(2025, 1, 5))
        _make_topup(self.cliente, 30_000, date(2025, 1, 15))
        _make_topup(self.cliente, 30_000, date(2025, 1, 25))

        # Estado inicial del promedio (1 mes con $90_000 → promedio $90_000)
        average_inicial, _, _ = EligibilityEngine.calculate_average_spending(self.cliente)
        self.promedio_inicial = average_inicial

    def test_promedio_inicial_correcto_antes_de_nueva_recarga(self):
        """El gasto promedio base (1 mes, $90.000) es correcto."""
        self.assertEqual(self.promedio_inicial, Decimal("90000.00"))

    def test_nueva_recarga_en_mes_diferente_modifica_promedio(self):
        """
        Al agregar una recarga en un mes distinto, el promedio cambia:
        mes1=$90_000, mes2=$60_000 → promedio=(90_000+60_000)/2=$75_000.
        """
        _make_topup(self.cliente, 60_000, date(2025, 2, 10))

        average_nuevo, _, meses = EligibilityEngine.calculate_average_spending(self.cliente)

        self.assertEqual(meses, 2)
        self.assertEqual(average_nuevo, Decimal("75000.00"))

    def test_nueva_recarga_en_mismo_mes_acumula_al_mes(self):
        """
        Una recarga adicional en el mismo mes se suma al total de ese mes
        sin crear un nuevo período → promedio = $120_000 / 1 mes.
        """
        _make_topup(self.cliente, 30_000, date(2025, 1, 28))

        average_nuevo, total_topups, meses = EligibilityEngine.calculate_average_spending(
            self.cliente
        )

        self.assertEqual(meses, 1)
        self.assertEqual(average_nuevo, Decimal("120000.00"))
        self.assertEqual(total_topups, 4)

    def test_promedio_actualizado_refleja_historialo_completo(self):
        """
        Con 2 meses: enero=$90_000 y febrero=$60_000,
        el promedio = $75_000 (no el valor de un solo mes).
        """
        _make_topup(self.cliente, 60_000, date(2025, 2, 10))

        average, _, _ = EligibilityEngine.calculate_average_spending(self.cliente)

        self.assertNotEqual(average, self.promedio_inicial)
        self.assertEqual(average, Decimal("75000.00"))

    def test_total_recargas_se_actualiza_despues_de_nueva_recarga(self):
        """El conteo total de recargas aumenta tras agregar una nueva."""
        _, total_antes, _ = EligibilityEngine.calculate_average_spending(self.cliente)
        _make_topup(self.cliente, 20_000, date(2025, 3, 5))
        _, total_despues, _ = EligibilityEngine.calculate_average_spending(self.cliente)

        self.assertEqual(total_antes, 3)
        self.assertEqual(total_despues, 4)

    def test_signal_post_save_actualiza_campo_average_spending_en_bd(self):
        """
        La señal post_save de TopUp actualiza automáticamente
        el campo average_spending del cliente en la base de datos.
        """
        _make_topup(self.cliente, 60_000, date(2025, 2, 10))

        self.cliente.refresh_from_db()

        # Con mes1=$90_000 y mes2=$60_000, promedio esperado=$75_000
        self.assertEqual(self.cliente.average_spending, Decimal("75000.00"))


# ══════════════════════════════════════════════════════════════════════════════
# CP 1.2 — Primera recarga con historial vacío (sin división por cero)
# ══════════════════════════════════════════════════════════════════════════════


class RF12CP12PrimeraRecargaHistorialVacioTest(TestCase):
    """
    CP 1.2 — Cálculo de gasto promedio con primera recarga (historial vacío).

    Dado que un cliente no tiene recargas previas registradas,
    cuando se registra su primera recarga,
    entonces el sistema calcula el gasto promedio tomando ese único valor como base,
    sin generar errores por división por cero ni historial vacío.

    Tipo: Prueba Unitaria sobre la lógica matemática de EligibilityEngine.
    """

    def setUp(self):
        self.cliente = _make_client("3120000002")
        # Sin recargas previas → historial completamente vacío

    def test_calculate_average_con_historial_vacio_devuelve_cero(self):
        """
        Sin recargas, el promedio debe ser $0, sin lanzar excepciones
        (especialmente sin ZeroDivisionError).
        """
        average, total, meses = EligibilityEngine.calculate_average_spending(self.cliente)

        self.assertEqual(average, Decimal("0.00"))
        self.assertEqual(total, 0)
        self.assertEqual(meses, 0)

    def test_no_lanza_zero_division_error_con_historial_vacio(self):
        """La lógica matemática no lanza ZeroDivisionError con historial vacío."""
        try:
            EligibilityEngine.calculate_average_spending(self.cliente)
        except ZeroDivisionError:
            self.fail(
                "calculate_average_spending lanzó ZeroDivisionError con historial vacío."
            )

    def test_primera_recarga_calcula_promedio_igual_al_monto(self):
        """
        Con exactamente una recarga, el promedio mensual debe ser igual
        al monto de esa única recarga (1 mes con ese valor).
        """
        monto = Decimal("45000.00")
        _make_topup(self.cliente, monto, date(2025, 3, 15))

        average, total, meses = EligibilityEngine.calculate_average_spending(self.cliente)

        self.assertEqual(average, monto)
        self.assertEqual(total, 1)
        self.assertEqual(meses, 1)

    def test_primera_recarga_no_lanza_excepcion(self):
        """Registrar la primera recarga no provoca ninguna excepción."""
        try:
            _make_topup(self.cliente, 50_000, date(2025, 4, 1))
            EligibilityEngine.calculate_average_spending(self.cliente)
        except Exception as exc:
            self.fail(
                f"Se lanzó excepción inesperada al calcular promedio con primera recarga: {exc}"
            )

    def test_signal_actualiza_campo_average_spending_tras_primera_recarga(self):
        """
        La señal post_save de TopUp persiste el promedio en la BD
        incluso para la primera recarga del cliente.
        """
        monto = Decimal("35000.00")
        _make_topup(self.cliente, monto, date(2025, 5, 20))

        self.cliente.refresh_from_db()

        self.assertEqual(self.cliente.average_spending, monto)
        self.assertNotEqual(self.cliente.average_spending, Decimal("0.00"))
