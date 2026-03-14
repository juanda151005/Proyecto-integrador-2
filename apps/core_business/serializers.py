from rest_framework import serializers
from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    """Serializer completo de lectura para Client."""

    class Meta:
        model = Client
        fields = [
            'id', 'phone_number', 'full_name', 'document_number', 'email',
            'activation_date', 'current_plan', 'is_eligible',
            'average_spending', 'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_eligible', 'average_spending', 'created_at', 'updated_at']


class ClientCreateSerializer(serializers.ModelSerializer):
    """Serializer para creación de clientes prepago (RF06)."""

    class Meta:
        model = Client
        fields = [
            'id', 'phone_number', 'full_name', 'document_number',
            'email', 'activation_date', 'current_plan',
        ]


class ClientExportSerializer(serializers.ModelSerializer):
    """Serializer para exportación a CSV (RF10)."""

    class Meta:
        model = Client
        fields = [
            'phone_number', 'full_name', 'document_number',
            'activation_date', 'current_plan', 'is_eligible',
            'average_spending', 'status',
        ]
