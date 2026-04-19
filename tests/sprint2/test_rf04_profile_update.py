"""
RF04 — Actualización de perfil de usuario.

CP 1.1 (Integration): Actualización exitosa — PATCH /api/v1/users/profile/.
CP 1.2 (Unit):        Rechazo de campos con formato inválido (letras en teléfono,
                      menos de 10 dígitos).
CP 2.1 (E2E/API):     Los cambios se reflejan inmediatamente en la respuesta
                      (equivalente backend de la actualización en tiempo real de la UI).
"""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import CustomUser

PROFILE_URL = "/api/v1/users/profile/"


def _make_user(
    username="perfil_user",
    email="perfil@test.com",
    password="Pass1234!",
    first_name="Juan",
    last_name="Pérez",
    phone_number="3001234567",
):
    return CustomUser.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
    )


class RF04CP11ActualizacionExitosaTest(TestCase):
    """
    CP 1.1 — Actualización exitosa del perfil.
    Verifica que PATCH /api/v1/users/profile/ procesa y persiste correctamente
    los nuevos datos del usuario autenticado.
    """

    def setUp(self):
        self.api = APIClient()
        self.user = _make_user()
        self.api.force_authenticate(user=self.user)

    def test_patch_nombre_actualiza_db(self):
        response = self.api.patch(
            PROFILE_URL,
            {"first_name": "Carlos", "last_name": "López"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Carlos")
        self.assertEqual(self.user.last_name, "López")

    def test_patch_telefono_valido_actualiza_db(self):
        response = self.api.patch(
            PROFILE_URL,
            {"phone_number": "3119876543"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, "3119876543")

    def test_patch_multiples_campos_simultaneamente(self):
        response = self.api.patch(
            PROFILE_URL,
            {
                "first_name": "Ana",
                "last_name": "Martínez",
                "phone_number": "3205556677",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ana")
        self.assertEqual(self.user.last_name, "Martínez")
        self.assertEqual(self.user.phone_number, "3205556677")

    def test_usuario_no_autenticado_recibe_401(self):
        api_anonimo = APIClient()
        response = api_anonimo.patch(
            PROFILE_URL,
            {"first_name": "Hack"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RF04CP12FormatoInvalidoRechazadoTest(TestCase):
    """
    CP 1.2 — Rechazo de campos con formato inválido.
    El sistema valida que el teléfono no contenga letras y tenga al menos 10 dígitos.
    """

    def setUp(self):
        self.api = APIClient()
        self.user = _make_user(username="u_formato", email="formato@test.com")
        self.api.force_authenticate(user=self.user)

    def test_telefono_con_letras_es_rechazado(self):
        response = self.api.patch(
            PROFILE_URL,
            {"phone_number": "30ABCDE567"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_telefono_menos_de_10_digitos_es_rechazado(self):
        response = self.api.patch(
            PROFILE_URL,
            {"phone_number": "123456789"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_telefono_con_caracteres_especiales_no_numericos_es_rechazado(self):
        response = self.api.patch(
            PROFILE_URL,
            {"phone_number": "300-123-abc"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_datos_originales_no_mutan_tras_rechazo(self):
        telefono_original = self.user.phone_number
        self.api.patch(
            PROFILE_URL,
            {"phone_number": "invalido"},
            format="multipart",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, telefono_original)

    def test_nombre_vacio_es_rechazado(self):
        response = self.api.patch(
            PROFILE_URL,
            {"first_name": "   "},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("first_name", response.data)


class RF04CP21ReflejoInmediatoEnRespuestaTest(TestCase):
    """
    CP 2.1 — Los cambios se reflejan inmediatamente en la respuesta de la API.
    Equivalente backend de la actualización en tiempo real de la UI:
    la misma llamada PATCH devuelve los datos ya actualizados sin recarga adicional.
    """

    def setUp(self):
        self.api = APIClient()
        self.user = _make_user(username="u_reflect", email="reflect@test.com")
        self.api.force_authenticate(user=self.user)

    def test_respuesta_patch_contiene_datos_actualizados(self):
        response = self.api.patch(
            PROFILE_URL,
            {"first_name": "Nuevo", "last_name": "Apellido"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Nuevo")
        self.assertEqual(response.data["last_name"], "Apellido")

    def test_get_perfil_devuelve_datos_actualizados_sin_recarga(self):
        self.api.patch(
            PROFILE_URL,
            {"first_name": "Cambiado"},
            format="multipart",
        )
        response_get = self.api.get(PROFILE_URL)
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)
        self.assertEqual(response_get.data["first_name"], "Cambiado")

    def test_actualizacion_no_afecta_campos_no_enviados(self):
        apellido_original = self.user.last_name
        self.api.patch(
            PROFILE_URL,
            {"first_name": "Solo Nombre"},
            format="multipart",
        )
        response_get = self.api.get(PROFILE_URL)
        self.assertEqual(response_get.data["last_name"], apellido_original)
