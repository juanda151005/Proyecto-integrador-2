from django.urls import path
from . import views

app_name = 'core_business'

urlpatterns = [
    # RF06, RF07 — Registro y consulta de clientes
    path('', views.ClientListCreateView.as_view(), name='client-list-create'),

    # RF08, RF09 — Actualización y eliminación
    path('<int:pk>/', views.ClientDetailView.as_view(), name='client-detail'),

    # RF10 — Exportación a CSV
    path('export/csv/', views.ClientExportCSVView.as_view(), name='client-export-csv'),
]
