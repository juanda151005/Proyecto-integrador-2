from django.urls import path
from . import views

app_name = "app_management"

urlpatterns = [
    path(
        "system-settings/",
        views.GlobalSystemSettingsView.as_view(),
        name="global-system-settings",
    ),
    # RF16 — Configuración de parámetros generales
    path(
        "rules/",
        views.BusinessRuleListCreateView.as_view(),
        name="businessrule-list-create",
    ),
    path(
        "rules/<int:pk>/",
        views.BusinessRuleDetailView.as_view(),
        name="businessrule-detail",
    ),
    # RF14 — Bitácora de auditoría
    path("audit-logs/", views.AuditLogListView.as_view(), name="auditlog-list"),
    # RF17 — Dashboard de reportes de conversión
    path(
        "reports/conversion/",
        views.ConversionReportView.as_view(),
        name="conversion-report",
    ),
]
