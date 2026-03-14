from rest_framework import serializers
from .models import TopUp, ClientChangeLog


class TopUpSerializer(serializers.ModelSerializer):
    """Serializer para registro y lectura de recargas (RF11)."""
    client_phone = serializers.CharField(source='client.phone_number', read_only=True)

    class Meta:
        model = TopUp
        fields = [
            'id', 'client', 'client_phone', 'amount',
            'date', 'channel', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class EligibilityResultSerializer(serializers.Serializer):
    """Serializer para resultado del motor de elegibilidad (RF13)."""
    client_id = serializers.IntegerField()
    phone_number = serializers.CharField()
    full_name = serializers.CharField()
    average_spending = serializers.DecimalField(max_digits=12, decimal_places=2)
    is_eligible = serializers.BooleanField()
    reason = serializers.CharField()


class ClientChangeLogSerializer(serializers.ModelSerializer):
    """Serializer para historial de cambios del cliente (RF18)."""
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True)

    class Meta:
        model = ClientChangeLog
        fields = [
            'id', 'client', 'field_name', 'old_value', 'new_value',
            'changed_by', 'changed_by_username', 'changed_at',
        ]
        read_only_fields = ['id', 'changed_at']


class AverageSpendingSerializer(serializers.Serializer):
    """Serializer para resultado de cálculo de gasto promedio (RF12)."""
    client_id = serializers.IntegerField()
    phone_number = serializers.CharField()
    average_spending = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_topups = serializers.IntegerField()
    months_analyzed = serializers.IntegerField()
