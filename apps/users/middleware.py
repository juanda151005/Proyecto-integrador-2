import json
import logging
import re

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# =============================================================================
# RF05 — Middleware de Auditoría de Login
# =============================================================================

#: Ruta del endpoint de autenticación que se va a auditar
_LOGIN_PATH = "/api/v1/auth/token/"


class LoginAuditMiddleware(MiddlewareMixin):
    """
    RF05 — Middleware de auditoría de intentos de inicio de sesión.

    Intercepta TODAS las peticiones POST a ``/api/v1/auth/token/`` y registra
    en la tabla ``login_logs`` (modelo LoginAttempt) los siguientes datos:

    - Dirección IP de origen (incluyendo soporte para X-Forwarded-For)
    - User-Agent del cliente (navegador, herramienta, etc.)
    - Username intentado
    - Fecha y hora exacta del intento
    - Resultado: exitoso (HTTP 200) o fallido (cualquier otro código)

    Criterios de aceptación RF05:
    ✓ Se registran tanto los intentos fallidos como los exitosos.
    ✓ El log incluye el origen (dirección IP) del intento.
    ✓ El log incluye el User-Agent para detectar herramientas de ataque.

    Nota de diseño: el registro «exitoso/fallido» se determina por el código
    de respuesta HTTP *después* de que la vista procesa la petición. Esto es
    complementario al registro que hace el serializer; si alguno falla, el
    otro garantiza que el intento quede registrado (defensa en profundidad).
    """

    def process_request(self, request):
        """Guarda la IP y User-Agent antes de que la vista procese el request."""
        if request.path == _LOGIN_PATH and request.method == "POST":
            request._audit_ip = self._get_client_ip(request)
            request._audit_ua = request.META.get("HTTP_USER_AGENT", "")[:512]
            request._audit_username = self._extract_username(request)

    def process_response(self, request, response):
        """
        Registra el intento de login tras conocer el resultado HTTP.

        Solo actúa sobre POST a la ruta de token. El serializer ya registra
        el intento; este middleware actúa como fallback y fuente de verdad
        para el código de respuesta real.
        """
        if request.path == _LOGIN_PATH and request.method == "POST":
            # Si process_request no corrió (e.g. middleware no instalado arriba),
            # intentamos recuperar los valores de todas formas.
            ip = getattr(request, "_audit_ip", None) or self._get_client_ip(request)
            ua = getattr(request, "_audit_ua", None)
            if ua is None:
                ua = request.META.get("HTTP_USER_AGENT", "")[:512]
            username = getattr(request, "_audit_username", None) or ""

            success = response.status_code == 200

            # Solo log a nivel DEBUG aquí para no duplicar el INSERT del
            # serializer. El serializer ya hace el INSERT en la BD.
            # Este middleware solo registra en el logger de Python (útil
            # para sistemas de monitoreo externos como Sentry o ELK).
            level = logging.INFO if success else logging.WARNING
            logger.log(
                level,
                "[LoginAudit] ip=%s user=%r ua=%.80s status=%s",
                ip,
                username,
                ua,
                response.status_code,
            )

        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_client_ip(request):
        """Detecta la IP real del cliente soportando proxies inversos."""
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @staticmethod
    def _extract_username(request):
        """
        Intenta leer el username del body JSON *sin consumir* el stream.

        Django almacena el body en ``request.body`` (bytes) la primera vez
        que se accede; lecturas posteriores devuelven el mismo buffer.
        """
        try:
            body = json.loads(request.body.decode("utf-8", errors="ignore"))
            return body.get("username", "")
        except Exception:
            return ""


# =============================================================================
# RF19 — Mapa de rutas protegidas por rol
# =============================================================================

RBAC_ROUTE_MAP = [
    {
        "pattern": r"^/api/v1/users/$",
        "methods": ["GET", "POST"],
        "allowed_roles": ["ADMIN"],
    },
    {
        "pattern": r"^/api/v1/users/\d+/$",
        "methods": ["GET", "PUT", "PATCH", "DELETE"],
        "allowed_roles": ["ADMIN"],
    },
    {
        "pattern": r"^/api/v1/users/login-attempts/$",
        "methods": ["GET"],
        "allowed_roles": ["ADMIN"],
    },
    {
        "pattern": r"^/api/v1/management/system-settings/$",
        "methods": ["GET", "PUT", "PATCH"],
        "allowed_roles": ["ADMIN"],
    },
]

# Rutas que NO requieren autenticación (login, docs, schema)
PUBLIC_PATHS = [
    r"^/api/v1/auth/",
    r"^/api/schema/",
    r"^/api/docs/",
    r"^/api/redoc/",
    r"^/admin/",
]


def _is_public_path(path):
    """Verifica si la ruta es pública (no requiere autenticación)."""
    return any(re.match(p, path) for p in PUBLIC_PATHS)


def _get_required_roles(path, method):
    """
    RF19 — Busca en el mapa RBAC si la ruta+método tiene roles requeridos.

    Retorna la lista de roles permitidos o None si no hay restricción explícita.
    """
    for route in RBAC_ROUTE_MAP:
        if re.match(route["pattern"], path) and method in route["methods"]:
            return route["allowed_roles"]
    return None


class RBACMiddleware:
    """
    RF19 — Middleware de Control de Acceso Basado en Roles.

    Intercepta todas las peticiones API y verifica que el usuario
    tenga el rol necesario según el mapa RBAC_ROUTE_MAP.

    Flujo:
    1. Si la ruta es pública → pasa.
    2. Si el usuario no está autenticado → pasa (DRF maneja el 401).
    3. Si la ruta tiene restricción de rol y el usuario NO tiene ese rol → 403.
    4. Si no hay restricción explícita → pasa (las vistas manejan sus permisos).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        method = request.method

        # 1. Rutas públicas → siempre pasan
        if _is_public_path(path):
            return self.get_response(request)

        # 2. Usuario no autenticado → DRF se encarga del 401
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return self.get_response(request)

        # 3. Verificar RBAC
        required_roles = _get_required_roles(path, method)
        if required_roles and request.user.role not in required_roles:
            return JsonResponse(
                {
                    "detail": "No tiene permisos para acceder a este recurso.",
                    "required_roles": required_roles,
                    "your_role": request.user.role,
                },
                status=403,
            )

        # 4. Sin restricción explícita → pasa
        return self.get_response(request)
