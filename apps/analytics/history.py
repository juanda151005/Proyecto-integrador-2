"""
RF18 — Trazabilidad de cambios sobre clientes.

Función centralizada que compara el estado anterior de un cliente
con el nuevo y registra en ClientChangeLog solo los campos que cambiaron.

Uso desde una vista (cambio manual):
    before = snapshot_for_history(client_instance)
    client_instance = serializer.save()
    record_client_changes(before, client_instance, changed_by=request.user)

Uso desde un signal (cambio automático):
    before = snapshot_for_history(client_instance)
    # ... lógica que modifica el cliente ...
    record_client_changes(before, client_instance, changed_by=None, source="Motor de elegibilidad")
"""

from __future__ import annotations

import logging
from typing import Any

from .models import ClientChangeLog

logger = logging.getLogger(__name__)

# =============================================================================
# Campos de negocio que se rastrean.
# No incluimos updated_at / created_at porque son metadata, no cambios
# funcionales. average_spending se incluye para que el analista vea
# cuándo el sistema recalculó el gasto del cliente.
# =============================================================================

TRACKED_FIELDS: tuple[str, ...] = (
    "status",
    "is_eligible",
    "current_plan",
    "plan_id",
    "average_spending",
    "full_name",
    "email",
    "phone_number",
)

# Etiquetas legibles para el analista (campo de BD -> nombre en pantalla)
FIELD_LABELS: dict[str, str] = {
    "status": "Estado",
    "is_eligible": "Elegible para postpago",
    "current_plan": "Plan actual",
    "plan_id": "Plan de migración objetivo",
    "average_spending": "Gasto promedio mensual",
    "full_name": "Nombre completo",
    "email": "Correo electrónico",
    "phone_number": "Número de celular",
}


def snapshot_for_history(client) -> dict[str, Any]:
    """
    Captura los valores actuales de los campos rastreados de un cliente.

    Llamar ANTES de guardar para tener el estado anterior.

    Args:
        client: instancia de apps.core_business.models.Client

    Returns:
        dict con {campo: valor_actual} para cada campo en TRACKED_FIELDS.
    """
    return {field: getattr(client, field, None) for field in TRACKED_FIELDS}


def record_client_changes(
    before: dict[str, Any],
    client_after,
    changed_by=None,
    source: str = "manual",
) -> list[ClientChangeLog]:
    """
    RF18 — Compara before vs after y crea entradas en ClientChangeLog
    para cada campo que cambió.

    Args:
        before:       dict obtenido con snapshot_for_history() antes del save.
        client_after: instancia de Client ya guardada (el nuevo estado).
        changed_by:   instancia de CustomUser que hizo el cambio,
                      o None si fue un proceso automático del sistema.
        source:       descripción del origen del cambio cuando es automático
                      (ej: "Motor de elegibilidad", "Importación CSV").
                      Solo se usa en el log cuando changed_by es None.

    Returns:
        Lista de ClientChangeLog creados (puede ser vacía si no hubo cambios).
    """
    logs: list[ClientChangeLog] = []

    for field in TRACKED_FIELDS:
        old_val = before.get(field)
        new_val = getattr(client_after, field, None)

        # Comparamos como string para evitar diferencias de tipo (Decimal vs float)
        if str(old_val) != str(new_val):
            display_name = FIELD_LABELS.get(field, field)

            log = ClientChangeLog.objects.create(
                client=client_after,
                field_name=display_name,
                old_value=_format_value(field, old_val),
                new_value=_format_value(field, new_val),
                changed_by=changed_by,
            )
            logs.append(log)

            logger.debug(
                "[RF18] Cambio registrado | cliente=%s | campo=%s | '%s' -> '%s' | origen=%s",
                client_after.pk,
                display_name,
                old_val,
                new_val,
                changed_by.username if changed_by else source,
            )

    return logs


# =============================================================================
# Helpers internos
# =============================================================================


def _format_value(field: str, value: Any) -> str:
    """
    Convierte un valor a string legible para el analista.
    Maneja None, booleanos y decimales de forma consistente.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)
