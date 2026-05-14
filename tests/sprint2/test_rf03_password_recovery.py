"""
RF03 — Recuperación de contraseña por email.

CP 1.1 (Integration): Envío exitoso del enlace de recuperación.
CP 1.2 (Unit):        Email no registrado — no revela existencia del email.
CP 2.1 (Integration): El enlace queda invalidado tras un único uso.
"""

from django.core import mail
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import CustomUser
from apps.users.services import generate_password_reset_link, validate_password_reset_token

PASSWORD_RESET_URL = "/api/v1/auth/password-reset/"
PASSWORD_RESET_CONFIRM_URL = "/api/v1/auth/password-reset/confirm/"


def _make_user(username="usuario_test", email="usuario@test.com", password="Pass1234!"):
    return CustomUser.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name="Test",
        last_name="User",
    )


def _extract_uid_token_from_link(link: str):
    """Extrae uid y token de un enlace de recuperación generado por el servicio."""
    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(link)
    params = parse_qs(parsed.query)
    return params["uid"][0], params["token"][0]


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RF03CP11EnvioExitosoTest(TestCase):
    """
    CP 1.1 — Envío exitoso del enlace de recuperación.
    Verifica el flujo completo: generación del token temporal y envío del
    correo de recuperación para una dirección registrada válida.
    """

    def setUp(self):
        self.api = APIClient()
        self.user = _make_user()

    def test_respuesta_200_para_email_registrado(self):
        response = self.api.post(
            PASSWORD_RESET_URL,
            {"email": self.user.email},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)

    def test_se_envia_exactamente_un_correo(self):
        self.api.post(
            PASSWORD_RESET_URL,
            {"email": self.user.email},
            format="json",
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_correo_contiene_enlace_con_uid_y_token(self):
        self.api.post(
            PASSWORD_RESET_URL,
            {"email": self.user.email},
            format="json",
        )
        email_sent = mail.outbox[0]
        self.assertIn("uid=", email_sent.body)
        self.assertIn("token=", email_sent.body)

    def test_correo_dirigido_al_destinatario_correcto(self):
        self.api.post(
            PASSWORD_RESET_URL,
            {"email": self.user.email},
            format="json",
        )
        email_sent = mail.outbox[0]
        self.assertIn(self.user.email, email_sent.to)

    def test_token_generado_es_valido_para_el_usuario(self):
        link = generate_password_reset_link(self.user)
        uid, token = _extract_uid_token_from_link(link)
        user_recovered = validate_password_reset_token(uid, token)
        self.assertIsNotNone(user_recovered)
        self.assertEqual(user_recovered.pk, self.user.pk)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RF03CP12EmailNoRegistradoTest(TestCase):
    """
    CP 1.2 — Email no registrado.
    El sistema no revela si el email existe, protegiendo datos sensibles
    (prevención de enumeración de usuarios).
    """

    def setUp(self):
        self.api = APIClient()

    def test_respuesta_200_para_email_no_registrado(self):
        response = self.api.post(
            PASSWORD_RESET_URL,
            {"email": "noexiste@correo.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_se_envia_correo_para_email_no_registrado(self):
        self.api.post(
            PASSWORD_RESET_URL,
            {"email": "noexiste@correo.com"},
            format="json",
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_mensaje_respuesta_identico_al_de_email_valido(self):
        user = _make_user(username="u2", email="valido@test.com")

        resp_invalido = self.api.post(
            PASSWORD_RESET_URL,
            {"email": "noexiste@correo.com"},
            format="json",
        )
        resp_valido = self.api.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )

        self.assertEqual(resp_invalido.data["detail"], resp_valido.data["detail"])


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RF03CP21EnlaceInvalidadoTrasUsoTest(TestCase):
    """
    CP 2.1 — Enlace invalidado tras uso único.
    El token de recuperación queda inutilizable después de ser consumido
    por un restablecimiento exitoso de contraseña.
    """

    def setUp(self):
        self.api = APIClient()
        self.user = _make_user(username="u_reset", email="reset@test.com")
        link = generate_password_reset_link(self.user)
        self.uid, self.token = _extract_uid_token_from_link(link)

    def test_primer_uso_del_token_es_exitoso(self):
        response = self.api.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "NuevaPass999!",
                "new_password_confirm": "NuevaPass999!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_segundo_uso_del_mismo_token_es_rechazado(self):
        self.api.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "NuevaPass999!",
                "new_password_confirm": "NuevaPass999!",
            },
            format="json",
        )

        response = self.api.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": "OtraPass888!",
                "new_password_confirm": "OtraPass888!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_token_invalido_es_rechazado(self):
        response = self.api.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "uid": self.uid,
                "token": "token-invalido-fabricado",
                "new_password": "NuevaPass999!",
                "new_password_confirm": "NuevaPass999!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
