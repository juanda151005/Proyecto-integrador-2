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
    """Serializer para reportes de conversión y métricas del sistema (RF17)."""

    # Clientes
    total_clients = serializers.IntegerField()
    active_clients = serializers.IntegerField(default=0)
    inactive_clients = serializers.IntegerField(default=0)
    eligible_clients = serializers.IntegerField()
    migrated_clients = serializers.IntegerField()
    # RF17: % clientes migrados entre los que recibieron oferta (contactados)
    conversion_rate = serializers.FloatField()
    migrated_among_contacted = serializers.IntegerField(default=0)
    migration_rate_vs_contacted = serializers.FloatField(default=0.0)
    average_spending_global = serializers.FloatField(default=0.0)

    # RF17 — Alcance de campaña
    customers_contacted = serializers.IntegerField(default=0)
    offers_sent = serializers.IntegerField(default=0)

    # RF17 — Tasas sobre respuestas Sí / No (conversaciones con respuesta)
    acceptance_rate = serializers.FloatField(default=0.0)
    rejection_rate = serializers.FloatField(default=0.0)
    responses_total = serializers.IntegerField(default=0)

    # Notificaciones
    total_notifications = serializers.IntegerField(default=0)
    accepted = serializers.IntegerField()
    rejected = serializers.IntegerField()
    pending = serializers.IntegerField()
    failed = serializers.IntegerField(default=0)
    response_rate = serializers.FloatField(default=0.0)

    # Conversaciones / flujo asesor
    open_conversations = serializers.IntegerField(default=0)
    closed_conversations = serializers.IntegerField(default=0)
    interested = serializers.IntegerField(default=0)
    not_interested = serializers.IntegerField(default=0)
