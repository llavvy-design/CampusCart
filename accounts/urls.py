from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    StudentRegistrationView,
    StudentLogoutView,
    MyProfileView,
    PublicStudentProfileView,
)

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

        path(
        "profile/",
        MyProfileView.as_view(),
        name="my_profile",
    ),
    path(
        "students/<int:student_id>/",
        PublicStudentProfileView.as_view(),
        name="public_student_profile",
    ),
]
