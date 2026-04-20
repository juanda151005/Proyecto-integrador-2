from rest_framework import serializers
from .models import NotificationLog


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
    """Serializer para enviar una notificación libre a un cliente."""

    client_id = serializers.IntegerField()
    channel = serializers.ChoiceField(choices=NotificationLog.ChannelChoices.choices)
    message = serializers.CharField(max_length=1000)


class BulkNotificationSerializer(serializers.Serializer):
    """RF15 — Serializer para envío masivo de ofertas a elegibles."""

    channel = serializers.ChoiceField(
        choices=NotificationLog.ChannelChoices.choices,
        default=NotificationLog.ChannelChoices.WHATSAPP,
    )
