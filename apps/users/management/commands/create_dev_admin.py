"""
Usuario de demostración con rol ADMIN para probar el frontend (JWT / RBAC).

Solo para entornos de desarrollo. No usar en producción.

  python manage.py create_dev_admin
  python manage.py create_dev_admin --reset-password   # si ya existía: vuelve a fijar clave y rol ADMIN
"""

from django.core.management.base import BaseCommand

from apps.users.models import CustomUser

DEV_ADMIN_USERNAME = "admin_demo"
DEV_ADMIN_EMAIL = "admin_demo@localhost"
DEV_ADMIN_PASSWORD = "AdminPass123*"


class Command(BaseCommand):
    help = "Crea (o restablece) un usuario de aplicación con rol Administrador para pruebas locales."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Si el usuario ya existe, restablece la contraseña de demo y fuerza rol ADMIN.",
        )

    def handle(self, *args, **options):
        reset = options["reset_password"]
        user = CustomUser.objects.filter(username=DEV_ADMIN_USERNAME).first()

        if user and not reset:
            self.stdout.write(
                self.style.WARNING(
                    f'Ya existe "{DEV_ADMIN_USERNAME}". '
                    "Ejecuta con --reset-password para fijar de nuevo la clave de demo y el rol ADMIN."
                )
            )
            self._print_credentials(created=False)
            return

        if user and reset:
            user.email = DEV_ADMIN_EMAIL
            user.role = CustomUser.Role.ADMIN
            user.is_staff = True
            user.set_password(DEV_ADMIN_PASSWORD)
            user.save()
            self.stdout.write(self.style.SUCCESS("Usuario actualizado (contraseña y rol ADMIN)."))
            self._print_credentials(created=False)
            return

        CustomUser.objects.create_user(
            username=DEV_ADMIN_USERNAME,
            email=DEV_ADMIN_EMAIL,
            password=DEV_ADMIN_PASSWORD,
            first_name="Admin",
            last_name="Demo",
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        self.stdout.write(self.style.SUCCESS("Usuario de demostración creado."))
        self._print_credentials(created=True)

    def _print_credentials(self, created):
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("  Frontend (login.html) — usar:"))
        self.stdout.write(f'    Usuario:     {DEV_ADMIN_USERNAME}')
        self.stdout.write(f'    Contraseña:  {DEV_ADMIN_PASSWORD}')
        self.stdout.write(f'    Rol:         ADMIN (aplicación)')
        self.stdout.write("")
