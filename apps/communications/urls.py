from django.urls import path
from . import views

app_name = "communications"

urlpatterns = [
    # ── Logs de notificaciones (RF15) ──────────────────────────────────────
    path(
        "notifications/",
        views.NotificationLogListView.as_view(),
        name="notification-list",
    ),
    path(
        "notifications/send/",
        views.SendNotificationView.as_view(),
        name="notification-send",
    ),
    path(
        "notifications/send-offer/",
        views.SendOfferView.as_view(),
        name="notification-send-offer",
    ),
    path(
        "notifications/send-bulk/",
        views.BulkNotifyEligibleView.as_view(),
        name="notification-bulk",
    ),

    # ── Webhook Twilio (respuestas Sí/No del cliente) ─────────────────────
    path(
        "webhook/twilio/",
        views.TwilioWebhookView.as_view(),
        name="twilio-webhook",
    ),

    # ── Conversaciones / flujo asesor ─────────────────────────────────────
    path(
        "conversations/",
        views.ConversationListView.as_view(),
        name="conversation-list",
    ),
    path(
        "conversations/<int:pk>/",
        views.ConversationDetailView.as_view(),
        name="conversation-detail",
    ),

    # ── Consulta API externa (RF20) ───────────────────────────────────────
    path(
        "external/query/",
        views.ExternalAPIQueryView.as_view(),
        name="external-query",
    ),
]
