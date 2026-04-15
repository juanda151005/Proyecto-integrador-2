import re

from rest_framework import serializers

from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    """Serializer completo de lectura para Client."""

    class Meta:
        model = Client
        fields = [
            "id",
            "phone_number",
            "full_name",
            "document_number",
            "email",
            "activation_date",
            "current_plan",
            "is_eligible",
            "average_spending",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_eligible",
            "average_spending",
            "created_at",
            "updated_at",
        ]


class ClientCreateSerializer(serializers.ModelSerializer):
    """Serializer para creación de clientes prepago (RF06)."""

    class Meta:
        model = Client
        fields = [
            "id",
            "phone_number",
            "full_name",
            "document_number",
            "email",
            "activation_date",
            "current_plan",
        ]
        read_only_fields = ["id"]

    def validate_phone_number(self, value):
        """Valida formato colombiano: 10 dígitos, empieza con 3."""
        if not re.match(r"^3\d{9}$", value):
            raise serializers.ValidationError(
                "El número debe tener 10 dígitos y empezar con 3. Ej: 3001234567"
            )
        return value


class ClientUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualización de clientes (RF08).
    Bloquea cambios a phone_number y document_number (datos de identidad).
    """

    class Meta:
        model = Client
        fields = [
            "id",
            "phone_number",
            "full_name",
            "document_number",
            "email",
            "activation_date",
            "current_plan",
            "is_eligible",
            "average_spending",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "phone_number",
            "document_number",
            "is_eligible",
            "average_spending",
            "created_at",
            "updated_at",
        ]


class ClientExportSerializer(serializers.ModelSerializer):
    """Serializer para exportación a CSV (RF10)."""

    class Meta:
        model = Client
        fields = [
            "phone_number",
            "full_name",
            "document_number",
            "email",
            "activation_date",
            "current_plan",
            "is_eligible",
            "average_spending",
            "status",
        ]
