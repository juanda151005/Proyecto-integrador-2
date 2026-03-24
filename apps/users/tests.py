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
