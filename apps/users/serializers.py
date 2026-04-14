from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import CustomUser, LoginAttempt
from .services import create_user, get_client_ip, log_login_attempt

# =============================================================================
# RF01 — Gestión de Usuarios y Roles
# =============================================================================


class UserSerializer(serializers.ModelSerializer):
    """Serializer de lectura para usuarios."""

    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "role_display",
            "phone_number",
            "photo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para registro de usuarios (RF01).

    Validaciones:
    - Email único (validado a nivel de modelo Y serializer)
    - Contraseña mínima 8 caracteres
    - Rol obligatorio (ADMIN, ANALYST, AGENT)
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="Mínimo 8 caracteres.",
    )
    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="Repita la contraseña.",
    )
    role = serializers.ChoiceField(
        choices=CustomUser.Role.choices,
        help_text="Rol del usuario: ADMIN, ANALYST o AGENT.",
    )

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "role",
            "phone_number",
        ]

    def validate_email(self, value):
        """Validar que el email no esté duplicado (Criterio RF01)."""
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Ya existe un usuario con este correo electrónico."
            )
        return value.lower()

    def validate(self, attrs):
        """Validar que las contraseñas coincidan."""
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        return attrs

    def create(self, validated_data):
        """Delega la creación al services layer."""
        return create_user(validated_data)


# =============================================================================
# RF02 — Autenticación de Usuarios
# =============================================================================


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado de JWT que incluye datos del usuario en la respuesta.

    Criterios de aceptación RF02:
    - Solo usuarios registrados y activos pueden autenticarse.
    - El token expira después de un tiempo definido.
    - Se registran los intentos de login (exitosos y fallidos).
    """

    @classmethod
    def get_token(cls, user):
        """Agrega claims personalizados al JWT (rol del usuario)."""
        token = super().get_token(user)
        token["role"] = user.role
        token["username"] = user.username
        token["email"] = user.email
        return token

    def validate(self, attrs):
        """Valida credenciales y registra el intento de login via services."""
        request = self.context.get("request")
        ip_address = get_client_ip(request) if request else None
        username = attrs.get("username", "")

        try:
            data = super().validate(attrs)
        except Exception as e:
            log_login_attempt(username, ip_address, success=False)
            raise e

        user = self.user
        log_login_attempt(username, ip_address, success=True, user=user)

        data["user"] = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "role_display": user.get_role_display(),
        }

        return data


# =============================================================================
# RF04 — Actualización de perfil
# =============================================================================


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualización de perfil (RF04)."""

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "email", "phone_number", "photo"]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer para cambio de contraseña (RF03)."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)


class LoginAttemptSerializer(serializers.ModelSerializer):
    """Serializer para bitácora de login (RF05)."""

    class Meta:
        model = LoginAttempt
        fields = [
            "id",
            "user",
            "username_attempted",
            "ip_address",
            "was_successful",
            "timestamp",
        ]
        read_only_fields = ["id", "timestamp"]


# =============================================================================
# RF06 — Recuperación de contraseña por email
# =============================================================================


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    RF06 — Solicitud de recuperación de contraseña.

    Valida que el correo exista en el sistema.
    Siempre retorna 200 (no revela si el email existe o no por seguridad).
    """

    email = serializers.EmailField(
        help_text="Correo electrónico registrado en el sistema."
    )

    def validate_email(self, value):
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    RF06 — Confirmación del reset con nuevo password.

    Valida el token HMAC y aplica las reglas de contraseña.
    """

    uid = serializers.CharField(help_text="UID de usuario codificado en base64.")
    token = serializers.CharField(help_text="Token de recuperación.")
    new_password = serializers.CharField(
        min_length=8,
        write_only=True,
        style={"input_type": "password"},
        help_text="Nueva contraseña (mínimo 8 caracteres).",
    )
    new_password_confirm = serializers.CharField(
        min_length=8,
        write_only=True,
        style={"input_type": "password"},
        help_text="Repite la nueva contraseña.",
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Las contraseñas no coinciden."}
            )
        return attrs
