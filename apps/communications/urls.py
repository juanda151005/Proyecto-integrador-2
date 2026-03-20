from django.urls import path
from . import views

app_name = "communications"

urlpatterns = [
    # RF15 — Logs de notificaciones
    path(
        "notifications/",
        views.NotificationLogListView.as_view(),
        name="notification-list",
    ),
    # RF15 — Envío individual
    path(
        "notifications/send/",
        views.SendNotificationView.as_view(),
        name="notification-send",
    ),
    # RF15 — Envío masivo a elegibles
    path(
        "notifications/send-bulk/",
        views.BulkNotifyEligibleView.as_view(),
        name="notification-bulk",
    ),
    # RF20 — Consulta API externa
    path(
        "external/query/", views.ExternalAPIQueryView.as_view(), name="external-query"
    ),
]
