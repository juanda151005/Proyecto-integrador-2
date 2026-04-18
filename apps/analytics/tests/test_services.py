"""
Tests del motor de elegibilidad — RF13.

Criterios de aceptación:
- CP 1.1: Cliente que cumple TODOS los criterios → marcado como "Elegible".
- CP 1.2: Cliente que cumple solo ALGUNOS criterios → NO marcado como "Elegible".
"""

import datetime
from decimal import Decimal

from django.test import TestCase

from apps.core_business.models import Client
from apps.management.models import BusinessRule

from ..models import TopUp
from ..services import EligibilityEngine

# =============================================================================
# Helpers — datos reutilizables
# =============================================================================

BASE_DATE = datetime.date(2026, 1, 15)


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


def create_topups(client, amounts_by_month):
    """
    Crea recargas distribuidas por mes.

    Args:
        client: instancia de Client.
        amounts_by_month: dict {mes_int: [monto1, monto2, ...]}
            Ejemplo: {1: [20000, 15000], 2: [30000], 3: [25000, 10000]}
    """
    for month, amounts in amounts_by_month.items():
        for i, amount in enumerate(amounts):
            TopUp.objects.create(
                client=client,
                amount=Decimal(str(amount)),
                date=datetime.date(2026, month, min(1 + i, 28)),
                channel=TopUp.ChannelChoices.APP,
            )


def setup_business_rules(min_spending="50000.00", min_frequency="3"):
    """Crea o actualiza las dos BusinessRule necesarias para el motor."""
    BusinessRule.objects.update_or_create(
        key="MIN_AVERAGE_SPENDING",
        defaults={
            "value": min_spending,
            "description": "Gasto promedio mensual mínimo para elegibilidad.",
            "is_active": True,
        },
    )
    BusinessRule.objects.update_or_create(
        key="MIN_RECHARGE_FREQUENCY",
        defaults={
            "value": min_frequency,
            "description": "Cantidad mínima de recargas para elegibilidad.",
            "is_active": True,
        },
    )


# =============================================================================
# Tests — Lectura de umbrales desde BusinessRule
# =============================================================================


class EligibilityThresholdTest(TestCase):
    """Verifica que el motor lee los umbrales desde BusinessRule."""

    def test_get_threshold_lee_desde_business_rule(self):
        """RF13: El umbral de gasto se lee desde la regla configurada."""
        BusinessRule.objects.update_or_create(
            key="MIN_AVERAGE_SPENDING",
            defaults={"value": "75000.00", "is_active": True},
        )
        threshold = EligibilityEngine.get_threshold()
        self.assertEqual(threshold, Decimal("75000.00"))

    def test_get_threshold_usa_default_si_no_existe_regla(self):
        """RF13: Si no existe la regla, usa el valor por defecto."""
        BusinessRule.objects.filter(key="MIN_AVERAGE_SPENDING").delete()
        threshold = EligibilityEngine.get_threshold()
        self.assertEqual(threshold, Decimal("50000.00"))

    def test_get_threshold_ignora_regla_inactiva(self):
        """RF13: Una regla inactiva no se usa; se aplica el default."""
        BusinessRule.objects.update_or_create(
            key="MIN_AVERAGE_SPENDING",
            defaults={"value": "75000.00", "is_active": False},
        )
        threshold = EligibilityEngine.get_threshold()
        self.assertEqual(threshold, Decimal("50000.00"))

    def test_get_min_frequency_lee_desde_business_rule(self):
        """RF13: La frecuencia mínima se lee desde la regla configurada."""
        BusinessRule.objects.update_or_create(
            key="MIN_RECHARGE_FREQUENCY",
            defaults={"value": "5", "is_active": True},
        )
        freq = EligibilityEngine.get_min_frequency()
        self.assertEqual(freq, 5)

    def test_get_min_frequency_usa_default_si_no_existe_regla(self):
        """RF13: Si no existe la regla de frecuencia, usa el default (3)."""
        BusinessRule.objects.filter(key="MIN_RECHARGE_FREQUENCY").delete()
        freq = EligibilityEngine.get_min_frequency()
        self.assertEqual(freq, 3)

    def test_get_min_frequency_ignora_regla_inactiva(self):
        """RF13: Una regla de frecuencia inactiva no se usa."""
        BusinessRule.objects.update_or_create(
            key="MIN_RECHARGE_FREQUENCY",
            defaults={"value": "10", "is_active": False},
        )
        freq = EligibilityEngine.get_min_frequency()
        self.assertEqual(freq, 3)


# =============================================================================
# Tests — CP 1.1: Cliente elegible al cumplir TODOS los criterios
# =============================================================================


class EligibilityCP11Test(TestCase):
    """
    CP 1.1 — Dado que el motor tiene configurados los parámetros de
    elegibilidad, cuando el sistema evalúa un cliente cuyo gasto promedio
    y frecuencia de recarga superan AMBOS umbrales configurados, entonces
    el sistema marca automáticamente el campo de estado como 'Elegible'.
    """

    def setUp(self):
        self.client_obj = make_client(phone="3005551111")
        setup_business_rules(min_spending="50000.00", min_frequency="3")

    def test_cliente_cumple_ambos_criterios_es_elegible(self):
        """
        RF13 CP 1.1: Gasto promedio > umbral AND frecuencia > mínimo
        → is_eligible = True.
        """
        # 3 meses de recargas, 5 recargas totales, promedio alto
        create_topups(
            self.client_obj,
            {
                1: [30000, 25000],  # Enero: 55000
                2: [40000],  # Febrero: 40000
                3: [35000, 30000],  # Marzo: 65000
            },
        )
        # Promedio mensual: (55000 + 40000 + 65000) / 3 = 53333.33
        # Frecuencia: 5 recargas (>= 3)

        result = EligibilityEngine.evaluate_client(self.client_obj)

        self.assertTrue(result["is_eligible"])

        # Verificar que se persistió en la BD
        self.client_obj.refresh_from_db()
        self.assertTrue(self.client_obj.is_eligible)

    def test_campo_is_eligible_se_persiste_en_bd(self):
        """RF13 CP 1.1: El campo is_eligible se guarda en el perfil del cliente."""
        create_topups(
            self.client_obj,
            {
                1: [60000],
                2: [55000],
                3: [70000],
            },
        )
        # Promedio: 61666.67, Frecuencia: 3

        EligibilityEngine.evaluate_client(self.client_obj)

        # Leer directamente de la BD, no del objeto en memoria
        client_from_db = Client.objects.get(pk=self.client_obj.pk)
        self.assertTrue(client_from_db.is_eligible)

    def test_average_spending_se_actualiza_en_bd(self):
        """RF13: El gasto promedio calculado se guarda en el cliente."""
        create_topups(
            self.client_obj,
            {
                1: [60000],
                2: [60000],
                3: [60000],
            },
        )

        EligibilityEngine.evaluate_client(self.client_obj)

        client_from_db = Client.objects.get(pk=self.client_obj.pk)
        self.assertEqual(client_from_db.average_spending, Decimal("60000.00"))

    def test_reason_indica_cumplimiento_completo(self):
        """RF13 CP 1.1: La razón describe que cumple ambos criterios."""
        create_topups(
            self.client_obj,
            {
                1: [60000],
                2: [55000],
                3: [70000],
            },
        )

        result = EligibilityEngine.evaluate_client(self.client_obj)

        self.assertIn("supera", result["reason"].lower())


# =============================================================================
# Tests — CP 1.2: Cliente NO elegible al cumplir solo ALGUNOS criterios
# =============================================================================


class EligibilityCP12Test(TestCase):
    """
    CP 1.2 — Dado que el motor tiene configurados los parámetros de
    elegibilidad, cuando el sistema evalúa un cliente que cumple
    únicamente UNO de los dos criterios, entonces el sistema NO marca
    al cliente como 'Elegible'.
    """

    def setUp(self):
        self.client_obj = make_client(phone="3005552222")
        setup_business_rules(min_spending="50000.00", min_frequency="5")

    def test_supera_gasto_pero_no_frecuencia_no_es_elegible(self):
        """
        RF13 CP 1.2: Gasto promedio > umbral PERO frecuencia < mínimo
        → is_eligible = False.
        """
        # Solo 2 recargas (frecuencia < 5), pero gasto alto
        create_topups(
            self.client_obj,
            {
                1: [80000],
                2: [70000],
            },
        )
        # Promedio: 75000 (>= 50000) ✓
        # Frecuencia: 2 recargas (< 5) ✗

        result = EligibilityEngine.evaluate_client(self.client_obj)

        self.assertFalse(result["is_eligible"])

        self.client_obj.refresh_from_db()
        self.assertFalse(self.client_obj.is_eligible)

    def test_supera_frecuencia_pero_no_gasto_no_es_elegible(self):
        """
        RF13 CP 1.2: Frecuencia >= mínimo PERO gasto promedio < umbral
        → is_eligible = False.
        """
        # 6 recargas (frecuencia >= 5), pero montos bajos
        create_topups(
            self.client_obj,
            {
                1: [5000, 5000],
                2: [5000, 5000],
                3: [5000, 5000],
            },
        )
        # Promedio: (10000 + 10000 + 10000) / 3 = 10000 (< 50000) ✗
        # Frecuencia: 6 recargas (>= 5) ✓

        result = EligibilityEngine.evaluate_client(self.client_obj)

        self.assertFalse(result["is_eligible"])

        self.client_obj.refresh_from_db()
        self.assertFalse(self.client_obj.is_eligible)

    def test_no_cumple_ningun_criterio_no_es_elegible(self):
        """
        RF13 CP 1.2: No cumple ni gasto ni frecuencia
        → is_eligible = False.
        """
        # Solo 1 recarga de monto bajo
        create_topups(
            self.client_obj,
            {
                1: [5000],
            },
        )
        # Promedio: 5000 (< 50000) ✗
        # Frecuencia: 1 recarga (< 5) ✗

        result = EligibilityEngine.evaluate_client(self.client_obj)

        self.assertFalse(result["is_eligible"])

    def test_sin_recargas_no_es_elegible(self):
        """RF13 CP 1.2: Un cliente sin recargas no puede ser elegible."""
        result = EligibilityEngine.evaluate_client(self.client_obj)

        self.assertFalse(result["is_eligible"])
        self.assertEqual(result["average_spending"], Decimal("0.00"))

    def test_reason_indica_criterio_no_cumplido(self):
        """
        RF13 CP 1.2: La razón describe cuáles criterios no se cumplieron.
        """
        # Supera gasto, no frecuencia
        create_topups(
            self.client_obj,
            {
                1: [80000],
                2: [70000],
            },
        )

        result = EligibilityEngine.evaluate_client(self.client_obj)

        self.assertIn("frecuencia", result["reason"].lower())

    def test_reason_lista_ambos_criterios_si_ambos_fallan(self):
        """RF13 CP 1.2: Si fallan ambos criterios, la razón los menciona."""
        create_topups(
            self.client_obj,
            {
                1: [1000],
            },
        )

        result = EligibilityEngine.evaluate_client(self.client_obj)

        reason_lower = result["reason"].lower()
        self.assertIn("gasto", reason_lower)
        self.assertIn("frecuencia", reason_lower)


# =============================================================================
# Tests — Re-evaluación: un cliente puede cambiar de estado
# =============================================================================


class EligibilityReEvaluationTest(TestCase):
    """Verifica que la elegibilidad se recalcula correctamente."""

    def setUp(self):
        self.client_obj = make_client(phone="3005553333")
        setup_business_rules(min_spending="50000.00", min_frequency="3")

    def test_cliente_pasa_de_no_elegible_a_elegible(self):
        """RF13: Al agregar más recargas, un cliente puede volverse elegible."""
        # Inicialmente no elegible (1 recarga, bajo gasto)
        create_topups(self.client_obj, {1: [10000]})
        result = EligibilityEngine.evaluate_client(self.client_obj)
        self.assertFalse(result["is_eligible"])

        # Agregar más recargas con montos altos que compensen enero
        # Total: 10000 + 80000 + 80000 + 80000 = 250000 en 4 meses
        # Promedio: 250000 / 4 = 62500 (>= 50000) ✓
        # Frecuencia: 4 recargas (>= 3) ✓
        create_topups(
            self.client_obj,
            {
                2: [80000],
                3: [80000],
                4: [80000],
            },
        )
        result = EligibilityEngine.evaluate_client(self.client_obj)
        self.assertTrue(result["is_eligible"])

    def test_evaluate_all_evalua_solo_clientes_activos(self):
        """RF13: evaluate_all_clients solo procesa clientes ACTIVE."""
        make_client(phone="3006661111", client_status=Client.StatusChoices.INACTIVE)
        make_client(phone="3006662222", client_status=Client.StatusChoices.MIGRATED)
        active_client = make_client(phone="3006663333")

        create_topups(
            active_client,
            {1: [60000], 2: [60000], 3: [60000]},
        )

        results = EligibilityEngine.evaluate_all_clients()

        # Solo debe evaluar clientes activos (self.client_obj + active_client)
        evaluated_ids = [r["client_id"] for r in results]
        self.assertIn(self.client_obj.id, evaluated_ids)
        self.assertIn(active_client.id, evaluated_ids)
        self.assertEqual(len(results), 2)


# =============================================================================
# Tests — Configuración dinámica de umbrales
# =============================================================================


class EligibilityDynamicConfigTest(TestCase):
    """
    Verifica que cambiar los umbrales en BusinessRule afecta
    inmediatamente el resultado de la evaluación.
    Solo ADMIN puede modificar BusinessRule (validado en RF16 views).
    """

    def setUp(self):
        self.client_obj = make_client(phone="3005554444")

    def test_cambio_de_umbral_gasto_afecta_resultado(self):
        """RF13: Si el admin sube el umbral de gasto, el resultado cambia."""
        create_topups(
            self.client_obj,
            {1: [40000], 2: [40000], 3: [40000]},
        )
        # Con umbral bajo: elegible
        setup_business_rules(min_spending="30000.00", min_frequency="3")
        result = EligibilityEngine.evaluate_client(self.client_obj)
        self.assertTrue(result["is_eligible"])

        # El admin sube el umbral: ya no elegible
        setup_business_rules(min_spending="60000.00", min_frequency="3")
        result = EligibilityEngine.evaluate_client(self.client_obj)
        self.assertFalse(result["is_eligible"])

    def test_cambio_de_umbral_frecuencia_afecta_resultado(self):
        """RF13: Si el admin sube la frecuencia mínima, el resultado cambia."""
        create_topups(
            self.client_obj,
            {1: [60000], 2: [60000], 3: [60000]},
        )
        # Con frecuencia baja: elegible
        setup_business_rules(min_spending="50000.00", min_frequency="2")
        result = EligibilityEngine.evaluate_client(self.client_obj)
        self.assertTrue(result["is_eligible"])

        # El admin sube la frecuencia mínima: ya no elegible
        setup_business_rules(min_spending="50000.00", min_frequency="10")
        result = EligibilityEngine.evaluate_client(self.client_obj)
        self.assertFalse(result["is_eligible"])
