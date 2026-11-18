from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import StudentRegistrationView, StudentLogoutView


app_name = "accounts"

urlpatterns = [
    path(
        "register/",
        StudentRegistrationView.as_view(),
        name="register",
    ),
    path(
        "login/",
        TokenObtainPairView.as_view(),
        name="login",
    ),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path(
        "logout/",
        StudentLogoutView.as_view(),
        name="logout",
    ),
]