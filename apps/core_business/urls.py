from django.urls import path
from . import views

app_name = "core_business"

urlpatterns = [
    # ── Planes parametrizables ──────────────────────────────────────────────
    path("plans/", views.PlanListCreateView.as_view(), name="plan-list-create"),
    path("plans/<int:pk>/", views.PlanDetailView.as_view(), name="plan-detail"),

    # ── Clientes: RF06, RF07 ────────────────────────────────────────────────
    path("", views.ClientListCreateView.as_view(), name="client-list-create"),
    path("<int:pk>/", views.ClientDetailView.as_view(), name="client-detail"),

    # ── Exportación RF10 ────────────────────────────────────────────────────
    path("export/csv/", views.ClientExportCSVView.as_view(), name="client-export-csv"),

    # ── Importación masiva CSV/Excel ────────────────────────────────────────
    path("import/", views.ClientImportView.as_view(), name="client-import"),
]
