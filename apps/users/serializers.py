from rest_framework import serializers
from .models import CustomUser, LoginAttempt


class UserSerializer(serializers.ModelSerializer):
    """Serializer de lectura para usuarios."""

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone_number', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer para registro de usuarios (RF01)."""
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'password',
            'first_name', 'last_name', 'role', 'phone_number',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user


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
