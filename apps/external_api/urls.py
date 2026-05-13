from django.urls import path

from .views import ExternalProspectDetailView, ExternalProspectListView, ExternalStatusView

app_name = "external_api"

urlpatterns = [
    path("status/", ExternalStatusView.as_view(), name="external-status"),
    path("prospects/", ExternalProspectListView.as_view(), name="external-prospect-list"),
    path("prospects/<int:pk>/", ExternalProspectDetailView.as_view(), name="external-prospect-detail"),
]
