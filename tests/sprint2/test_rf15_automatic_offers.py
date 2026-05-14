"""
RF15 — Envío automático de ofertas de migración vía WhatsApp/SMS (Twilio).

CP 1.1 (Integration): Al marcarse un cliente como "Elegible", el sistema
                      invoca el SDK de Twilio y envía la oferta al número
                      del cliente en formato E.164.
CP 1.2 (Unit):        El sistema omite el envío y registra el error cuando
                      el número del cliente no puede formatearse a E.164,
                      sin interrumpir el procesamiento de los demás.
CP 2.1 (Integration): Tras la confirmación de Twilio, se genera el registro
                      en NotificationLog con canal, cliente, fecha y estado
                      "Enviado exitosamente".
CP 2.1 RF14 (Integration): Cada envío de oferta (exitoso o fallido) genera
                      también un AuditLog con action=NOTIFICATION_SENT.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group
from django.test import TestCase

from apps.communications.models import NotificationLog
from apps.communications.services import TwilioService
from apps.core_business.models import Client
from apps.management.models import AuditLog
from apps.users.models import CustomUser


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_analyst(username="analista_rf15", email="analista_rf15@test.com"):
    user = CustomUser.objects.create_user(
        username=username,
        email=email,
        password="Pass1234!",
        role=CustomUser.Role.ANALYST,
    )
    group, _ = Group.objects.get_or_create(name="Analista")
    user.groups.add(group)
    return user


def _make_client(phone, document=None, is_eligible=False):
    return Client.objects.create(
        phone_number=phone,
        full_name="Cliente RF15 Test",
        document_number=document or f"DOC-RF15-{phone}",
        email=f"{phone}@rf15test.com",
        activation_date=date(2025, 1, 1),
        current_plan=Client.PlanChoices.PREPAGO_PLUS,
        status=Client.StatusChoices.ACTIVE,
        average_spending=Decimal("70000.00"),
        is_eligible=is_eligible,
    )


def _mock_twilio_success(sid="SMTEST12345"):
    """Retorna un mock de mensaje Twilio con éxito."""
    msg = MagicMock()
    msg.sid = sid
    return msg


# ══════════════════════════════════════════════════════════════════════════════
# CP 1.1 — Envío al marcarse cliente como elegible (disparador automático)
# ══════════════════════════════════════════════════════════════════════════════


class RF15CP11EnvioAlMarcarsElegibleTest(TestCase):
    """
    CP 1.1 — El disparador automático (señal pre_save) invoca TwilioService
    y envía la oferta al número del cliente en formato E.164 (+57)
    cuando pasa a estado is_eligible=True.

    Tipo: Prueba de Integración (señal → servicio → Twilio mockeado).
    """

    def setUp(self):
        self.cliente = _make_client("3150000001", is_eligible=False)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_marcar_elegible_dispara_envio_de_oferta(self, mock_get_client):
        """
        Al cambiar is_eligible de False a True y guardar,
        la señal pre_save debe haber invocado el envío de la oferta.
        """
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success()
        mock_get_client.return_value = mock_twilio_client

        self.cliente.is_eligible = True
        self.cliente.save()

        # El cliente de Twilio debe haber sido invocado para crear un mensaje
        self.assertTrue(mock_twilio_client.messages.create.called)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_numero_enviado_tiene_formato_e164_con_prefijo_57(self, mock_get_client):
        """
        El número enviado a Twilio debe estar en formato E.164 (+57XXXXXXXXXX).
        """
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success()
        mock_get_client.return_value = mock_twilio_client

        self.cliente.is_eligible = True
        self.cliente.save()

        call_kwargs = mock_twilio_client.messages.create.call_args
        # El número destino debe empezar con +57
        to_number = call_kwargs.kwargs.get("to") or call_kwargs[1].get("to") or call_kwargs[0][2]
        # Para WhatsApp viene como "whatsapp:+57XXXXXXXXXX"
        self.assertIn("+573150000001", str(to_number))

    @patch("apps.communications.services.TwilioService._get_client")
    def test_marcar_elegible_crea_notification_log(self, mock_get_client):
        """
        Al marcar el cliente como elegible, se debe crear un registro
        en NotificationLog asociado al cliente.
        """
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_CP11")
        mock_get_client.return_value = mock_twilio_client

        self.cliente.is_eligible = True
        self.cliente.save()

        logs = NotificationLog.objects.filter(client=self.cliente)
        self.assertEqual(logs.count(), 1)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_doble_guardado_elegible_no_duplica_envio(self, mock_get_client):
        """
        Si el cliente ya es elegible y se vuelve a guardar con is_eligible=True,
        la señal NO debe disparar un segundo envío (solo cuando cambia False→True).
        """
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success()
        mock_get_client.return_value = mock_twilio_client

        # Primer guardado: False → True (debe disparar)
        self.cliente.is_eligible = True
        self.cliente.save()

        count_after_first = NotificationLog.objects.filter(client=self.cliente).count()

        # Segundo guardado: True → True (NO debe disparar)
        self.cliente.is_eligible = True
        self.cliente.save()

        count_after_second = NotificationLog.objects.filter(client=self.cliente).count()

        self.assertEqual(count_after_first, count_after_second)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_cliente_nuevo_con_is_eligible_true_no_dispara_oferta(self, mock_get_client):
        """
        Crear un cliente nuevo directamente con is_eligible=True
        no debe disparar la señal (solo aplica para transiciones).
        """
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success()
        mock_get_client.return_value = mock_twilio_client

        # Crear con is_eligible=True (nuevo registro, no transición)
        _make_client("3150000099", document="DOC-NUEVO-ELIG", is_eligible=True)

        self.assertFalse(mock_twilio_client.messages.create.called)


# ══════════════════════════════════════════════════════════════════════════════
# CP 1.2 — Número con formato inválido → omitir envío, registrar error
# ══════════════════════════════════════════════════════════════════════════════


class RF15CP12NumeroFormatoInvalidoTest(TestCase):
    """
    CP 1.2 — Cuando el número del cliente no puede formatearse a E.164,
    el sistema omite el envío y registra el error sin interrumpir
    el procesamiento de los demás clientes elegibles.

    Tipo: Prueba Unitaria sobre TwilioService.send_sms / send_whatsapp.
    """

    def setUp(self):
        # Cliente con número colombiano válido (10 dígitos, empieza con 3)
        self.cliente_valido = _make_client("3150000002", document="DOC-VAL")

    @patch("apps.communications.services.TwilioService._get_client")
    def test_error_twilio_en_envio_devuelve_success_false(self, mock_get_client):
        """
        Cuando Twilio lanza una excepción (simula número inválido rechazado),
        send_whatsapp retorna {'success': False, 'error': ...}.
        """
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.side_effect = Exception(
            "The 'To' number +57999 is not a valid phone number."
        )
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        resultado = service.send_whatsapp(self.cliente_valido.phone_number, "Oferta test")

        self.assertFalse(resultado["success"])
        self.assertIn("error", resultado)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_error_en_envio_crea_notification_log_con_status_failed(self, mock_get_client):
        """
        Cuando el envío falla, send_whatsapp_offer debe crear un NotificationLog
        con status=FAILED en lugar de lanzar una excepción no controlada.
        """
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.side_effect = Exception("Número inválido")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        resultado = service.send_whatsapp_offer(self.cliente_valido)

        self.assertFalse(resultado["success"])

        log = NotificationLog.objects.get(pk=resultado["log_id"])
        self.assertEqual(log.status, NotificationLog.StatusChoices.FAILED)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_fallo_en_un_cliente_no_interrumpe_procesamiento_del_siguiente(
        self, mock_get_client
    ):
        """
        CP 1.2 esencial: un error en el envío a un cliente no debe
        interrumpir el proceso para los demás.
        La señal captura Exception y continúa sin relanzar.
        """
        # Twilio falla siempre
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.side_effect = Exception("Error de red")
        mock_get_client.return_value = mock_twilio_client

        cliente_a = _make_client("3150000003", document="DOC-A", is_eligible=False)
        cliente_b = _make_client("3150000004", document="DOC-B", is_eligible=False)

        try:
            # Ambos clientes pasan a elegibles → la señal se dispara dos veces
            cliente_a.is_eligible = True
            cliente_a.save()

            cliente_b.is_eligible = True
            cliente_b.save()
        except Exception as exc:
            self.fail(
                f"La señal propagó una excepción que no debía propagarse: {exc}"
            )

        # Ambos clientes deben tener un NotificationLog con FAILED
        self.assertEqual(
            NotificationLog.objects.filter(client=cliente_a, status=NotificationLog.StatusChoices.FAILED).count(),
            1,
        )
        self.assertEqual(
            NotificationLog.objects.filter(client=cliente_b, status=NotificationLog.StatusChoices.FAILED).count(),
            1,
        )

    @patch("apps.communications.services.TwilioService._get_client")
    def test_resultado_error_contiene_descripcion_del_fallo(self, mock_get_client):
        """El dict de resultado con error incluye el campo 'error' con texto descriptivo."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.side_effect = Exception("Número E.164 inválido")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        resultado = service.send_sms(self.cliente_valido.phone_number, "Test")

        self.assertIn("error", resultado)
        self.assertGreater(len(resultado["error"]), 0)


# ══════════════════════════════════════════════════════════════════════════════
# CP 2.1 — Registro en bitácora (NotificationLog) tras envío exitoso
# ══════════════════════════════════════════════════════════════════════════════


class RF15CP21RegistroEnBitacoraTraEnvioExitosoTest(TestCase):
    """
    CP 2.1 — Tras la confirmación de Twilio, se genera el registro en
    NotificationLog con canal, cliente, fecha y estado "Enviado exitosamente".

    Tipo: Prueba de Integración (TwilioService → NotificationLog).
    """

    def setUp(self):
        self.cliente = _make_client("3150000005", document="DOC-RF15-LOG")

    @patch("apps.communications.services.TwilioService._get_client")
    def test_envio_exitoso_crea_notification_log(self, mock_get_client):
        """send_whatsapp_offer exitoso crea exactamente 1 NotificationLog."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_LOG01")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        resultado = service.send_whatsapp_offer(self.cliente)

        self.assertTrue(resultado["success"])
        self.assertEqual(NotificationLog.objects.filter(client=self.cliente).count(), 1)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_log_tiene_canal_whatsapp(self, mock_get_client):
        """El NotificationLog creado por send_whatsapp_offer tiene canal=WHATSAPP."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_LOG02")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        resultado = service.send_whatsapp_offer(self.cliente)

        log = NotificationLog.objects.get(pk=resultado["log_id"])
        self.assertEqual(log.channel, NotificationLog.ChannelChoices.WHATSAPP)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_log_tiene_status_sent_tras_envio_exitoso(self, mock_get_client):
        """El NotificationLog creado por send_whatsapp_offer exitoso tiene status=SENT."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_LOG03")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        resultado = service.send_whatsapp_offer(self.cliente)

        log = NotificationLog.objects.get(pk=resultado["log_id"])
        self.assertEqual(log.status, NotificationLog.StatusChoices.SENT)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_log_contiene_sid_de_twilio(self, mock_get_client):
        """El NotificationLog persiste el SID retornado por Twilio en external_id."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_LOGFINAL")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        resultado = service.send_whatsapp_offer(self.cliente)

        log = NotificationLog.objects.get(pk=resultado["log_id"])
        self.assertEqual(log.external_id, "SM_LOGFINAL")

    @patch("apps.communications.services.TwilioService._get_client")
    def test_log_esta_asociado_al_cliente_correcto(self, mock_get_client):
        """El NotificationLog está vinculado al cliente que recibió la oferta."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_LOG05")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        resultado = service.send_whatsapp_offer(self.cliente)

        log = NotificationLog.objects.get(pk=resultado["log_id"])
        self.assertEqual(log.client, self.cliente)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_log_tiene_fecha_de_envio_registrada(self, mock_get_client):
        """El NotificationLog tiene el campo sent_at con fecha de envío (no nulo)."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_LOG06")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        resultado = service.send_whatsapp_offer(self.cliente)

        log = NotificationLog.objects.get(pk=resultado["log_id"])
        self.assertIsNotNone(log.sent_at)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_log_tiene_mensaje_de_oferta_recordado(self, mock_get_client):
        """El NotificationLog persiste el mensaje que se envió al cliente."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_LOG07")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        resultado = service.send_whatsapp_offer(self.cliente)

        log = NotificationLog.objects.get(pk=resultado["log_id"])
        self.assertGreater(len(log.message), 0)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_envio_sms_exitoso_crea_log_con_canal_sms(self, mock_get_client):
        """send_sms_offer exitoso crea NotificationLog con canal=SMS."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_SMS01")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        resultado = service.send_sms_offer(self.cliente)

        self.assertTrue(resultado[\"success\"])
        log = NotificationLog.objects.get(pk=resultado["log_id"])
        self.assertEqual(log.channel, NotificationLog.ChannelChoices.SMS)


# ══════════════════════════════════════════════════════════════════════════════
# RF14 integration — AuditLog generado por cada envío de oferta
# ══════════════════════════════════════════════════════════════════════════════


class RF15RF14AuditLogPorEnvioTest(TestCase):
    """
    Integración RF14 ↔ RF15: cada envío de oferta (exitoso o fallido)
    debe generar automáticamente un AuditLog con action=NOTIFICATION_SENT.

    Tipo: Prueba de Integración (TwilioService → NotificationLog + AuditLog).
    """

    def setUp(self):
        self.cliente = _make_client("3150000006", document="DOC-RF14-INT")

    @patch("apps.communications.services.TwilioService._get_client")
    def test_envio_exitoso_genera_audit_log(self, mock_get_client):
        """send_whatsapp_offer exitoso crea un AuditLog con action=NOTIFICATION_SENT."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_AUDIT01")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        service.send_whatsapp_offer(self.cliente)

        audit = AuditLog.objects.filter(
            action=AuditLog.ActionChoices.NOTIFICATION_SENT,
            model_name="NotificationLog",
        ).first()
        self.assertIsNotNone(audit)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_audit_log_contiene_phone_number_del_cliente(self, mock_get_client):
        """El AuditLog de envío contiene el número de teléfono del cliente en el campo 'after'."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_AUDIT02")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        service.send_whatsapp_offer(self.cliente)

        audit = AuditLog.objects.filter(
            action=AuditLog.ActionChoices.NOTIFICATION_SENT
        ).latest("timestamp")
        self.assertIn("phone_number", audit.changes.get("after", {}))
        self.assertEqual(audit.changes["after"]["phone_number"], self.cliente.phone_number)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_audit_log_estado_enviado_exitosamente(self, mock_get_client):
        """El AuditLog generado por un envío exitoso contiene estado 'Enviado exitosamente'."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_AUDIT03")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        service.send_whatsapp_offer(self.cliente)

        audit = AuditLog.objects.filter(
            action=AuditLog.ActionChoices.NOTIFICATION_SENT
        ).latest("timestamp")
        self.assertIn("Enviado exitosamente", audit.changes["after"]["status"])

    @patch("apps.communications.services.TwilioService._get_client")
    def test_audit_log_contiene_canal_utilizado(self, mock_get_client):
        """El AuditLog incluye el canal (WHATSAPP o SMS) utilizado en el envío."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_AUDIT04")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        service.send_sms_offer(self.cliente)

        audit = AuditLog.objects.filter(
            action=AuditLog.ActionChoices.NOTIFICATION_SENT
        ).latest("timestamp")
        self.assertEqual(audit.changes["after"]["channel"], NotificationLog.ChannelChoices.SMS)

    @patch("apps.communications.services.TwilioService._get_client")
    def test_envio_fallido_tambien_genera_audit_log(self, mock_get_client):
        """
        Incluso cuando el envío falla, se genera un AuditLog con el estado
        de error para trazabilidad completa.
        """
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.side_effect = Exception("Número inválido")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        service.send_whatsapp_offer(self.cliente)

        audit = AuditLog.objects.filter(
            action=AuditLog.ActionChoices.NOTIFICATION_SENT
        ).first()
        self.assertIsNotNone(audit)
        # El estado debe reflejar el fallo
        self.assertIn("Fallido", audit.changes["after"]["status"])

    @patch("apps.communications.services.TwilioService._get_client")
    def test_audit_log_contiene_sid_de_twilio_en_envio_exitoso(self, mock_get_client):
        """El AuditLog registra el SID de Twilio cuando el envío fue exitoso."""
        mock_twilio_client = MagicMock()
        mock_twilio_client.messages.create.return_value = _mock_twilio_success("SM_AUDIT_SID")
        mock_get_client.return_value = mock_twilio_client

        service = TwilioService()
        service.send_whatsapp_offer(self.cliente)

        audit = AuditLog.objects.filter(
            action=AuditLog.ActionChoices.NOTIFICATION_SENT
        ).latest("timestamp")
        self.assertEqual(audit.changes["after"]["twilio_sid"], "SM_AUDIT_SID")
