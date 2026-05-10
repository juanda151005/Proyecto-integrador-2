from django.db import models
from apps.core_business.models import Client


class NotificationLog(models.Model):
    """
    RF15 — Log de notificaciones enviadas a clientes.
    Registra ofertas enviadas por WhatsApp/SMS y su estado.
    """

    class ChannelChoices(models.TextChoices):
        WHATSAPP = "WHATSAPP", "WhatsApp"
        SMS = "SMS", "SMS"

    class StatusChoices(models.TextChoices):
        SENT = "SENT", "Enviada"
        ACCEPTED = "ACCEPTED", "Aceptada"
        REJECTED = "REJECTED", "Rechazada"
        FAILED = "FAILED", "Fallida"

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Cliente",
    )
    message = models.TextField(verbose_name="Mensaje enviado")
    channel = models.CharField(
        max_length=10,
        choices=ChannelChoices.choices,
        verbose_name="Canal",
    )
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.SENT,
        verbose_name="Estado",
    )
    external_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ID externo (Twilio SID)",
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de envío")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Log de notificación"
        verbose_name_plural = "Logs de notificaciones"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"[{self.get_channel_display()}] {self.client.phone_number} — {self.get_status_display()}"


class Conversation(models.Model):
    """
    Conversación iniciada tras el envío de una notificación.
    Registra la respuesta del cliente (Sí/No), el estado del chat y el asesor asignado.
    """

    class StatusChoices(models.TextChoices):
        OPEN = "OPEN", "Abierta"
        CLOSED = "CLOSED", "Cerrada"

    class ResponseChoices(models.TextChoices):
        YES = "YES", "Sí me interesa"
        NO = "NO", "No, gracias"

    notification = models.OneToOneField(
        NotificationLog,
        on_delete=models.CASCADE,
        related_name="conversation",
        verbose_name="Notificación origen",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="Cliente",
    )
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.OPEN,
        verbose_name="Estado del chat",
    )
    client_response = models.CharField(
        max_length=5,
        choices=ResponseChoices.choices,
        blank=True,
        verbose_name="Respuesta del cliente",
    )
    had_response = models.BooleanField(
        default=False,
        verbose_name="¿El cliente respondió?",
    )
    advisor = models.ForeignKey(
        "users.CustomUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_conversations",
        verbose_name="Asesor asignado",
    )
    notes = models.TextField(blank=True, verbose_name="Notas del asesor")
    opened_at = models.DateTimeField(auto_now_add=True, verbose_name="Abierta el")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Cerrada el")

    class Meta:
        verbose_name = "Conversación"
        verbose_name_plural = "Conversaciones"
        ordering = ["-opened_at"]

    def __str__(self):
        resp = self.get_client_response_display() if self.client_response else "Sin respuesta"
        return f"{self.client.phone_number} — {self.get_status_display()} — {resp}"
