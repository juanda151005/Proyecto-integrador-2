from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import CustomUser, LoginAttempt
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
    LoginAttemptSerializer,
    CustomTokenObtainPairSerializer,
)
from .permissions import IsAdmin


# =============================================================================
# RF01 — Gestión de Usuarios y Roles
# =============================================================================

class UserListCreateView(generics.ListCreateAPIView):
    """
    GET  — Lista todos los usuarios (solo ADMIN).
    POST — Crea un nuevo usuario con rol asignado (RF01).

    RF01 Criterios:
    - Se asigna al menos un rol al crear el usuario.
    - No se permiten correos duplicados.
    - Contraseña hasheada con algoritmo seguro.
    """
    queryset = CustomUser.objects.all()
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'username']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        """Solo ADMIN puede listar y crear usuarios."""
        return [IsAdmin()]


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET / PUT / PATCH / DELETE un usuario específico (solo ADMIN).
    """
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
    Registra automáticamente cada intento de login (exitoso o fallido) en la bitácora.

    RF02 Criterios:
    - Solo usuarios registrados y activos pueden autenticarse.
    - El token expira después de un tiempo definido (configurable en settings).
    - Errores de credenciales inválidas retornan 401 con mensaje descriptivo.
    """
    serializer_class = CustomTokenObtainPairSerializer


class VerifyTokenView(APIView):
    """
    GET — Verifica el token JWT actual y retorna datos del usuario autenticado.
    Útil para que el frontend sepa si el token sigue siendo válido y qué rol tiene.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'role_display': user.get_role_display(),
            'is_active': user.is_active,
        })


# =============================================================================
# RF03, RF04 — Perfil y Contraseña (esqueleto para futuros sprints)
# =============================================================================

class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET / PUT / PATCH — Perfil del usuario autenticado (RF04).
    """
    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    POST — Cambio de contraseña del usuario autenticado (RF03).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'detail': 'La contraseña actual es incorrecta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'detail': 'Contraseña actualizada correctamente.'})


# =============================================================================
# RF05 — Bitácora de Login
# =============================================================================

class LoginAttemptListView(generics.ListAPIView):
    """
    GET — Lista intentos de login (RF05, solo ADMIN).
    """
    queryset = LoginAttempt.objects.all()
    serializer_class = LoginAttemptSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['was_successful']
    search_fields = ['username_attempted', 'ip_address']
