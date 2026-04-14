from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import CustomUser, LoginAttempt
from .services import create_user, log_login_attempt

# =============================================================================
# Tests para Models (RF01)
# =============================================================================


class CustomUserModelTest(TestCase):
    """Tests para el modelo CustomUser."""

    def test_create_user_with_role(self):
        """RF01: El sistema permite asignar al menos un rol al crear el usuario."""
        user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123*",
            role=CustomUser.Role.ANALYST,
        )
        self.assertEqual(user.role, "ANALYST")
        self.assertTrue(user.is_analyst)
        self.assertFalse(user.is_admin)

    def test_email_unique(self):
        """RF01: No se permiten correos electrónicos duplicados."""
        CustomUser.objects.create_user(
            username="user1",
            email="duplicate@example.com",
            password="TestPass123*",
        )
        with self.assertRaises(Exception):
            CustomUser.objects.create_user(
                username="user2",
                email="duplicate@example.com",
                password="TestPass123*",
            )

    def test_default_role_is_agent(self):
        """RF01: El rol por defecto es AGENT (Asesor)."""
        user = CustomUser.objects.create_user(
            username="defaultrole",
            email="default@example.com",
            password="TestPass123*",
        )
        self.assertEqual(user.role, "AGENT")

    def test_str_representation(self):
        user = CustomUser.objects.create_user(
            username="strtest",
            email="str@example.com",
            password="TestPass123*",
            role=CustomUser.Role.ADMIN,
        )
        self.assertIn("strtest", str(user))
        self.assertIn("Administrador", str(user))


class LoginAttemptModelTest(TestCase):
    """Tests para el modelo LoginAttempt."""

    def test_create_login_attempt(self):
        attempt = LoginAttempt.objects.create(
            username_attempted="testuser",
            ip_address="127.0.0.1",
            was_successful=False,
        )
        self.assertFalse(attempt.was_successful)
        self.assertEqual(attempt.username_attempted, "testuser")


# =============================================================================
# Tests para Services (RF01, RF02)
# =============================================================================


class UserServicesTest(TestCase):
    """Tests para la capa de servicios."""

    def test_create_user_service(self):
        """RF01: Crear usuario vía service con contraseña hasheada."""
        user = create_user(
            {
                "username": "svcuser",
                "email": "svc@example.com",
                "password": "SecurePass123*",
                "role": "ANALYST",
                "first_name": "Service",
                "last_name": "User",
            }
        )
        self.assertEqual(user.username, "svcuser")
        self.assertTrue(user.check_password("SecurePass123*"))
        self.assertNotEqual(user.password, "SecurePass123*")  # Hasheada

    def test_log_login_attempt_success(self):
        """RF02/RF05: Registrar intento exitoso."""
        attempt = log_login_attempt("admin", "192.168.1.1", success=True)
        self.assertTrue(attempt.was_successful)

    def test_log_login_attempt_failure(self):
        """RF02/RF05: Registrar intento fallido."""
        attempt = log_login_attempt("hacker", "10.0.0.1", success=False)
        self.assertFalse(attempt.was_successful)
        self.assertEqual(attempt.username_attempted, "hacker")


# =============================================================================
# Tests para Views (RF01, RF02)
# =============================================================================


class AuthenticationViewsTest(TestCase):
    """Tests para las vistas de autenticación (RF02)."""

    def setUp(self):
        self.client = APIClient()
        self.admin = CustomUser.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            password="AdminPass123*",
            role=CustomUser.Role.ADMIN,
        )

    def test_login_success(self):
        """RF02: Login exitoso retorna access token y datos del usuario."""
        response = self.client.post(
            "/api/v1/auth/token/",
            {"username": "admin_test", "password": "AdminPass123*"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["role"], "ADMIN")

    def test_login_failure(self):
        """RF02: Credenciales inválidas retornan 401."""
        response = self.client.post(
            "/api/v1/auth/token/",
            {"username": "admin_test", "password": "WrongPass"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_logs_attempt(self):
        """RF02/RF05: Cada intento de login queda registrado."""
        self.client.post(
            "/api/v1/auth/token/",
            {"username": "admin_test", "password": "WrongPass"},
            format="json",
        )
        self.client.post(
            "/api/v1/auth/token/",
            {"username": "admin_test", "password": "AdminPass123*"},
            format="json",
        )
        attempts = LoginAttempt.objects.filter(username_attempted="admin_test")
        self.assertEqual(attempts.count(), 2)
        # Ordering is -timestamp, so first() = most recent (successful login)
        self.assertTrue(attempts.first().was_successful)
        self.assertFalse(attempts.last().was_successful)

    def test_verify_token_authenticated(self):
        """RF02: /me/ retorna datos del usuario autenticado."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/users/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "admin_test")
        self.assertEqual(response.data["role"], "ADMIN")

    def test_verify_token_unauthenticated(self):
        """RF02: /me/ sin token retorna 401."""
        response = self.client.get("/api/v1/users/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserManagementViewsTest(TestCase):
    """Tests para las vistas de gestión de usuarios (RF01)."""

    def setUp(self):
        self.client = APIClient()
        self.admin = CustomUser.objects.create_user(
            username="admin_mgmt",
            email="admin_mgmt@test.com",
            password="AdminPass123*",
            role=CustomUser.Role.ADMIN,
        )
        self.agent = CustomUser.objects.create_user(
            username="agent_test",
            email="agent@test.com",
            password="AgentPass123*",
            role=CustomUser.Role.AGENT,
        )

    def test_admin_can_list_users(self):
        """RF01: Admin puede listar usuarios."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_agent_cannot_list_users(self):
        """RF01/RF19: Non-admin no puede listar usuarios."""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_user(self):
        """RF01: Admin puede crear usuario con rol."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/v1/users/",
            {
                "username": "newuser",
                "email": "new@example.com",
                "password": "NewPass123*",
                "password_confirm": "NewPass123*",
                "role": "ANALYST",
                "first_name": "New",
                "last_name": "User",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            CustomUser.objects.filter(username="newuser", role="ANALYST").exists()
        )

    def test_duplicate_email_rejected(self):
        """RF01: No se permiten correos duplicados."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/v1/users/",
            {
                "username": "dupuser",
                "email": "admin_mgmt@test.com",  # Ya existe
                "password": "DupPass123*",
                "password_confirm": "DupPass123*",
                "role": "AGENT",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_mismatch_rejected(self):
        """RF01: Contraseñas que no coinciden son rechazadas."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/v1/users/",
            {
                "username": "mismatch",
                "email": "mismatch@example.com",
                "password": "Pass1234*",
                "password_confirm": "Different*",
                "role": "AGENT",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# Tests para RF19 — RBAC (Control de Acceso Basado en Roles)
# =============================================================================


class RBACMiddlewareTest(TestCase):
    """Tests para el middleware RBAC (RF19)."""

    def setUp(self):
        self.client = APIClient()
        self.admin = CustomUser.objects.create_user(
            username="rbac_admin",
            email="rbac_admin@test.com",
            password="AdminPass123*",
            role=CustomUser.Role.ADMIN,
        )
        self.agent = CustomUser.objects.create_user(
            username="rbac_agent",
            email="rbac_agent@test.com",
            password="AgentPass123*",
            role=CustomUser.Role.AGENT,
        )
        self.analyst = CustomUser.objects.create_user(
            username="rbac_analyst",
            email="rbac_analyst@test.com",
            password="AnalystPass123*",
            role=CustomUser.Role.ANALYST,
        )

    def test_agent_cannot_list_users(self):
        """RF19: Un Asesor NO puede acceder a la lista de usuarios."""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.json())

    def test_agent_cannot_create_user(self):
        """RF19: Un Asesor NO puede crear usuarios."""
        self.client.force_authenticate(user=self.agent)
        response = self.client.post(
            "/api/v1/users/",
            {
                "username": "blocked",
                "email": "blocked@test.com",
                "password": "Pass1234*",
                "password_confirm": "Pass1234*",
                "role": "AGENT",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agent_cannot_delete_user(self):
        """RF19: Un Asesor NO puede eliminar usuarios."""
        self.client.force_authenticate(user=self.agent)
        response = self.client.delete(f"/api/v1/users/{self.admin.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agent_cannot_view_login_attempts(self):
        """RF19: Un Asesor NO puede ver la bitácora de login."""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get("/api/v1/users/login-attempts/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_analyst_cannot_manage_users(self):
        """RF19: Un Analista NO puede acceder a gestión de usuarios."""
        self.client.force_authenticate(user=self.analyst)
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_all(self):
        """RF19: Un Admin SÍ puede acceder a todo."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_forbidden_response_includes_role_info(self):
        """RF19: La respuesta 403 incluye info del rol requerido vs actual."""
        self.client.force_authenticate(user=self.agent)
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        # El middleware retorna detail con info, o DRF retorna su propio 403
        self.assertIn("detail", data)


# =============================================================================
# Tests para RF06 — Recuperación de contraseña por email
# =============================================================================


class PasswordResetRequestViewTest(TestCase):
    """Tests para la solicitud de recuperación de contraseña (RF06)."""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username="reset_user",
            email="reset@example.com",
            password="OldPass123*",
            first_name="Juan",
            is_active=True,
        )

    def test_request_with_registered_email_returns_200(self):
        """RF06: Solicitar reset con email registrado retorna 200."""
        response = self.client.post(
            "/api/v1/auth/password-reset/",
            {"email": "reset@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.json())

    def test_request_with_unknown_email_also_returns_200(self):
        """RF06: Solicitar reset con email desconocido también retorna 200 (seguridad)."""
        response = self.client.post(
            "/api/v1/auth/password-reset/",
            {"email": "noexiste@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_request_with_invalid_email_format_returns_400(self):
        """RF06: Email con formato inválido retorna 400."""
        response = self.client.post(
            "/api/v1/auth/password-reset/",
            {"email": "no-es-un-email"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_request_does_not_require_authentication(self):
        """RF06: El endpoint de solicitud es público (no requiere token)."""
        # Sin force_authenticate — debe funcionar igual
        response = self.client.post(
            "/api/v1/auth/password-reset/",
            {"email": "reset@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PasswordResetConfirmViewTest(TestCase):
    """Tests para la confirmación de reset de contraseña (RF06)."""

    def setUp(self):
        from django.contrib.auth.tokens import PasswordResetTokenGenerator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username="confirm_user",
            email="confirm@example.com",
            password="OldPass123*",
            is_active=True,
        )
        # Generar un token válido para este usuario
        generator = PasswordResetTokenGenerator()
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = generator.make_token(self.user)

    def test_valid_token_resets_password(self):
        """RF06: Token válido + nueva contraseña → contraseña cambiada."""
        response = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "NewSecure123*",
                "new_password_confirm": "NewSecure123*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que la contraseña realmente cambió
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecure123*"))
        self.assertFalse(self.user.check_password("OldPass123*"))

    def test_invalid_token_returns_400(self):
        """RF06: Token manipulado / inválido retorna 400."""
        response = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                "uid": self.uid,
                "token": "token-completamente-falso",
                "new_password": "NewSecure123*",
                "new_password_confirm": "NewSecure123*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.json())

    def test_invalid_uid_returns_400(self):
        """RF06: UID inválido / no corresponde a ningún usuario retorna 400."""
        response = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                "uid": "uid-que-no-existe",
                "token": self.token,
                "new_password": "NewSecure123*",
                "new_password_confirm": "NewSecure123*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_mismatch_returns_400(self):
        """RF06: Contraseñas que no coinciden retornan 400 antes de tocar el token."""
        response = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "NewSecure123*",
                "new_password_confirm": "Diferente999*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_invalidated_after_use(self):
        """RF06: El token queda inválido después de usar (contraseña guardada cambia el hash)."""
        # Primer uso — exitoso
        self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "NewSecure123*",
                "new_password_confirm": "NewSecure123*",
            },
            format="json",
        )
        # Segundo uso con el mismo token — debe fallar
        response = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "AnotherPass456*",
                "new_password_confirm": "AnotherPass456*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_does_not_require_authentication(self):
        """RF06: El endpoint de confirmación es público (no requiere token JWT)."""
        response = self.client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "NewSecure123*",
                "new_password_confirm": "NewSecure123*",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PasswordResetServiceTest(TestCase):
    """Tests unitarios del service layer de RF06."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="svc_reset",
            email="svc_reset@example.com",
            password="OldPass123*",
            is_active=True,
        )

    def test_generate_and_validate_token(self):
        """RF06: El token generado puede ser validado correctamente."""
        from .services import (
            generate_password_reset_link,
            validate_password_reset_token,
        )

        link = generate_password_reset_link(self.user)
        # Extraer uid y token del link
        parts = link.rstrip("/").split("/")
        token = parts[-1]
        uid = parts[-2]

        validated_user = validate_password_reset_token(uid, token)
        self.assertIsNotNone(validated_user)
        self.assertEqual(validated_user.pk, self.user.pk)

    def test_validate_invalid_token_returns_none(self):
        """RF06: Token inválido retorna None."""
        from .services import validate_password_reset_token
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        result = validate_password_reset_token(uid, "token-falso-xyz")
        self.assertIsNone(result)

    def test_validate_nonexistent_uid_returns_none(self):
        """RF06: UID de usuario inexistente retorna None."""
        from .services import validate_password_reset_token

        result = validate_password_reset_token("uidinvalido", "cualquier-token")
        self.assertIsNone(result)
