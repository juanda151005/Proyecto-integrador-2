from django.contrib import admin
from .models import BusinessRule, AuditLog


@admin.register(BusinessRule)
class BusinessRuleAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'is_active', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['key', 'description']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'model_name', 'object_id', 'user', 'timestamp']
    list_filter = ['action', 'model_name']
    search_fields = ['model_name', 'object_id']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'changes', 'ip_address', 'timestamp']
