from rest_framework.permissions import BasePermission

from .models import ExternalAPIKey


class HasValidApiKey(BasePermission):
    """
    RF20 — Permite el acceso solo si request.auth es una ExternalAPIKey activa.
    Usada en conjunto con ApiKeyAuthentication.
    """

    message = "Se requiere una API Key válida en el header X-API-Key."

    def has_permission(self, request, view):
        return isinstance(request.auth, ExternalAPIKey)
