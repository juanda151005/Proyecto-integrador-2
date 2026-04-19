"""
Motor de elegibilidad y cálculos analíticos.
Persona 3 — RF12, RF13.
"""

from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from apps.core_business.models import Client
from apps.management.models import BusinessRule

from .models import TopUp


class EligibilityEngine:
    """
    Motor que determina si un cliente prepago es elegible para migrar a postpago.

    Utiliza las reglas de negocio configuradas en BusinessRule (RF16):
    - MIN_AVERAGE_SPENDING: Gasto promedio mensual mínimo requerido.
    - MIN_RECHARGE_FREQUENCY: Cantidad mínima de recargas totales requeridas.

    RF13 — Criterios de aceptación:
    - CP 1.1: Solo los clientes que cumplen el 100% de los criterios
      configurados son marcados como elegibles.
    - CP 1.2: Si un cliente cumple solo algunos criterios (ej. supera
      el gasto pero no la frecuencia), NO se marca como elegible.
    """

    @staticmethod
    def get_analysis_interval_minutes():
        """
        Periodicidad de re-evaluación del motor leída desde configuración global.
        """
        from apps.management.runtime_settings import get_runtime_settings

        return get_runtime_settings()["analysis_interval_minutes"]

    @staticmethod
    def get_threshold():
        """
        Obtiene el umbral mínimo de gasto promedio mensual desde BusinessRule.
        Clave: MIN_AVERAGE_SPENDING (solo ADMIN puede modificarla vía RF16).
        """
        try:
            rule = BusinessRule.objects.get(key="MIN_AVERAGE_SPENDING", is_active=True)
            return Decimal(rule.value)
        except BusinessRule.DoesNotExist:
            return Decimal("50000.00")

    @staticmethod
    def get_min_frequency():
        """
        Obtiene la frecuencia mínima de recargas desde BusinessRule.
        Clave: MIN_RECHARGE_FREQUENCY (solo ADMIN puede modificarla vía RF16).

        Este valor representa la cantidad mínima de recargas totales
        que un cliente debe tener registradas para ser considerado elegible.
        """
        try:
            rule = BusinessRule.objects.get(
                key="MIN_RECHARGE_FREQUENCY", is_active=True
            )
            return int(rule.value)
        except BusinessRule.DoesNotExist:
            return 3

    @staticmethod
    def calculate_average_spending(client):
        """
        RF12 — Calcula el gasto promedio mensual de un cliente
        basado en sus recargas agrupadas por mes.

        Retorna:
            tuple: (gasto_promedio, total_recargas, meses_analizados)
        """
        monthly_totals = (
            TopUp.objects.filter(client=client)
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
        )

        if not monthly_totals:
            return Decimal("0.00"), 0, 0

        total_spending = sum(m["total"] for m in monthly_totals)
        months = len(monthly_totals)
        average = total_spending / months
        total_topups = TopUp.objects.filter(client=client).count()

        return average, total_topups, months

    @classmethod
    def evaluate_client(cls, client):
        """
        RF13 — Evalúa si un cliente es elegible para migración a postpago.

        Lee ambos umbrales desde BusinessRule (configurados por ADMIN):
        - MIN_AVERAGE_SPENDING: gasto promedio mensual mínimo.
        - MIN_RECHARGE_FREQUENCY: cantidad mínima de recargas.

        Un cliente es elegible SOLO si cumple TODOS los criterios (AND lógico).
        Si cumple únicamente uno de los dos, NO se marca como elegible (CP 1.2).

        Retorna un dict con el resultado de la evaluación.
        """
        spending_threshold = cls.get_threshold()
        frequency_threshold = cls.get_min_frequency()
        average, total_topups, months = cls.calculate_average_spending(client)

        # ── Evaluación: AMBOS criterios deben cumplirse (CP 1.1 / CP 1.2) ──
        meets_spending = average >= spending_threshold
        meets_frequency = total_topups >= frequency_threshold
        is_eligible = meets_spending and meets_frequency

        # ── Persistir resultado en el perfil del cliente ──
        client.average_spending = average
        client.is_eligible = is_eligible
        client.save(update_fields=["average_spending", "is_eligible"])

        # ── Construir razón descriptiva ──
        if is_eligible:
            reason = (
                f"Gasto promedio ${average:,.2f} supera el umbral de "
                f"${spending_threshold:,.2f} y frecuencia de {total_topups} "
                f"recargas supera el mínimo de {frequency_threshold}."
            )
        else:
            reasons = []
            if not meets_spending:
                reasons.append(
                    f"Gasto promedio ${average:,.2f} no alcanza el umbral "
                    f"de ${spending_threshold:,.2f}"
                )
            if not meets_frequency:
                reasons.append(
                    f"Frecuencia de {total_topups} recargas no alcanza "
                    f"el mínimo de {frequency_threshold}"
                )
            reason = ". ".join(reasons) + "."

        return {
            "client_id": client.id,
            "phone_number": client.phone_number,
            "full_name": client.full_name,
            "average_spending": average,
            "is_eligible": is_eligible,
            "reason": reason,
        }

    @classmethod
    def evaluate_all_clients(cls):
        """Evalúa todos los clientes activos y retorna lista de resultados."""
        clients = Client.objects.filter(status=Client.StatusChoices.ACTIVE)
        return [cls.evaluate_client(client) for client in clients]
