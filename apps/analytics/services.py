"""
Motor de elegibilidad y cálculos analíticos.
Persona 3 — RF12, RF13.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth

from apps.core_business.models import Client
from apps.management.models import BusinessRule

from .models import TopUp


class EligibilityEngine:
    """
    Motor que determina si un cliente prepago es elegible para migrar a postpago.

    RF13 — Criterio de elegibilidad:
    - Un cliente es elegible SOLO si lleva ≥ MIN_SENIORITY_DAYS días
      con la línea activa (calculado desde activation_date).

    CP 1.1: Clientes con antigüedad ≥ MIN_SENIORITY_DAYS son marcados elegibles.
    CP 1.2: Clientes con antigüedad < MIN_SENIORITY_DAYS NO son marcados elegibles.
    """

    @staticmethod
    def get_analysis_interval_minutes():
        """Periodicidad de re-evaluación del motor leída desde configuración global."""
        from apps.management.runtime_settings import get_runtime_settings

        return get_runtime_settings()["analysis_interval_minutes"]

    @staticmethod
    def get_min_seniority_days():
        """
        Obtiene la antigüedad mínima en días desde BusinessRule.
        Clave: MIN_SENIORITY_DAYS (solo ADMIN puede modificarla vía RF16).
        """
        try:
            rule = BusinessRule.objects.get(key="MIN_SENIORITY_DAYS", is_active=True)
            return int(rule.value)
        except BusinessRule.DoesNotExist:
            return 60

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

        Un cliente es elegible SOLO si su antigüedad (días desde activation_date
        hasta hoy) es mayor o igual a MIN_SENIORITY_DAYS (60 días por defecto).

        También actualiza average_spending para RF12, aunque ese valor
        ya no determina la elegibilidad.

        Retorna un dict con el resultado de la evaluación.
        """
        min_seniority = cls.get_min_seniority_days()
        seniority_days = (date.today() - client.activation_date).days

        # Actualizar average_spending (RF12) aunque no sea criterio de elegibilidad
        average, total_topups, months = cls.calculate_average_spending(client)

        is_eligible = seniority_days >= min_seniority

        # ── Persistir resultado en el perfil del cliente ──
        client.average_spending = average
        client.is_eligible = is_eligible
        client.save(update_fields=["average_spending", "is_eligible"])

        # ── Construir razón descriptiva ──
        if is_eligible:
            reason = (
                f"Antigüedad de {seniority_days} días supera el mínimo de "
                f"{min_seniority} días requeridos."
            )
        else:
            reason = (
                f"Antigüedad de {seniority_days} días no alcanza el mínimo de "
                f"{min_seniority} días requeridos."
            )

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
