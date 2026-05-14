from rest_framework import serializers
from .models import Conversation, NotificationLog


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de notificaciones (RF15)."""

    client_phone = serializers.CharField(source="client.phone_number", read_only=True)
    client_name = serializers.CharField(source="client.full_name", read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            "id",
            "client",
            "client_phone",
            "client_name",
            "message",
            "channel",
            "status",
            "external_id",
            "sent_at",
            "updated_at",
        ]
        read_only_fields = ["id", "external_id", "sent_at", "updated_at"]


class SendOfferSerializer(serializers.Serializer):
    """RF15 — Serializer para disparar la oferta personalizada a un cliente."""

    client_id = serializers.IntegerField()
    channel = serializers.ChoiceField(
        choices=NotificationLog.ChannelChoices.choices,
        default=NotificationLog.ChannelChoices.WHATSAPP,
    )


class SendNotificationSerializer(serializers.Serializer):
    """Serializer para enviar una notificación a un cliente."""

    client_id = serializers.IntegerField()
    channel = serializers.ChoiceField(choices=NotificationLog.ChannelChoices.choices)
    message = serializers.CharField(max_length=1000)


class BulkNotificationSerializer(serializers.Serializer):
    """Serializer para envío masivo de ofertas a elegibles (RF15)."""

    channel = serializers.ChoiceField(
        choices=NotificationLog.ChannelChoices.choices,
        default=NotificationLog.ChannelChoices.WHATSAPP,
    )


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer para conversaciones (flujo asesor / chat)."""

    client_phone = serializers.CharField(source="client.phone_number", read_only=True)
    client_name = serializers.CharField(source="client.full_name", read_only=True)
    notification_channel = serializers.CharField(source="notification.channel", read_only=True)
    advisor_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    response_display = serializers.CharField(
        source="get_client_response_display", read_only=True
    )

    def get_advisor_name(self, obj):
        if obj.advisor:
            return obj.advisor.get_full_name() or obj.advisor.username
        return None

    class Meta:
        model = Conversation
        fields = [
            "id",
            "notification",
            "client",
            "client_phone",
            "client_name",
            "notification_channel",
            "status",
            "status_display",
            "client_response",
            "response_display",
            "had_response",
            "advisor",
            "advisor_name",
            "notes",
            "opened_at",
            "closed_at",
        ]
        read_only_fields = [
            "id",
            "client",
            "notification",
            "client_response",
            "had_response",
            "opened_at",
        ]


class ConversationUpdateSerializer(serializers.ModelSerializer):
    """Permite al asesor actualizar estado, notas y cerrar la conversación."""

    class Meta:
        model = Conversation
        fields = ["status", "advisor", "notes", "closed_at"]
