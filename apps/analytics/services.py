"""
Motor de elegibilidad y cálculos analíticos.
Persona 3 — RF12, RF13.
"""

from decimal import Decimal
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth

from apps.core_business.models import Client
from apps.management.models import BusinessRule
from .models import TopUp


class EligibilityEngine:
    """
    Motor que determina si un cliente prepago es elegible para migrar a postpago.
    Utiliza las reglas de negocio configuradas en BusinessRule (RF16).
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
        """Obtiene el umbral mínimo de gasto promedio desde BusinessRule."""
        try:
            rule = BusinessRule.objects.get(key="MIN_AVERAGE_SPENDING", is_active=True)
            return Decimal(rule.value)
        except BusinessRule.DoesNotExist:
            return Decimal("50000.00")  # Valor por defecto

    @staticmethod
    def calculate_average_spending(client):
        """
        RF12 — Calcula el gasto promedio mensual de un cliente
        basado en sus recargas.
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

        return average, int(TopUp.objects.filter(client=client).count()), months

    @classmethod
    def evaluate_client(cls, client):
        """
        RF13 — Evalúa si un cliente es elegible para migración.
        Retorna un dict con el resultado.
        """
        threshold = cls.get_threshold()
        average, total_topups, months = cls.calculate_average_spending(client)

        is_eligible = average >= threshold and months >= 3

        # Actualizar el cliente
        client.average_spending = average
        client.is_eligible = is_eligible
        client.save(update_fields=["average_spending", "is_eligible"])

        if is_eligible:
            reason = f"Gasto promedio ${average:,.2f} supera el umbral de ${threshold:,.2f} con {months} meses de historial."
        else:
            reasons = []
            if average < threshold:
                reasons.append(
                    f"Gasto promedio ${average:,.2f} no alcanza el umbral de ${threshold:,.2f}"
                )
            if months < 3:
                reasons.append(f"Solo tiene {months} mes(es) de historial (mínimo 3)")
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
