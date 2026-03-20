from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Usuario personalizado con roles para RBAC.
    RF01 — Gestión de Usuarios y Roles.

    Criterios de aceptación:
    - El sistema permite asignar al menos un rol al crear el usuario.
    - No se permiten correos electrónicos duplicados.
    - La contraseña se almacena de forma segura (hasheada con PBKDF2/BCrypt).
    """

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        ANALYST = 'ANALYST', 'Analista'
        AGENT = 'AGENT', 'Asesor'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.AGENT,
        verbose_name='Rol',
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Teléfono',
    )

    # Forzar email único (Criterio de aceptación RF01)
    email = models.EmailField(
        unique=True,
        verbose_name='Correo electrónico',
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    # Campos requeridos al crear superusuario
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_analyst(self):
        return self.role == self.Role.ANALYST

    @property
    def is_agent(self):
        return self.role == self.Role.AGENT


class LoginAttempt(models.Model):
    """
    RF05 — Bitácora de intentos de inicio de sesión.
    También utilizado por RF02 para registrar cada intento de autenticación.
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_attempts',
        verbose_name='Usuario',
    )
    username_attempted = models.CharField(max_length=150, verbose_name='Username intentado')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='Dirección IP')
    was_successful = models.BooleanField(default=False, verbose_name='¿Exitoso?')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Fecha/Hora')

    class Meta:
        verbose_name = 'Intento de inicio de sesión'
        verbose_name_plural = 'Intentos de inicio de sesión'
        ordering = ['-timestamp']

    def __str__(self):
        status = '✓' if self.was_successful else '✗'
        return f'[{status}] {self.username_attempted} — {self.timestamp:%Y-%m-%d %H:%M}'
