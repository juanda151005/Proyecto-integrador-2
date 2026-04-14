from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.users.models import CustomUser, LoginAttempt


def create_user(validated_data):
    """
    RF01 — Crea un usuario con contraseña hasheada.

    La contraseña se encripta con PBKDF2 (Django default) o BCrypt.
    Esta función encapsula la lógica de negocio de creación de usuarios.
    """
    password = validated_data.pop("password")
    user = CustomUser(**validated_data)
    user.set_password(password)
    user.save()
    return user


def log_login_attempt(username, ip_address, success, user=None):
    """
    RF02/RF05 — Registra un intento de inicio de sesión en la bitácora.

    Se llama automáticamente en cada intento de login (exitoso o fallido).
    """
    return LoginAttempt.objects.create(
        user=user,
        username_attempted=username,
        ip_address=ip_address,
        was_successful=success,
    )


def get_client_ip(request):
    """Obtiene la IP real del cliente desde el request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# =============================================================================
# RF06 — Recuperación de contraseña por email
# =============================================================================

_token_generator = PasswordResetTokenGenerator()


def generate_password_reset_link(user):
    """
    RF06 — Genera el enlace de recuperación de contraseña.

    Usa PasswordResetTokenGenerator de Django (HMAC con timestamp).
    El enlace es válido por PASSWORD_RESET_TIMEOUT segundos (default: 3 días).

    Returns:
        str: URL completa lista para incluir en el email.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = _token_generator.make_token(user)
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    return f"{frontend_url}/reset-password/{uid}/{token}/"


def validate_password_reset_token(uidb64, token):
    """
    RF06 — Valida el UID y token del enlace de reset.

    Returns:
        CustomUser | None: el usuario si el token es válido, None si no.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        return None

    if _token_generator.check_token(user, token):
        return user
    return None


def send_password_reset_email(user):
    """
    RF06 — Envía el email de recuperación de contraseña.

    En desarrollo (console backend) imprime el correo en la terminal.
    En producción lo envía via SMTP configurado en .env.
    """
    reset_link = generate_password_reset_link(user)
    subject = "Recuperación de contraseña — Smart Migration System"
    message = (
        f"Hola {user.first_name or user.username},\n\n"
        f"Recibimos una solicitud para restablecer tu contraseña.\n\n"
        f"Haz clic en el siguiente enlace para crear una nueva contraseña:\n"
        f"{reset_link}\n\n"
        f"Este enlace expirará en 3 días.\n\n"
        f"Si no solicitaste este cambio, puedes ignorar este correo.\n\n"
        f"— Equipo Smart Migration System"
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
