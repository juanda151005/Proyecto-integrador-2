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
