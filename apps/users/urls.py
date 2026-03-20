from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # RF01 — Gestión de usuarios
    path('', views.UserListCreateView.as_view(), name='user-list-create'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),

    # RF02 — Verificar token / obtener usuario autenticado
    path('me/', views.VerifyTokenView.as_view(), name='user-me'),

    # RF04 — Perfil del usuario autenticado
    path('profile/', views.ProfileView.as_view(), name='profile'),

    # RF03 — Cambio de contraseña
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),

    # RF05 — Bitácora de intentos de login
    path('login-attempts/', views.LoginAttemptListView.as_view(), name='login-attempts'),
]
