"""
RF14 — Bitácora de operaciones críticas (Audit Logging).

CP 1.1 (Integration): Se genera automáticamente un registro completo de auditoría
                      tras operaciones críticas (eliminación o modificación de reglas).
CP 1.2 (Unit):        Los registros son inmutables: la API rechaza edición/borrado
                      y el modelo lanza ValidationError ante intentos directos.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.core_business.models import Client
from apps.management.audit import log_critical_action
from apps.management.models import AuditLog, BusinessRule
from apps.users.models import CustomUser

CLIENTS_URL = "/api/v1/clients/"
AUDIT_LOGS_URL = "/api/v1/management/audit-logs/"
MANAGEMENT_RULES_URL = "/api/v1/management/rules/"


def _make_admin(username="admin_rf14", email="admin_rf14@test.com"):
    user = CustomUser.objects.create_user(
        username=username,
        email=email,
        password="Pass1234!",
        role=CustomUser.Role.ADMIN,
    )
    group, _ = Group.objects.get_or_create(name="Administrador")
    user.groups.add(group)
    return user


def _make_analyst(username="analista_rf14", email="analista_rf14@test.com"):
    user = CustomUser.objects.create_user(
        username=username,
        email=email,
        password="Pass1234!",
        role=CustomUser.Role.ANALYST,
    )
    group, _ = Group.objects.get_or_create(name="Analista")
    user.groups.add(group)
    return user


def _make_client(phone, document=None):
    return Client.objects.create(
        phone_number=phone,
        full_name="Cliente Auditoría",
        document_number=document or f"DOC-{phone}",
        email=f"{phone}@audit.com",
        activation_date=date(2025, 3, 1),
        current_plan=Client.PlanChoices.PREPAGO_BASIC,
        status=Client.StatusChoices.ACTIVE,
        average_spending=Decimal("35000.00"),
    )


class RF14CP11GeneracionRegistroAuditoriaTest(TestCase):
    """
    CP 1.1 — Generación automática de registro de auditoría.
    Tras operaciones críticas (DELETE de cliente o UPDATE de regla de negocio),
    el sistema crea automáticamente un AuditLog con usuario, acción, fecha
    y snapshot antes/después.
    """

    def setUp(self):
        self.admin = _make_admin()
        self.analyst = _make_analyst()

        self.admin_api = APIClient()
        self.admin_api.force_authenticate(user=self.admin)

        self.analyst_api = APIClient()
        self.analyst_api.force_authenticate(user=self.analyst)

    def test_eliminacion_cliente_genera_audit_log(self):
        cliente = _make_client("3020000001")
        pk = str(cliente.pk)
        url = f"{CLIENTS_URL}{cliente.pk}/"

        self.analyst_api.delete(url)

        log = AuditLog.objects.get(model_name="Client", object_id=pk)
        self.assertEqual(log.action, AuditLog.ActionChoices.DELETE)

    def test_audit_log_eliminacion_contiene_usuario_responsable(self):
        cliente = _make_client("3020000002")
        url = f"{CLIENTS_URL}{cliente.pk}/"
        self.analyst_api.delete(url)

        log = AuditLog.objects.get(model_name="Client", object_id=str(cliente.pk))
        self.assertEqual(log.user, self.analyst)

    def test_audit_log_eliminacion_contiene_snapshot_before(self):
        cliente = _make_client("3020000003", document="DOC-SNAP")
        url = f"{CLIENTS_URL}{cliente.pk}/"
        self.analyst_api.delete(url)

        log = AuditLog.objects.get(model_name="Client", object_id=str(cliente.pk))
        self.assertIn("before", log.changes)
        self.assertEqual(log.changes["before"]["phone_number"], "3020000003")

    def test_audit_log_eliminacion_tiene_after_nulo(self):
        cliente = _make_client("3020000004")
        url = f"{CLIENTS_URL}{cliente.pk}/"
        self.analyst_api.delete(url)

        log = AuditLog.objects.get(model_name="Client", object_id=str(cliente.pk))
        self.assertNotIn("after", log.changes)

    def test_actualizacion_cliente_genera_audit_log_con_before_y_after(self):
        cliente = _make_client("3020000005")
        url = f"{CLIENTS_URL}{cliente.pk}/"
        self.analyst_api.patch(url, {"full_name": "Nombre Actualizado"}, format="json")

        log = AuditLog.objects.filter(
            model_name="Client",
            object_id=str(cliente.pk),
            action=AuditLog.ActionChoices.UPDATE,
        ).latest("timestamp")

        self.assertIn("before", log.changes)
        self.assertIn("after", log.changes)
        self.assertEqual(log.changes["before"]["full_name"], "Cliente Auditoría")
        self.assertEqual(log.changes["after"]["full_name"], "Nombre Actualizado")

    def test_modificacion_regla_negocio_genera_audit_log(self):
        resp = self.admin_api.post(
            MANAGEMENT_RULES_URL,
            {"key": "RF14_RULE_TEST", "value": "100", "description": "test", "is_active": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        rule_id = resp.data["id"]

        self.admin_api.patch(
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

    def test_audit_log_contiene_timestamp(self):
        cliente = _make_client("3020000006")
        url = f"{CLIENTS_URL}{cliente.pk}/"
        self.analyst_api.delete(url)

        log = AuditLog.objects.get(model_name="Client", object_id=str(cliente.pk))
        self.assertIsNotNone(log.timestamp)

    def test_log_critico_directo_via_servicio(self):
        """Verifica que log_critical_action crea el registro correctamente."""
        entry = log_critical_action(
            user=self.admin,
            action=AuditLog.ActionChoices.DELETE,
            model_name="TestModel",
            object_id="42",
            before={"campo": "valor_antes"},
            after=None,
        )
        self.assertIsNotNone(entry.pk)
        self.assertEqual(entry.action, AuditLog.ActionChoices.DELETE)
        self.assertEqual(entry.changes["before"]["campo"], "valor_antes")
        self.assertNotIn("after", entry.changes)


class RF14CP12InmutabilidadRegistrosTest(TestCase):
    """
    CP 1.2 — Inmutabilidad de registros de auditoría.
    La API rechaza cualquier intento de edición o eliminación de un AuditLog
    existente, y el modelo lanza ValidationError ante operaciones directas en ORM.
    """

    def setUp(self):
        self.admin = _make_admin(username="admin_immut", email="admin_immut@test.com")
        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

        self.log_entry = log_critical_action(
            user=self.admin,
            action=AuditLog.ActionChoices.CREATE,
            model_name="TestModel",
            object_id="1",
            before=None,
            after={"campo": "valor"},
        )

    def test_api_no_permite_post_en_audit_logs(self):
        """El endpoint de auditoría es de solo lectura (no acepta POST)."""
        response = self.api.post(
            AUDIT_LOGS_URL,
            {"action": "DELETE", "model_name": "X"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_api_no_permite_put_en_audit_log(self):
        response = self.api.put(
            f"{AUDIT_LOGS_URL}{self.log_entry.pk}/",
            {"action": "UPDATE"},
            format="json",
        )
        self.assertIn(
            response.status_code,
            [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_404_NOT_FOUND],
        )

    def test_api_no_permite_patch_en_audit_log(self):
        response = self.api.patch(
            f"{AUDIT_LOGS_URL}{self.log_entry.pk}/",
            {"action": "UPDATE"},
            format="json",
        )
        self.assertIn(
            response.status_code,
            [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_404_NOT_FOUND],
        )

    def test_save_directo_en_registro_existente_lanza_validationerror(self):
        """Editar un AuditLog existente via ORM lanza ValidationError."""
        self.log_entry.model_name = "Tampered"
        with self.assertRaises(ValidationError):
            self.log_entry.save()

    def test_delete_directo_en_instancia_lanza_validationerror(self):
        """Llamar .delete() en una instancia lanza ValidationError."""
        with self.assertRaises(ValidationError):
            self.log_entry.delete()

    def test_delete_via_queryset_lanza_validationerror(self):
        """AuditLog.objects.filter(...).delete() lanza ValidationError."""
        with self.assertRaises(ValidationError):
            AuditLog.objects.filter(pk=self.log_entry.pk).delete()

    def test_registro_permanece_intacto_tras_intentos_de_mutacion(self):
        original_action = self.log_entry.action
        original_model = self.log_entry.model_name

        try:
            self.log_entry.model_name = "Tampered"
            self.log_entry.save()
        except ValidationError:
            pass

        try:
            self.log_entry.delete()
        except ValidationError:
            pass

        fresh = AuditLog.objects.get(pk=self.log_entry.pk)
        self.assertEqual(fresh.action, original_action)
        self.assertEqual(fresh.model_name, original_model)

    def test_solo_admin_puede_listar_audit_logs(self):
        """Solo el rol ADMIN puede consultar la bitácora."""
        analyst = _make_analyst(username="a_immut", email="a_immut@test.com")
        analyst_api = APIClient()
        analyst_api.force_authenticate(user=analyst)

        response_analyst = analyst_api.get(AUDIT_LOGS_URL)
        self.assertEqual(response_analyst.status_code, status.HTTP_403_FORBIDDEN)

        response_admin = self.api.get(AUDIT_LOGS_URL)
        self.assertEqual(response_admin.status_code, status.HTTP_200_OK)
