from django.contrib import admin

from .models import Client, Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "target_plan_name", "target_plan_price", "min_seniority_days", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code", "target_plan_name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "phone_number",
        "document_number",
        "email",
        "current_plan",
        "plan",
        "activation_date",
        "is_eligible",
        "average_spending",
        "status",
    ]
    list_filter = ["current_plan", "plan", "is_eligible", "status"]
    search_fields = ["full_name", "phone_number", "document_number"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "activation_date"
    autocomplete_fields = ["plan"]
