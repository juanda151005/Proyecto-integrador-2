from django.db import models
from apps.core_business.models import Client


class NotificationLog(models.Model):
    """
    RF15 — Log de notificaciones enviadas a clientes.
    Registra ofertas enviadas por WhatsApp/SMS y su estado.
    """

    class ChannelChoices(models.TextChoices):
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
        SMS = 'SMS', 'SMS'

    class StatusChoices(models.TextChoices):
        SENT = 'SENT', 'Enviada'
        ACCEPTED = 'ACCEPTED', 'Aceptada'
        REJECTED = 'REJECTED', 'Rechazada'
        FAILED = 'FAILED', 'Fallida'

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Cliente',
    )
    message = models.TextField(verbose_name='Mensaje enviado')
    channel = models.CharField(
        max_length=10,
        choices=ChannelChoices.choices,
        verbose_name='Canal',
    )
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.SENT,
        verbose_name='Estado',
    )
    external_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='ID externo (Twilio SID)',
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de envío')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Log de notificación'
        verbose_name_plural = 'Logs de notificaciones'
        ordering = ['-sent_at']

    def __str__(self):
        return f'[{self.get_channel_display()}] {self.client.phone_number} — {self.get_status_display()}'
