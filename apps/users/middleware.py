import re

from django.http import JsonResponse

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
