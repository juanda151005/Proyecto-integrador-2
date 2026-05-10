from django.contrib import admin
from .models import Conversation, NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["client", "channel", "status", "sent_at"]
    list_filter = ["channel", "status"]
    search_fields = ["client__phone_number", "client__full_name"]
    readonly_fields = [
        "client",
        "message",
        "channel",
        "status",
        "external_id",
        "sent_at",
    ]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        "client",
        "status",
        "client_response",
        "had_response",
        "advisor",
        "opened_at",
        "closed_at",
    ]
    list_filter = ["status", "client_response", "had_response"]
    search_fields = ["client__phone_number", "client__full_name"]
    readonly_fields = ["client", "notification", "client_response", "had_response", "opened_at"]
    autocomplete_fields = ["advisor"]
