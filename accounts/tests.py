from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import StudentProfile


class StudentRegistrationTests(APITestCase):

    def setUp(self):
        self.url = "/api/accounts/register/"

        self.valid_payload = {
            "username": "teststudent",
            "email": "student@example.com",
            "password": "CampusCartPass123!",
            "confirm_password": "CampusCartPass123!",
            "first_name": "Test",
            "last_name": "Student",
            "student_id": "TUM001",
            "institution": "Technical University of Mombasa",
            "course": "Computer Science",
            "year_of_study": 4,
            "phone_number": "0712345678",
        }

    def test_student_can_register_successfully(self):
        response = self.client.post(
            self.url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(StudentProfile.objects.count(), 1)

        user = User.objects.get(username="teststudent")

        self.assertTrue(user.check_password("CampusCartPass123!"))
        self.assertEqual(user.student_profile.student_id, "TUM001")
        self.assertEqual(user.student_profile.year_of_study, 4)

    def test_registration_rejects_duplicate_username(self):
        User.objects.create_user(
            username="teststudent",
            email="another@example.com",
            password="ExistingPass123!",
        )

        response = self.client.post(
            self.url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_duplicate_email(self):
        User.objects.create_user(
            username="existinguser",
            email="student@example.com",
            password="ExistingPass123!",
        )

        response = self.client.post(
            self.url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_password_mismatch(self):
        payload = self.valid_payload.copy()
        payload["confirm_password"] = "DifferentPass123!"

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_rejects_weak_password(self):
        payload = self.valid_payload.copy()
        payload["password"] = "123"
        payload["confirm_password"] = "123"

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_registration_does_not_allow_duplicate_student_id(self):
        User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="ExistingPass123!",
        )

        StudentProfile.objects.create(
            user=User.objects.get(username="existinguser"),
            student_id="TUM001",
        )

        response = self.client.post(
            self.url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)


class StudentAuthenticationTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="authstudent",
            email="authstudent@example.com",
            password="CampusCartPass123!",
        )

        self.login_url = "/api/accounts/login/"
        self.refresh_url = "/api/accounts/token/refresh/"
        self.logout_url = "/api/accounts/logout/"

    def test_student_can_login_and_receive_tokens(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "authstudent",
                "password": "CampusCartPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_incorrect_password(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "authstudent",
                "password": "WrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_endpoint_returns_new_access_token(self):
        refresh = RefreshToken.for_user(self.user)

        response = self.client.post(
            self.refresh_url,
            {"refresh": str(refresh)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_authenticated_student_can_logout(self):
        refresh = RefreshToken.for_user(self.user)
        access = str(refresh.access_token)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

        response = self.client.post(
            self.logout_url,
            {"refresh": str(refresh)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_blacklists_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        access = str(refresh.access_token)
        refresh_string = str(refresh)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access}"
        )

        logout_response = self.client.post(
            self.logout_url,
            {"refresh": refresh_string},
            format="json",
        )

        self.assertEqual(
            logout_response.status_code,
            status.HTTP_200_OK,
        )

        refresh_response = self.client.post(
            self.refresh_url,
            {"refresh": refresh_string},
            format="json",
        )

        self.assertEqual(
            refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_requires_authentication(self):
        refresh = RefreshToken.for_user(self.user)

        response = self.client.post(
            self.logout_url,
            {"refresh": str(refresh)},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

