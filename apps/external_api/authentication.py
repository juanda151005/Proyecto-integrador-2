from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import ExternalAPIKey


class ApiKeyAuthentication(BaseAuthentication):
    """
    RF20 — Autenticación por API Key para el prefijo /api/v1/external/.
    La clave se envía en el header:  X-API-Key: <key>
    """

    def authenticate(self, request):
        api_key = request.META.get("HTTP_X_API_KEY")
        if not api_key:
            return None

        try:
            key_obj = ExternalAPIKey.objects.get(key=api_key, is_active=True)
        except ExternalAPIKey.DoesNotExist:
            raise AuthenticationFailed("API Key inválida o inactiva.")

        key_obj.last_used_at = timezone.now()
        key_obj.save(update_fields=["last_used_at"])
        return (None, key_obj)

    def authenticate_header(self, request):
        return "X-API-Key"
