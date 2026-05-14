from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Solo usuarios con rol ADMIN."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "ADMIN"
        )


class IsAnalyst(BasePermission):
    """Solo usuarios con rol ANALYST."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "ANALYST"
        )


class IsAgent(BasePermission):
    """Solo usuarios con rol AGENT."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "AGENT"
        )


class IsAdminOrAnalyst(BasePermission):
    """Usuarios con rol ADMIN, ANALYST o AGENT."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ("ADMIN", "ANALYST", "AGENT")
        )
