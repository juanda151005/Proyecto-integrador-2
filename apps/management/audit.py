"""
RF14 — Escritura centralizada de la bitácora de auditoría.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.http import HttpRequest

from apps.core_business.models import Client

from .models import AuditLog, BusinessRule


def get_client_ip(request: HttpRequest | None) -> str | None:
    if request is None:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def snapshot_client(client: Client) -> dict[str, Any]:
    return {
        "id": client.pk,
        "phone_number": client.phone_number,
        "full_name": client.full_name,
        "document_number": client.document_number,
        "email": client.email,
        "activation_date": _json_safe(client.activation_date),
        "current_plan": client.current_plan,
        "is_eligible": client.is_eligible,
        "is_test_eligible": client.is_test_eligible,
        "average_spending": _json_safe(client.average_spending),
        "status": client.status,
        "created_at": _json_safe(client.created_at),
        "updated_at": _json_safe(client.updated_at),
    }


def snapshot_business_rule(rule: BusinessRule) -> dict[str, Any]:
    return {
        "id": rule.pk,
        "key": rule.key,
        "value": rule.value,
        "description": rule.description,
        "is_active": rule.is_active,
        "created_at": _json_safe(rule.created_at),
        "updated_at": _json_safe(rule.updated_at),
    }


def log_critical_action(
    *,
    user,
    action: str,
    model_name: str,
    object_id: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    request: HttpRequest | None = None,
) -> AuditLog:
    changes: dict[str, Any] = {}
    if before is not None:
        changes["before"] = before
    if after is not None:
        changes["after"] = after

    actor = user if getattr(user, "is_authenticated", False) else None

    return AuditLog.objects.create(
        user=actor,
        action=action,
        model_name=model_name,
        object_id=object_id,
        changes=changes,
        ip_address=get_client_ip(request),
    )
