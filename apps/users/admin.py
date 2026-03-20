from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, LoginAttempt


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin mejorado para gestión de usuarios (RF01).
    Interfaz de registro de usuarios en el panel administrativo.
    """

    # Columnas en la lista
    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "created_at",
    ]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-created_at"]

    # Campos al EDITAR un usuario existente
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Información personal",
            {"fields": ("first_name", "last_name", "email", "phone_number")},
        ),
        (
            "Rol y permisos",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Fechas importantes", {"fields": ("last_login",)}),
    )

    # Campos al CREAR un usuario nuevo desde el admin
    add_fieldsets = (
        (
            "Datos de acceso",
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
        (
            "Información personal",
            {
                "classes": ("wide",),
                "fields": ("first_name", "last_name", "phone_number"),
            },
        ),
        (
            "Rol",
            {
                "classes": ("wide",),
                "fields": ("role",),
            },
        ),
    )


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    """Admin para bitácora de login (RF05)."""

    list_display = ["username_attempted", "ip_address", "was_successful", "timestamp"]
    list_filter = ["was_successful", "timestamp"]
    search_fields = ["username_attempted", "ip_address"]
    readonly_fields = [
        "user",
        "username_attempted",
        "ip_address",
        "was_successful",
        "timestamp",
    ]
    date_hierarchy = "timestamp"
