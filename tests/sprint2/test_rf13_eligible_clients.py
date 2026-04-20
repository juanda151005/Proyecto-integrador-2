"""
RF13 — Identificación de clientes elegibles para migración a postpago.

CP 1.1 (Unit): El motor de reglas asigna el estado "Elegible" únicamente
               a clientes que superan todos los umbrales configurados.
CP 1.2 (Unit): El motor de reglas NO marca como elegible a un cliente que
               cumple solo uno de los criterios configurados.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase

from apps.analytics.models import TopUp
from apps.analytics.services import EligibilityEngine
from apps.core_business.models import Client
from apps.management.models import BusinessRule
from apps.users.models import CustomUser


# ── Constantes de umbral para los tests ────────────────────────────────────────
UMBRAL_GASTO = Decimal("50000.00")   # MIN_AVERAGE_SPENDING
UMBRAL_FRECUENCIA = 3                # MIN_RECHARGE_FREQUENCY


# ── Helpers ────────────────────────────────────────────────────────────────────

def _setup_business_rules():
    """Crea las reglas de negocio con umbrales conocidos y predecibles."""
    BusinessRule.objects.update_or_create(
        key="MIN_AVERAGE_SPENDING",
        defaults={"value": str(UMBRAL_GASTO), "is_active": True, "description": "Test"},
    )
    BusinessRule.objects.update_or_create(
        key="MIN_RECHARGE_FREQUENCY",
        defaults={"value": str(UMBRAL_FRECUENCIA), "is_active": True, "description": "Test"},
    )


def _make_client(phone, document=None):
    return Client.objects.create(
        phone_number=phone,
        full_name="Cliente RF13 Test",
        document_number=document or f"DOC-RF13-{phone}",
        email=f"{phone}@rf13test.com",
        activation_date=date(2025, 1, 1),
        current_plan=Client.PlanChoices.PREPAGO_PLUS,
        status=Client.StatusChoices.ACTIVE,
        average_spending=Decimal("0.00"),
        is_eligible=False,
    )


def _make_topup(client, amount, topup_date):
    """Crea una recarga sin disparar la señal (para control fino del test)."""
    return TopUp.objects.create(
        client=client,
        amount=Decimal(str(amount)),
        date=topup_date,
        channel=TopUp.ChannelChoices.APP,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CP 1.1 — Cliente marcado como elegible al cumplir todos los criterios
# ══════════════════════════════════════════════════════════════════════════════


class RF13CP11ClienteMarcadoElegibleTest(TestCase):
    """
    CP 1.1 — El motor de reglas asigna estado "Elegible" cuando el cliente
    supera TODOS los umbrales configurados (gasto Y frecuencia).

    Dado q el motor tiene configurados MIN_AVERAGE_SPENDING=$50.000
    y MIN_RECHARGE_FREQUENCY=3,
    cuando se evalúa un cliente con gasto promedio >$50.000 y ≥3 recargas,
    entonces el sistema marca el campo is_eligible=True.

    Tipo: Prueba Unitaria.
    """

    def setUp(self):
        _setup_business_rules()
        # Cliente con gasto promedio ~$70.000 (supera $50.000) y 4 recargas (supera 3)
        self.cliente = _make_client("3130000001")
        # 4 recargas en meses distintos con montos que promedian ~$70.000/mes
        _make_topup(self.cliente, 70_000, date(2025, 1, 10))
        _make_topup(self.cliente, 70_000, date(2025, 2, 10))
        _make_topup(self.cliente, 70_000, date(2025, 3, 10))
        _make_topup(self.cliente, 70_000, date(2025, 4, 10))

    def test_cliente_cumple_ambos_criterios_es_marcado_elegible(self):
        """El motor retorna is_eligible=True cuando se superan ambos umbrales."""
        resultado = EligibilityEngine.evaluate_client(self.cliente)
        self.assertTrue(resultado["is_eligible"])

    def test_campo_is_eligible_persiste_en_bd_como_true(self):
        """Después de evaluate_client, el campo is_eligible del cliente en BD es True."""
        EligibilityEngine.evaluate_client(self.cliente)
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.is_eligible)

    def test_campo_average_spending_persiste_en_bd_tras_evaluacion(self):
        """El campo average_spending del cliente se actualiza en BD al evaluar."""
        EligibilityEngine.evaluate_client(self.cliente)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.average_spending, Decimal("70000.00"))

    def test_resultado_contiene_razon_descriptiva(self):
        """El dict de resultado incluye un campo 'reason' no vacío."""
        resultado = EligibilityEngine.evaluate_client(self.cliente)
        self.assertIn("reason", resultado)
        self.assertGreater(len(resultado["reason"]), 0)

    def test_resultado_contiene_datos_del_cliente(self):
        """El dict de resultado tiene los campos esperados con datos del cliente."""
        resultado = EligibilityEngine.evaluate_client(self.cliente)
        self.assertEqual(resultado["client_id"], self.cliente.pk)
        self.assertEqual(resultado["phone_number"], self.cliente.phone_number)

    def test_umbrales_exactos_marcan_elegible(self):
        """
        Un cliente con gasto promedio EXACTAMENTE igual al umbral ($50.000)
        y frecuencia EXACTAMENTE igual al mínimo (3) SÍ debe ser elegible
        (criterio >=, no solo >).
        """
        cliente_justo = _make_client("3130000002", document="DOC-JUSTO")
        # 3 recargas de $50.000 en meses distintos → promedio exacto $50.000, frecuencia=3
        _make_topup(cliente_justo, 50_000, date(2025, 1, 5))
        _make_topup(cliente_justo, 50_000, date(2025, 2, 5))
        _make_topup(cliente_justo, 50_000, date(2025, 3, 5))

        resultado = EligibilityEngine.evaluate_client(cliente_justo)
        self.assertTrue(resultado["is_eligible"])


# ══════════════════════════════════════════════════════════════════════════════
# CP 1.2 — Cliente NO elegible por cumplir solo alguno de los criterios
# ══════════════════════════════════════════════════════════════════════════════


class RF13CP12ClienteNoElegibleCriteriosParciales(TestCase):
    """
    CP 1.2 — El motor NO marca como elegible a un cliente que cumple
    únicamente uno de los dos criterios configurados.

    Tipo: Prueba Unitaria.
    """

    def setUp(self):
        _setup_business_rules()

    def test_supera_gasto_pero_no_frecuencia_no_es_elegible(self):
        """
        Cliente con gasto promedio >$50.000 pero solo 1 recarga (<3)
        → NO debe ser elegible.
        """
        cliente = _make_client("3130000003", document="DOC-NOGASTO")
        # Una sola recarga de monto alto → promedio alto, frecuencia baja
        _make_topup(cliente, 100_000, date(2025, 1, 10))

        resultado = EligibilityEngine.evaluate_client(cliente)

        self.assertFalse(resultado["is_eligible"])

    def test_supera_frecuencia_pero_no_gasto_no_es_elegible(self):
        """
        Cliente con ≥3 recargas pero gasto promedio <$50.000
        → NO debe ser elegible.
        """
        cliente = _make_client("3130000004", document="DOC-NOFREQ")
        # 5 recargas pequeñas → frecuencia alta, gasto bajo
        _make_topup(cliente, 5_000, date(2025, 1, 1))
        _make_topup(cliente, 5_000, date(2025, 2, 1))
        _make_topup(cliente, 5_000, date(2025, 3, 1))
        _make_topup(cliente, 5_000, date(2025, 4, 1))
        _make_topup(cliente, 5_000, date(2025, 5, 1))

        resultado = EligibilityEngine.evaluate_client(cliente)

        self.assertFalse(resultado["is_eligible"])

    def test_campo_is_eligible_permanece_false_tras_evaluacion_con_criterio_parcial(self):
        """El campo is_eligible en BD se persiste como False cuando no se cumplen todos los criterios."""
        cliente = _make_client("3130000005", document="DOC-PARTIAL")
        _make_topup(cliente, 5_000, date(2025, 1, 10))  # frecuencia=1, gasto=$5.000

        EligibilityEngine.evaluate_client(cliente)
        cliente.refresh_from_db()

        self.assertFalse(cliente.is_eligible)

    def test_sin_recargas_no_es_elegible(self):
        """Un cliente sin ninguna recarga no puede ser elegible."""
        cliente = _make_client("3130000006", document="DOC-NORECARGAS")

        resultado = EligibilityEngine.evaluate_client(cliente)

        self.assertFalse(resultado["is_eligible"])

    def test_razon_explica_criterio_no_cumplido_por_gasto(self):
        """
        Cuando el cliente no cumple el criterio de gasto, la razón
        del resultado debe mencionarlo explícitamente.
        """
        cliente = _make_client("3130000007", document="DOC-RAZONG")
        # Alta frecuencia, bajo gasto
        _make_topup(cliente, 5_000, date(2025, 1, 1))
        _make_topup(cliente, 5_000, date(2025, 2, 1))
        _make_topup(cliente, 5_000, date(2025, 3, 1))

        resultado = EligibilityEngine.evaluate_client(cliente)

        self.assertFalse(resultado["is_eligible"])
        # La razón debe mencionar el gasto insuficiente
        self.assertIn("Gasto", resultado["reason"])

    def test_razon_explica_criterio_no_cumplido_por_frecuencia(self):
        """
        Cuando el cliente no cumple el criterio de frecuencia, la razón
        del resultado debe mencionarlo explícitamente.
        """
        cliente = _make_client("3130000008", document="DOC-RAZONF")
        # Alto gasto, baja frecuencia (1 recarga)
        _make_topup(cliente, 100_000, date(2025, 1, 10))

        resultado = EligibilityEngine.evaluate_client(cliente)

        self.assertFalse(resultado["is_eligible"])
        # La razón debe mencionar la frecuencia insuficiente
        self.assertIn("Frecuencia", resultado["reason"])

    def test_evaluate_all_clients_no_incluye_clientes_no_elegibles(self):
        """
        evaluate_all_clients procesa todos los activos; los que no cumplen
        los criterios aparecen en los resultados con is_eligible=False.
        """
        cliente_no_elegible = _make_client("3130000009", document="DOC-NOELIG")
        _make_topup(cliente_no_elegible, 5_000, date(2025, 1, 1))

        resultados = EligibilityEngine.evaluate_all_clients()

        resultado_cliente = next(
            (r for r in resultados if r["client_id"] == cliente_no_elegible.pk), None
        )
        self.assertIsNotNone(resultado_cliente)
        self.assertFalse(resultado_cliente["is_eligible"])
