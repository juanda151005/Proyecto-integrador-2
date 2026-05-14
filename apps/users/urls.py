from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("", views.UserListCreateView.as_view(), name="user-list-create"),
    path("<int:pk>/", views.UserDetailView.as_view(), name="user-detail"),
    path("me/", views.VerifyTokenView.as_view(), name="user-me"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path(
        "change-password/", views.ChangePasswordView.as_view(), name="change-password"
    ),
    path(
        "login-attempts/", views.LoginAttemptListView.as_view(), name="login-attempts"
    ),
]
