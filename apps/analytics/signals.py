"""
Señales de analytics — RF12: Recálculo automático de gasto promedio.

Cuando se crea una nueva recarga (TopUp), el sistema recalcula
automáticamente el gasto promedio mensual del cliente asociado
y lo persiste en su perfil. También re-evalúa la elegibilidad RF13
(basada en antigüedad), de modo que si el cliente ya superó los
60 días, se marca elegible en ese momento.

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
    # RF13/RF15 — Al evaluar el cliente, se actualiza el promedio,
    # el estado is_eligible y se dispara la oferta si corresponde.
    EligibilityEngine.evaluate_client(client)

    logger.info(
        "[RF12-signal] Evaluación completa (promedio y elegibilidad) para cliente %s (%s)",
        client.pk,
        client.phone_number,
    )
