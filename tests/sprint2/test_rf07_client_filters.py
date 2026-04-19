"""
RF07 — Consulta de clientes con filtros combinados.

CP 1.1 (Integration): Filtrado estricto — solo devuelve clientes que cumplan
                      simultáneamente todos los parámetros aplicados.
CP 1.2 (Unit):        Sin resultados coincidentes — devuelve lista vacía con
                      el mensaje apropiado.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.core_business.models import Client
from apps.users.models import CustomUser

CLIENTS_URL = "/api/v1/clients/"


def _make_analyst():
    user = CustomUser.objects.create_user(
        username="analista_rf07",
        email="analista_rf07@test.com",
        password="Pass1234!",
        role=CustomUser.Role.ANALYST,
    )
    return user


def _make_client(
    phone,
    full_name,
    document,
    plan=Client.PlanChoices.PREPAGO_BASIC,
    status_val=Client.StatusChoices.ACTIVE,
    spending=Decimal("0.00"),
    is_eligible=False,
    activation=date(2025, 1, 1),
):
    return Client.objects.create(
        phone_number=phone,
        full_name=full_name,
        document_number=document,
        email=f"{phone}@example.com",
        activation_date=activation,
        current_plan=plan,
        status=status_val,
        average_spending=spending,
        is_eligible=is_eligible,
    )


class RF07CP11FiltradoEstrictoTest(TestCase):
    """
    CP 1.1 — Filtrado estricto.
    El endpoint devuelve únicamente los clientes que satisfacen
    simultáneamente todos los parámetros de filtro aplicados
    (gasto mínimo, plan y elegibilidad).
    """

    def setUp(self):
        self.api = APIClient()
        self.user = _make_analyst()
        self.api.force_authenticate(user=self.user)

        self.cliente_alto_gasto_premium_elegible = _make_client(
            phone="3001111111",
            full_name="Cliente A — Alto gasto premium elegible",
            document="DOC001",
            plan=Client.PlanChoices.PREPAGO_PREMIUM,
            spending=Decimal("80000.00"),
            is_eligible=True,
        )
        self.cliente_alto_gasto_premium_no_elegible = _make_client(
            phone="3002222222",
            full_name="Cliente B — Alto gasto premium no elegible",
            document="DOC002",
            plan=Client.PlanChoices.PREPAGO_PREMIUM,
            spending=Decimal("80000.00"),
            is_eligible=False,
        )
        self.cliente_bajo_gasto_basic = _make_client(
            phone="3003333333",
            full_name="Cliente C — Bajo gasto básico",
            document="DOC003",
            plan=Client.PlanChoices.PREPAGO_BASIC,
            spending=Decimal("20000.00"),
            is_eligible=False,
        )
        self.cliente_medio_gasto_plus = _make_client(
            phone="3004444444",
            full_name="Cliente D — Gasto medio plus",
            document="DOC004",
            plan=Client.PlanChoices.PREPAGO_PLUS,
            spending=Decimal("50000.00"),
            is_eligible=False,
        )

    def test_filtro_por_gasto_minimo_excluye_clientes_por_debajo(self):
        response = self.api.get(f"{CLIENTS_URL}?min_spending=70000")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        phones = [c["phone_number"] for c in response.data["results"]]
        self.assertIn("3001111111", phones)
        self.assertIn("3002222222", phones)
        self.assertNotIn("3003333333", phones)
        self.assertNotIn("3004444444", phones)

    def test_filtro_por_plan_devuelve_solo_ese_plan(self):
        response = self.api.get(f"{CLIENTS_URL}?current_plan=PREPAGO_PREMIUM")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertEqual(item["current_plan"], "PREPAGO_PREMIUM")

    def test_filtros_combinados_gasto_plan_y_elegibilidad(self):
        """Tres filtros simultáneos: solo el cliente A cumple los tres."""
        response = self.api.get(
            f"{CLIENTS_URL}?min_spending=70000&current_plan=PREPAGO_PREMIUM&is_eligible=true"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["phone_number"], "3001111111"
        )

    def test_filtro_por_rango_de_gasto(self):
        response = self.api.get(
            f"{CLIENTS_URL}?min_spending=40000&max_spending=60000"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        phones = [c["phone_number"] for c in response.data["results"]]
        self.assertIn("3004444444", phones)
        self.assertNotIn("3001111111", phones)
        self.assertNotIn("3003333333", phones)

    def test_filtro_por_estado(self):
        cliente_inactivo = _make_client(
            phone="3005555555",
            full_name="Cliente Inactivo",
            document="DOC005",
            status_val=Client.StatusChoices.INACTIVE,
        )
        response = self.api.get(f"{CLIENTS_URL}?status=INACTIVE")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        phones = [c["phone_number"] for c in response.data["results"]]
        self.assertIn(cliente_inactivo.phone_number, phones)
        self.assertNotIn("3001111111", phones)


class RF07CP12SinResultadosCoincidentesTest(TestCase):
    """
    CP 1.2 — Sin resultados coincidentes.
    Cuando ningún cliente cumple los filtros, el sistema devuelve una
    lista vacía con count=0 (no un error ni una excepción).
    """

    def setUp(self):
        self.api = APIClient()
        self.user = _make_analyst()
        self.api.force_authenticate(user=self.user)

        _make_client(
            phone="3006666666",
            full_name="Único Cliente",
            document="DOC006",
            spending=Decimal("30000.00"),
            plan=Client.PlanChoices.PREPAGO_BASIC,
        )

    def test_filtro_sin_coincidencias_devuelve_lista_vacia(self):
        response = self.api.get(
            f"{CLIENTS_URL}?min_spending=999999"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_busqueda_texto_sin_coincidencias_devuelve_lista_vacia(self):
        response = self.api.get(f"{CLIENTS_URL}?search=NombreQueNoExisteEnLaBaseDeDatos")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_filtros_combinados_sin_coincidencias_devuelve_lista_vacia(self):
        response = self.api.get(
            f"{CLIENTS_URL}?current_plan=PREPAGO_PREMIUM&is_eligible=true&min_spending=500000"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_base_datos_vacia_devuelve_lista_vacia(self):
        Client.objects.all().delete()
        response = self.api.get(CLIENTS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])
