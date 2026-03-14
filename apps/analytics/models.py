from django.db import models
from apps.core_business.models import Client


class TopUp(models.Model):
    """
    Recarga de un cliente prepago.
    RF11 — Registro de recargas.
    """

    class ChannelChoices(models.TextChoices):
        ONLINE = 'ONLINE', 'En línea'
        STORE = 'STORE', 'Tienda física'
        ATM = 'ATM', 'Cajero automático'
        APP = 'APP', 'Aplicación móvil'

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='topups',
        verbose_name='Cliente',
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Monto',
    )
    date = models.DateField(verbose_name='Fecha de recarga')
    channel = models.CharField(
        max_length=10,
        choices=ChannelChoices.choices,
        default=ChannelChoices.ONLINE,
        verbose_name='Canal',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Recarga'
        verbose_name_plural = 'Recargas'
        ordering = ['-date']

    def __str__(self):
        return f'{self.client.phone_number} — ${self.amount} ({self.date})'


class ClientChangeLog(models.Model):
    """
    RF18 — Consulta de historial de cambios del cliente.
    Registra cada modificación realizada sobre un cliente.
    """
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='change_logs',
        verbose_name='Cliente',
    )
    field_name = models.CharField(max_length=100, verbose_name='Campo modificado')
    old_value = models.TextField(blank=True, verbose_name='Valor anterior')
    new_value = models.TextField(blank=True, verbose_name='Valor nuevo')
    changed_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Modificado por',
    )
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de cambio')

    class Meta:
        verbose_name = 'Historial de cambio'
        verbose_name_plural = 'Historial de cambios'
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.client} — {self.field_name}: {self.old_value} → {self.new_value}'
