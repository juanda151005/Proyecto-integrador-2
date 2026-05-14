from django.contrib import admin

from .models import ExternalAPIKey


@admin.register(ExternalAPIKey)
class ExternalAPIKeyAdmin(admin.ModelAdmin):
    list_display = ["name", "key", "is_active", "created_at", "last_used_at"]
    list_filter = ["is_active"]
    readonly_fields = ["key", "created_at", "last_used_at"]
    search_fields = ["name"]
