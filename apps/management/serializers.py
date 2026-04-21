from rest_framework import serializers

from .models import AuditLog, BusinessRule, GlobalSystemSettings


class GlobalSystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSystemSettings
        fields = [
            "id",
            "analysis_interval_minutes",
            "twilio_daily_message_limit",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class BusinessRuleSerializer(serializers.ModelSerializer):
    """Serializer para reglas de negocio (RF16)."""

    class Meta:
        model = BusinessRule
        fields = [
            "id",
            "key",
            "value",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer para bitácora de auditoría (RF14). Solo lectura (inmutable)."""

    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "user_username",
            "action",
            "model_name",
            "object_id",
            "changes",
            "ip_address",
            "timestamp",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_username",
            "action",
            "model_name",
            "object_id",
            "changes",
            "ip_address",
            "timestamp",
        ]


class ConversionReportSerializer(serializers.Serializer):
    """Serializer para reportes de conversión (RF17)."""

    total_clients = serializers.IntegerField()
    eligible_clients = serializers.IntegerField()
    migrated_clients = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    accepted = serializers.IntegerField()
    rejected = serializers.IntegerField()
    pending = serializers.IntegerField()
    average_spending_global = serializers.FloatField(required=False)
