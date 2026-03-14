from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CustomUser, LoginAttempt
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
    LoginAttemptSerializer,
)
from .permissions import IsAdmin


class UserListCreateView(generics.ListCreateAPIView):
    """
    GET  — Lista todos los usuarios (solo ADMIN).
    POST — Crea un nuevo usuario (RF01).
    """
    queryset = CustomUser.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return [IsAdmin()]


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET / PUT / PATCH / DELETE un usuario específico (solo ADMIN).
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]


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


class LoginAttemptListView(generics.ListAPIView):
    """
    GET — Lista intentos de login (RF05, solo ADMIN).
    """
    queryset = LoginAttempt.objects.all()
    serializer_class = LoginAttemptSerializer
    permission_classes = [IsAdmin]
