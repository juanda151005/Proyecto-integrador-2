"""
Señales de analytics — RF12: Recálculo automático de gasto promedio.

Cuando se crea una nueva recarga (TopUp), el sistema recalcula
automáticamente el gasto promedio mensual del cliente asociado
y lo persiste en su perfil.

Criterios de aceptación RF12:
- CP 1.1: Al registrar una nueva recarga, el gasto promedio se
  recalcula incluyendo el nuevo valor.
- CP 1.2: Al registrar la primera recarga de un cliente, el sistema
  calcula el promedio sin errores por división o historial vacío.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="analytics.TopUp")
def recalculate_average_spending_on_topup(sender, instance, created, **kwargs):
    """
    RF12 — Recálculo automático tras nueva recarga.

    Se dispara después de guardar un TopUp. Solo actúa cuando el
    registro es nuevo (created=True), no en actualizaciones.
    """
    if not created:
        return

    from .services import EligibilityEngine

    client = instance.client
    average, total_topups, months = EligibilityEngine.calculate_average_spending(client)

    client.average_spending = average
    client.save(update_fields=["average_spending"])

    logger.info(
        "[RF12-signal] Gasto promedio recalculado para cliente %s (%s): "
        "$%s (%d recargas en %d meses)",
        client.pk,
        client.phone_number,
        average,
        total_topups,
        months,
    )
