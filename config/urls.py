"""
URL configuration for Smart Migration System.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# Importar la vista personalizada de JWT (RF02)
from apps.users.views import CustomTokenObtainPairView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # =========================================================================
    # JWT Authentication (RF02)
    # =========================================================================
    path('api/v1/auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # =========================================================================
    # App Routes
    # =========================================================================
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/clients/', include('apps.core_business.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/management/', include('apps.management.urls')),
    path('api/v1/communications/', include('apps.communications.urls')),

    # =========================================================================
    # API Documentation — Swagger / OpenAPI
    # =========================================================================
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
