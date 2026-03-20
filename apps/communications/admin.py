from django.contrib import admin
from .models import NotificationLog


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
