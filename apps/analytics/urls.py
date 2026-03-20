from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    # RF11 — Registro de recargas
    path("topups/", views.TopUpListCreateView.as_view(), name="topup-list-create"),
    path("topups/<int:pk>/", views.TopUpDetailView.as_view(), name="topup-detail"),
    # RF12 — Cálculo de gasto promedio
    path(
        "average-spending/",
        views.CalculateAverageSpendingView.as_view(),
        name="average-spending",
    ),
    # RF13 — Motor de elegibilidad
    path(
        "eligibility/",
        views.EvaluateEligibilityView.as_view(),
        name="evaluate-eligibility",
    ),
    # RF18 — Historial de cambios
    path("change-logs/", views.ClientChangeLogListView.as_view(), name="change-logs"),
]
