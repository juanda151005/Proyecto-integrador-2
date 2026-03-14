from django.contrib import admin
from .models import CustomUser, LoginAttempt


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['username_attempted', 'ip_address', 'was_successful', 'timestamp']
    list_filter = ['was_successful']
    search_fields = ['username_attempted', 'ip_address']
    readonly_fields = ['user', 'username_attempted', 'ip_address', 'was_successful', 'timestamp']
