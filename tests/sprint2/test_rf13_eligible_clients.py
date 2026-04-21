"""
RF13 — Identificación de clientes elegibles para migración a postpago.

CP 1.1 (Unit): El motor de reglas asigna el estado "Elegible" únicamente
               a clientes con antigüedad ≥ 60 días desde su activation_date.
CP 1.2 (Unit): El motor de reglas NO marca como elegible a un cliente con
               antigüedad < 60 días desde su activation_date.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from apps.analytics.services import EligibilityEngine
from apps.core_business.models import Client


TODAY = date.today()
DATE_61_DAYS_AGO = TODAY - timedelta(days=61)
DATE_60_DAYS_AGO = TODAY - timedelta(days=60)
DATE_59_DAYS_AGO = TODAY - timedelta(days=59)
DATE_1_DAY_AGO = TODAY - timedelta(days=1)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_client(phone, activation_date, document=None):
    return Client.objects.create(
        phone_number=phone,
        full_name="Cliente RF13 Test",
        document_number=document or f"DOC-RF13-{phone}",
        email=f"{phone}@rf13test.com",
        activation_date=activation_date,
        current_plan=Client.PlanChoices.PREPAGO_PLUS,
        status=Client.StatusChoices.ACTIVE,
        average_spending=Decimal("0.00"),
        is_eligible=False,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CP 1.1 — Cliente marcado como elegible al superar antigüedad mínima
# ══════════════════════════════════════════════════════════════════════════════

class RF13CP11ClienteMarcadoElegibleTest(TestCase):
    """
    CP 1.1 — El motor de reglas asigna estado "Elegible" cuando el cliente
    lleva ≥ 60 días con la línea activa (activation_date).

    Dado que el motor tiene configurado MIN_SENIORITY_DAYS=60,
    cuando se evalúa un cliente con antigüedad ≥ 60 días,
    entonces el sistema marca el campo is_eligible=True.

    Tipo: Prueba Unitaria.
    """

    def setUp(self):
        # Cliente con 61 días de antigüedad (supera el mínimo de 60)
        self.cliente = _make_client("3130000001", DATE_61_DAYS_AGO)

    def test_cliente_con_antiguedad_suficiente_es_marcado_elegible(self):
        """El motor retorna is_eligible=True cuando la antigüedad es ≥ 60 días."""
        resultado = EligibilityEngine.evaluate_client(self.cliente)
        self.assertTrue(resultado["is_eligible"])

    def test_campo_is_eligible_persiste_en_bd_como_true(self):
        """Después de evaluate_client, el campo is_eligible del cliente en BD es True."""
        EligibilityEngine.evaluate_client(self.cliente)
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.is_eligible)

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

    def test_antiguedad_exactamente_60_dias_marca_elegible(self):
        """
        Un cliente con antigüedad EXACTAMENTE igual a 60 días SÍ debe ser
        elegible (criterio >=, no solo >).
        """
        cliente_justo = _make_client("3130000002", DATE_60_DAYS_AGO, document="DOC-JUSTO")
        resultado = EligibilityEngine.evaluate_client(cliente_justo)
        self.assertTrue(resultado["is_eligible"])

    def test_razon_menciona_antiguedad_suficiente(self):
        """La razón del resultado menciona la antigüedad cuando el cliente es elegible."""
        resultado = EligibilityEngine.evaluate_client(self.cliente)
        self.assertIn("días", resultado["reason"])

    def test_evaluate_all_clients_incluye_cliente_elegible(self):
        """
        evaluate_all_clients retorna el cliente elegible con is_eligible=True.
        """
        resultados = EligibilityEngine.evaluate_all_clients()
        resultado_cliente = next(
            (r for r in resultados if r["client_id"] == self.cliente.pk), None
        )
        self.assertIsNotNone(resultado_cliente)
        self.assertTrue(resultado_cliente["is_eligible"])


# ══════════════════════════════════════════════════════════════════════════════
# CP 1.2 — Cliente NO elegible por antigüedad insuficiente
# ══════════════════════════════════════════════════════════════════════════════

class RF13CP12ClienteNoElegibleAntiguedadInsuficiente(TestCase):
    """
    CP 1.2 — El motor NO marca como elegible a un cliente que lleva
    menos de 60 días con la línea activa.

    Tipo: Prueba Unitaria.
    """

    def test_cliente_con_59_dias_no_es_elegible(self):
        """Cliente con 59 días de antigüedad → NO debe ser elegible."""
        cliente = _make_client("3130000003", DATE_59_DAYS_AGO, document="DOC-59")
        resultado = EligibilityEngine.evaluate_client(cliente)
        self.assertFalse(resultado["is_eligible"])

    def test_cliente_con_1_dia_no_es_elegible(self):
        """Cliente recién activado (1 día de antigüedad) → NO debe ser elegible."""
        cliente = _make_client("3130000004", DATE_1_DAY_AGO, document="DOC-1DIA")
        resultado = EligibilityEngine.evaluate_client(cliente)
        self.assertFalse(resultado["is_eligible"])

    def test_cliente_activado_hoy_no_es_elegible(self):
        """Un cliente activado hoy (0 días de antigüedad) no puede ser elegible."""
        cliente = _make_client("3130000005", TODAY, document="DOC-HOY")
        resultado = EligibilityEngine.evaluate_client(cliente)
        self.assertFalse(resultado["is_eligible"])

    def test_campo_is_eligible_permanece_false_tras_evaluacion(self):
        """El campo is_eligible en BD se persiste como False cuando no se cumple antigüedad."""
        cliente = _make_client("3130000006", DATE_59_DAYS_AGO, document="DOC-PARTIAL")
        EligibilityEngine.evaluate_client(cliente)
        cliente.refresh_from_db()
        self.assertFalse(cliente.is_eligible)

    def test_razon_menciona_antiguedad_insuficiente(self):
        """
        Cuando el cliente no cumple la antigüedad mínima, la razón
        del resultado debe mencionarlo explícitamente.
        """
        cliente = _make_client("3130000007", DATE_59_DAYS_AGO, document="DOC-RAZON")
        resultado = EligibilityEngine.evaluate_client(cliente)
        self.assertFalse(resultado["is_eligible"])
        self.assertIn("días", resultado["reason"])

    def test_evaluate_all_clients_no_incluye_clientes_no_elegibles(self):
        """
        evaluate_all_clients procesa todos los activos; los que no cumplen
        la antigüedad aparecen en los resultados con is_eligible=False.
        """
        cliente_no_elegible = _make_client(
            "3130000008", DATE_59_DAYS_AGO, document="DOC-NOELIG"
        )
        resultados = EligibilityEngine.evaluate_all_clients()
        resultado_cliente = next(
            (r for r in resultados if r["client_id"] == cliente_no_elegible.pk), None
        )
        self.assertIsNotNone(resultado_cliente)
        self.assertFalse(resultado_cliente["is_eligible"])
