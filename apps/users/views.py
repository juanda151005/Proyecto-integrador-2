from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import CustomUser, LoginAttempt
from .permissions import IsAdmin
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    LoginAttemptSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from .services import send_password_reset_email, validate_password_reset_token

# =============================================================================
# RF01 — Gestión de Usuarios y Roles
# =============================================================================


class UserListCreateView(generics.ListCreateAPIView):
    """
    GET  — Lista todos los usuarios (solo ADMIN).
    POST — Crea un nuevo usuario con rol asignado (RF01).
    """

    queryset = CustomUser.objects.all()
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["created_at", "username"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        """Solo ADMIN puede listar y crear usuarios."""
        return [IsAdmin()]


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PUT / PATCH / DELETE un usuario específico (solo ADMIN)."""

    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]


# =============================================================================
# RF02 — Autenticación de Usuarios
# =============================================================================


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST — Inicio de sesión con JWT (RF02).

    Retorna access token, refresh token y datos del usuario (id, rol, nombre).
    Registra automáticamente cada intento de login.
    """

    serializer_class = CustomTokenObtainPairSerializer


class VerifyTokenView(APIView):
    """
    GET — Verifica el token JWT actual y retorna datos del usuario autenticado.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "role_display": user.get_role_display(),
                "is_active": user.is_active,
            }
        )


# =============================================================================
# RF03, RF04 — Perfil y Contraseña
# =============================================================================


class ProfileView(generics.RetrieveUpdateAPIView):
    """GET / PUT / PATCH — Perfil del usuario autenticado (RF04)."""

    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """POST — Cambio de contraseña del usuario autenticado (RF03)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"detail": "La contraseña actual es incorrecta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": "Contraseña actualizada correctamente."})


# =============================================================================
# RF05 — Bitácora de Login
# =============================================================================


class LoginAttemptListView(generics.ListAPIView):
    """GET — Lista intentos de login (RF05, solo ADMIN)."""

    queryset = LoginAttempt.objects.all()
    serializer_class = LoginAttemptSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["was_successful"]
    search_fields = ["username_attempted", "ip_address"]


# =============================================================================
# RF06 — Recuperación de contraseña por email
# =============================================================================


class PasswordResetRequestView(APIView):
    """
    POST — Solicita el envío de un email de recuperación de contraseña (RF06).

    Endpoint público (no requiere autenticación).
    Por seguridad, SIEMPRE retorna 200 independientemente de si el email existe.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        try:
            user = CustomUser.objects.get(email=email, is_active=True)
            send_password_reset_email(user)
        except CustomUser.DoesNotExist:
            # No revelamos si el email existe o no (prevención de enumeración)
            pass

        return Response(
            {
                "detail": (
                    "Si el correo está registrado, recibirás un enlace "
                    "para restablecer tu contraseña en los próximos minutos."
                )
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    POST — Confirma el reset y establece la nueva contraseña (RF06).

    Endpoint público (no requiere autenticación).
    Valida el UID y token HMAC antes de aplicar el cambio.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        user = validate_password_reset_token(data["uid"], data["token"])

        if user is None:
            return Response(
                {
                    "detail": (
                        "El enlace de recuperación es inválido o ha expirado. "
                        "Por favor solicita uno nuevo."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(data["new_password"])
        user.save()

        return Response(
            {
                "detail": "Contraseña restablecida correctamente. Ya puedes iniciar sesión."
            },
            status=status.HTTP_200_OK,
        )
