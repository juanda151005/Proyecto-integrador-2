from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.analytics.models import TopUp
from apps.analytics.services import EligibilityEngine
from apps.core_business.models import Client
from apps.communications.models import Conversation, NotificationLog
from apps.management.models import AuditLog, BusinessRule
from apps.users.models import CustomUser

# Persona 4 — Tests para RF14, RF16, RF17

MANAGEMENT_RULES_URL = "/api/v1/management/rules/"
AUDIT_LOGS_URL = "/api/v1/management/audit-logs/"
CONVERSION_REPORT_URL = "/api/v1/management/reports/conversion/"
CLIENTS_API = "/api/v1/clients/"


def make_admin_user(username="admin_test"):
    return CustomUser.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="TestPass123*",
        role=CustomUser.Role.ADMIN,
    )


def make_client(phone="3001234567"):
    return Client.objects.create(
        phone_number=phone,
        full_name="Cliente Test",
        document_number=f"DOC-{phone}",
        activation_date="2025-01-01",
        current_plan=Client.PlanChoices.PREPAGO_BASIC,
        status=Client.StatusChoices.ACTIVE,
    )


class BusinessRuleRF16Test(TestCase):
    """RF16: Configuración de parámetros generales (BusinessRule)."""

    def setUp(self):
        self.client_api = APIClient()
        self.admin_user = make_admin_user()

    def test_admin_can_create_business_rule_and_threshold_applies(self):
        """RF16 - Un admin crea una regla y el motor utiliza el valor dinámico."""
        self.client_api.force_authenticate(user=self.admin_user)

        print("Paso 1: crear regla y comprobar 201")
        response = self.client_api.post(
            MANAGEMENT_RULES_URL,
            {
                "key": "MIN_AVERAGE_SPENDING",
                "value": "65000.00",
                "description": "Umbral mínimo de gasto promedio",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        rule = BusinessRule.objects.get(key="MIN_AVERAGE_SPENDING")
        self.assertEqual(rule.value, "65000.00")

        print("Paso 2: evaluación inicial is_eligible=False")
        # Escenario con promedio 60000 -> no elegible
        client = make_client(phone="3009876543")
        TopUp.objects.create(
            client=client,
            amount=60000,
            date="2025-01-15",
            channel=TopUp.ChannelChoices.APP,
        )
        TopUp.objects.create(
            client=client,
            amount=60000,
            date="2025-02-15",
            channel=TopUp.ChannelChoices.APP,
        )
        TopUp.objects.create(
            client=client,
            amount=60000,
            date="2025-03-15",
            channel=TopUp.ChannelChoices.APP,
        )

        result = EligibilityEngine.evaluate_client(client)
        self.assertFalse(result["is_eligible"])

        print("Paso 3: actualizar regla y re-evaluación is_eligible=True")
        # Actualizar regla y re-evaluar
        response = self.client_api.patch(
            f"{MANAGEMENT_RULES_URL}{rule.id}/",
            {"value": "55000.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        result = EligibilityEngine.evaluate_client(client)
        self.assertTrue(result["is_eligible"])

    def test_non_admin_cannot_create_business_rule(self):
        """RF16 - Un usuario no admin no puede crear reglas de negocio."""
        non_admin = CustomUser.objects.create_user(
            username="analyst_test",
            email="analyst_test@test.com",
            password="TestPass123*",
            role=CustomUser.Role.ANALYST,
        )
        self.client_api.force_authenticate(user=non_admin)

        response = self.client_api.post(
            MANAGEMENT_RULES_URL,
            {
                "key": "MIN_AVERAGE_SPENDING",
                "value": "40000.00",
                "description": "Umbral mínimo de gasto promedio",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AuditLogRF14Tests(TestCase):
    """RF14 — Bitácora inmutable y registro tras operaciones críticas."""

    def setUp(self):
        self.admin = make_admin_user("admin_audit")
        self.client_api = APIClient()
        self.client_api.force_authenticate(user=self.admin)

        self.analyst = CustomUser.objects.create_user(
            username="analyst_audit",
            email="analyst_audit@test.com",
            password="TestPass123*",
            role=CustomUser.Role.ANALYST,
        )
        analista_group, _ = Group.objects.get_or_create(name="Analista")
        self.analyst.groups.add(analista_group)
        self.analyst_api = APIClient()
        self.analyst_api.force_authenticate(user=self.analyst)

    def test_cp_1_1_audit_after_client_delete(self):
        """
        CP 1.1: Tras eliminar un cliente con éxito, se genera un registro con
        usuario, acción, fecha y estado antes/después (antes = snapshot, después = null).
        """
        c = make_client(phone="3004455667")
        url = f"{CLIENTS_API}{c.pk}/"
        response = self.analyst_api.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        log = AuditLog.objects.get(model_name="Client", object_id=str(c.pk))
        self.assertEqual(log.action, AuditLog.ActionChoices.DELETE)
        self.assertEqual(log.user, self.analyst)
        self.assertIn("before", log.changes)
        self.assertIsNone(log.changes.get("after"))
        self.assertEqual(log.changes["before"]["phone_number"], "3004455667")

    def test_cp_1_1_audit_after_client_update(self):
        """Modificar cliente genera bitácora con before/after."""
        c = make_client(phone="3004455777")
        url = f"{CLIENTS_API}{c.pk}/"
        response = self.analyst_api.patch(
            url,
            {"full_name": "Cliente Editado"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        log = AuditLog.objects.filter(
            model_name="Client",
            object_id=str(c.pk),
            action=AuditLog.ActionChoices.UPDATE,
        ).latest("timestamp")
        self.assertEqual(log.user, self.analyst)
        self.assertEqual(log.changes["before"]["full_name"], "Cliente Test")
        self.assertEqual(log.changes["after"]["full_name"], "Cliente Editado")

    def test_cp_1_1_audit_after_business_rule_update(self):
        """Regla de negocio actualizada: bitácora con antes/después."""
        response = self.client_api.post(
            MANAGEMENT_RULES_URL,
            {
                "key": "RULE_AUDIT_TEST",
                "value": "100",
                "description": "test",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        rule_id = response.data["id"]

        self.client_api.patch(
            f"{MANAGEMENT_RULES_URL}{rule_id}/",
            {"value": "200"},
            format="json",
        )

        log = AuditLog.objects.filter(
            model_name="BusinessRule",
            object_id=str(rule_id),
            action=AuditLog.ActionChoices.UPDATE,
        ).latest("timestamp")
        self.assertIn("before", log.changes)
        self.assertIn("after", log.changes)
        self.assertEqual(log.changes["before"]["value"], "100")
        self.assertEqual(log.changes["after"]["value"], "200")

    def test_cp_1_2_api_cannot_create_audit_via_post(self):
        """La API no expone creación manual de bitácora (solo lectura)."""
        response = self.client_api.post(
            AUDIT_LOGS_URL,
            {"action": "DELETE", "model_name": "X"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_only_admin_can_list_audit_logs(self):
        """RF14 — Solo rol Administrador puede consultar la lista (no Analista)."""
        response = self.analyst_api.get(AUDIT_LOGS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        ok = self.client_api.get(AUDIT_LOGS_URL)
        self.assertEqual(ok.status_code, status.HTTP_200_OK)

    def test_cp_1_2_audit_entry_cannot_be_updated_or_deleted_in_db(self):
        """CP 1.2: No se puede editar ni borrar un registro de auditoría."""
        self.client_api.post(
            MANAGEMENT_RULES_URL,
            {
                "key": "RULE_IMMUTABLE",
                "value": "1",
                "description": "x",
                "is_active": True,
            },
            format="json",
        )
        entry = AuditLog.objects.latest("timestamp")

        entry.model_name = "tampered"
        with self.assertRaises(ValidationError):
            entry.save()

        with self.assertRaises(ValidationError):
            entry.delete()

        with self.assertRaises(ValidationError):
            AuditLog.objects.filter(pk=entry.pk).delete()

        self.assertTrue(AuditLog.objects.filter(pk=entry.pk).exists())


class ConversionReportRF17Test(TestCase):
    """RF17 — Dashboard de conversión: tasas Sí/No, contactados vs ofertas, migración / contactados."""

    def setUp(self):
        self.api = APIClient()
        self.admin = make_admin_user("admin_rf17")
        self.api.force_authenticate(user=self.admin)

    def _log(self, client, status=NotificationLog.StatusChoices.SENT):
        return NotificationLog.objects.create(
            client=client,
            message="Oferta test",
            channel=NotificationLog.ChannelChoices.WHATSAPP,
            status=status,
        )

    def test_conversion_report_metrics(self):
        """
        Tres clientes contactados, cuatro envíos exitosos; un migrado entre contactados;
        tasas de aceptación/rechazo sobre respuestas Sí/No.
        """
        c1 = make_client("3001111111")
        c2 = make_client("3002222222")
        c3 = make_client("3003333333")

        self._log(c1)
        self._log(c1)
        self._log(c2)
        n3 = self._log(c3)

        Conversation.objects.create(
            notification=n3,
            client=c3,
            status=Conversation.StatusChoices.CLOSED,
            client_response=Conversation.ResponseChoices.NO,
            had_response=True,
        )

        n2 = NotificationLog.objects.filter(client=c2).first()
        Conversation.objects.create(
            notification=n2,
            client=c2,
            status=Conversation.StatusChoices.OPEN,
            client_response=Conversation.ResponseChoices.YES,
            had_response=True,
        )

        c3.status = Client.StatusChoices.MIGRATED
        c3.save(update_fields=["status"])

        r = self.api.get(CONVERSION_REPORT_URL)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["customers_contacted"], 3)
        self.assertEqual(r.data["offers_sent"], 4)
        self.assertEqual(r.data["migrated_among_contacted"], 1)
        self.assertEqual(r.data["migration_rate_vs_contacted"], 33.33)
        self.assertEqual(r.data["responses_total"], 2)
        self.assertEqual(r.data["acceptance_rate"], 50.0)
        self.assertEqual(r.data["rejection_rate"], 50.0)
        self.assertEqual(r.data["conversion_rate"], r.data["migration_rate_vs_contacted"])

    def test_unauthenticated_cannot_access_conversion_report(self):
        bare = APIClient()
        r = bare.get(CONVERSION_REPORT_URL)
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)
