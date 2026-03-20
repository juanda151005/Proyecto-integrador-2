from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser, LoginAttempt


# =============================================================================
# RF01 — Gestión de Usuarios y Roles
# =============================================================================

class UserSerializer(serializers.ModelSerializer):
    """Serializer de lectura para usuarios."""
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'phone_number', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para registro de usuarios (RF01).

    Validaciones:
    - Email único (validado a nivel de modelo Y serializer)
    - Contraseña mínima 8 caracteres
    - Rol obligatorio (ADMIN, ANALYST, AGENT)
    - Username obligatorio
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='Mínimo 8 caracteres.',
    )
    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text='Repita la contraseña.',
    )
    role = serializers.ChoiceField(
        choices=CustomUser.Role.choices,
        help_text='Rol del usuario: ADMIN, ANALYST o AGENT.',
    )

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'phone_number',
        ]

    def validate_email(self, value):
        """Validar que el email no esté duplicado (Criterio de aceptación RF01)."""
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'Ya existe un usuario con este correo electrónico.'
            )
        return value.lower()

    def validate(self, attrs):
        """Validar que las contraseñas coincidan."""
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden.'
            })
        return attrs

    def create(self, validated_data):
        """Crear usuario con contraseña hasheada (encriptación segura)."""
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)  # Hashea con PBKDF2 (Django default) o BCrypt
        user.save()
        return user


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
        # Claims adicionales dentro del token
        token['role'] = user.role
        token['username'] = user.username
        token['email'] = user.email
        return token

    def validate(self, attrs):
        """
        Valida credenciales y registra el intento de login.
        Solo permite acceso a usuarios activos.
        """
        # Obtener IP del request
        request = self.context.get('request')
        ip_address = self._get_client_ip(request) if request else None
        username = attrs.get('username', '')

        try:
            data = super().validate(attrs)
        except Exception as e:
            # Login FALLIDO — registrar intento
            self._log_attempt(username, ip_address, success=False)
            raise e

        # Login EXITOSO — registrar intento
        user = self.user
        self._log_attempt(username, ip_address, success=True, user=user)

        # Agregar información del usuario a la respuesta JSON
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'role_display': user.get_role_display(),
        }

        return data

    def _log_attempt(self, username, ip_address, success, user=None):
        """Registra un intento de inicio de sesión en la bitácora."""
        LoginAttempt.objects.create(
            user=user,
            username_attempted=username,
            ip_address=ip_address,
            was_successful=success,
        )

    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


# =============================================================================
# RF04 — Actualización de perfil (esqueleto para Persona 1)
# =============================================================================

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualización de perfil (RF04)."""

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number']


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer para cambio de contraseña (RF03)."""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)


class LoginAttemptSerializer(serializers.ModelSerializer):
    """Serializer para bitácora de login (RF05)."""

    class Meta:
        model = LoginAttempt
        fields = [
            'id', 'user', 'username_attempted', 'ip_address',
            'was_successful', 'timestamp',
        ]
        read_only_fields = ['id', 'timestamp']
