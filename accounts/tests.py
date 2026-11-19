from django.contrib.auth.models import User
from io import BytesIO

from PIL import Image

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
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


class StudentProfileAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="profile_student",
            email="profile@example.com",
            password="CampusCartPass123!",
            first_name="Profile",
            last_name="Student",
        )

        self.profile = StudentProfile.objects.create(
            user=self.user,
            student_id="TUM100",
            institution="Technical University of Mombasa",
            course="Computer Science",
            year_of_study=4,
            phone_number="0712345678",
            bio="Computer Science student.",
        )

        self.other_user = User.objects.create_user(
            username="other_student",
            email="other@example.com",
            password="CampusCartPass123!",
        )

        self.other_profile = StudentProfile.objects.create(
            user=self.other_user,
            student_id="TUM200",
            institution="Another University",
            course="Information Technology",
            year_of_study=2,
            phone_number="0798765432",
            bio="Another student.",
        )

        self.profile_url = "/api/accounts/profile/"
        self.public_profile_url = (
            f"/api/accounts/students/{self.other_profile.pk}/"
        )

        self.client.force_authenticate(user=self.user)

    def test_student_can_retrieve_own_profile(self):
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "profile_student")
        self.assertEqual(response.data["student_id"], "TUM100")
        self.assertEqual(response.data["course"], "Computer Science")

    def test_student_can_update_own_profile(self):
        response = self.client.patch(
            self.profile_url,
            {
                "bio": "Updated CampusCart student biography.",
                "course": "Software Engineering",
                "year_of_study": 5,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()

        self.assertEqual(
            self.profile.bio,
            "Updated CampusCart student biography.",
        )
        self.assertEqual(
            self.profile.course,
            "Software Engineering",
        )
        self.assertEqual(self.profile.year_of_study, 5)

    def test_student_can_update_account_names_and_email(self):
        response = self.client.patch(
            self.profile_url,
            {
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()

        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.last_name, "Name")
        self.assertEqual(self.user.email, "updated@example.com")

    def test_student_cannot_change_username_or_student_id(self):
        response = self.client.patch(
            self.profile_url,
            {
                "username": "changed_username",
                "student_id": "TUM999",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.profile.refresh_from_db()

        self.assertEqual(self.user.username, "profile_student")
        self.assertEqual(self.profile.student_id, "TUM100")

    def test_duplicate_email_is_rejected(self):
        response = self.client.patch(
            self.profile_url,
            {"email": "other@example.com"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_public_profile_is_available_without_login(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.public_profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "other_student")
        self.assertEqual(response.data["course"], "Information Technology")

    def test_public_profile_does_not_expose_private_information(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.public_profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertNotIn("email", response.data)
        self.assertNotIn("phone_number", response.data)
        self.assertNotIn("student_id", response.data)

    def test_private_profile_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.profile_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_public_profile_returns_404_for_unknown_student(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            "/api/accounts/students/99999/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_can_upload_profile_picture(self):
        image_file = BytesIO()

        image = Image.new("RGB", (100, 100), color="green")
        image.save(image_file, format="PNG")
        image_file.seek(0)

        uploaded_image = SimpleUploadedFile(
            "profile.png",
            image_file.read(),
            content_type="image/png",
        )

        response = self.client.patch(
            self.profile_url,
            {"avatar": uploaded_image},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profile.refresh_from_db()

        self.assertTrue(self.profile.avatar)
        self.assertTrue(self.profile.avatar.name.startswith("profiles/"))


    def test_profile_picture_rejects_invalid_image(self):
        invalid_file = SimpleUploadedFile(
            "not_an_image.txt",
            b"This is not a valid image.",
            content_type="text/plain",
        )

        response = self.client.patch(
            self.profile_url,
            {"avatar": invalid_file},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_profile_picture_rejects_files_over_5_mb(self):
        oversized_file = SimpleUploadedFile(
            "large_image.png",
            b"x" * (5 * 1024 * 1024 + 1),
            content_type="image/png",
        )

        response = self.client.patch(
            self.profile_url,
            {"avatar": oversized_file},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("avatar", response.data)
