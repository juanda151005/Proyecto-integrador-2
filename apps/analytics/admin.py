from django.contrib import admin
from .models import TopUp, ClientChangeLog


@admin.register(TopUp)
class TopUpAdmin(admin.ModelAdmin):
    list_display = ['client', 'amount', 'date', 'channel']
    list_filter = ['channel', 'date']
    search_fields = ['client__phone_number', 'client__full_name']


@admin.register(ClientChangeLog)
class ClientChangeLogAdmin(admin.ModelAdmin):
    list_display = ['client', 'field_name', 'old_value', 'new_value', 'changed_by', 'changed_at']
    list_filter = ['field_name']
    search_fields = ['client__phone_number']
    readonly_fields = ['client', 'field_name', 'old_value', 'new_value', 'changed_by', 'changed_at']
