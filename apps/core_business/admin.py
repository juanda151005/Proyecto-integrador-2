from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "phone_number",
        "document_number",
        "email",
        "current_plan",
        "activation_date",
        "is_eligible",
        "average_spending",
        "status",
    ]
    list_filter = ["current_plan", "is_eligible", "status"]
    search_fields = ["full_name", "phone_number", "document_number"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "activation_date"
