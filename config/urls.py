from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.static import serve
from rest_framework_simplejwt.views import TokenRefreshView
import os
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# Importar las vistas de JWT y recuperación de contraseña (RF02, RF06)
from apps.users.views import (
    CustomTokenObtainPairView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # =========================================================================
    # JWT Authentication (RF02)
    # =========================================================================
    path(
        "api/v1/auth/token/",
        CustomTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"
    ),
    # =========================================================================
    # Recuperación de contraseña (RF06) — Rutas públicas
    # =========================================================================
    path(
        "api/v1/auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="password_reset_request",
    ),
    path(
        "api/v1/auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    # =========================================================================
    # App Routes
    # =========================================================================
    path("api/v1/users/", include("apps.users.urls")),
    path("api/v1/clients/", include("apps.core_business.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/management/", include("apps.management.urls")),
    path("api/v1/communications/", include("apps.communications.urls")),
    # =========================================================================
    # API Documentation — Swagger / OpenAPI
    # =========================================================================
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Servir archivos media en desarrollo (fotos de perfil — RF04)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# =========================================================================
# Frontend — Servir archivos HTML/CSS/JS estáticos en desarrollo
# =========================================================================
FRONTEND_DIR = os.path.join(settings.BASE_DIR, "frontend")

urlpatterns += [
    # Ruta raíz → redirige al login
    path("", RedirectView.as_view(url="/frontend/login.html", permanent=False)),

    # Servir cualquier archivo dentro de frontend/
    re_path(r"^frontend/(?P<path>.*)$", serve, {"document_root": FRONTEND_DIR}),
]
