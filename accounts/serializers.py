
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    validate_password as django_validate_password,
)
from django.db import transaction

from rest_framework import serializers

from .models import StudentProfile


User = get_user_model()


class StudentRegistrationSerializer(serializers.Serializer):

    # Account information
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        min_length=8
    )
    confirm_password = serializers.CharField(write_only=True)

    first_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True
    )
    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True
    )

    # Student profile information
    student_id = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    institution = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True
    )

    course = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True
    )

    year_of_study = serializers.ChoiceField(
        choices=StudentProfile.YEAR_CHOICES,
        required=False,
        allow_null=True
    )

    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True
    )

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "This username is already taken."
            )

        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value


    def validate_student_id(self, value):
        if value and StudentProfile.objects.filter(
            student_id=value
        ).exists():
            raise serializers.ValidationError(
                "A student with this student ID is already registered."
            )

        return value


    def validate_password(self, value):
        django_validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("confirm_password")

        password = validated_data.pop("password")

        profile_fields = {
            "student_id": validated_data.pop("student_id", None),
            "institution": validated_data.pop("institution", ""),
            "course": validated_data.pop("course", ""),
            "year_of_study": validated_data.pop("year_of_study", None),
            "phone_number": validated_data.pop("phone_number", ""),
        }

        # An omitted or blank student ID must be stored as NULL.
        if not profile_fields["student_id"]:
            profile_fields["student_id"] = None

        # Create the Django user with a securely hashed password.
        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        # Automatically create the corresponding student profile.
        StudentProfile.objects.create(
            user=user,
            **profile_fields
        )

        return user


class MyProfileSerializer(serializers.ModelSerializer):

    # Account fields from Django's built-in User model
    username = serializers.CharField(
        source="user.username",
        read_only=True
    )

    email = serializers.EmailField(
        source="user.email",
        required=False
    )

    first_name = serializers.CharField(
        source="user.first_name",
        required=False,
        allow_blank=True
    )

    last_name = serializers.CharField(
        source="user.last_name",
        required=False,
        allow_blank=True
    )

    class Meta:
        model = StudentProfile

        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "student_id",
            "institution",
            "course",
            "year_of_study",
            "phone_number",
            "bio",
            "avatar",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "username",
            "student_id",
            "created_at",
            "updated_at",
        ]

    def validate_email(self, value):
        existing_user = User.objects.filter(
            email__iexact=value
        ).exclude(
            pk=self.instance.user_id
        )

        if existing_user.exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value

    def validate_avatar(self, value):
        max_size = 5 * 1024 * 1024  # 5 MB

        if value and value.size > max_size:
            raise serializers.ValidationError(
                "Profile picture must not exceed 5 MB."
            )

        return value

    @transaction.atomic
    def update(self, instance, validated_data):

        # Extract account information separately.
        user_data = validated_data.pop("user", {})

        # Update the Django User fields.
        user = instance.user

        for field, value in user_data.items():
            setattr(user, field, value)

        if user_data:
            user.save(update_fields=list(user_data.keys()))

        # Update the StudentProfile fields.
        return super().update(instance, validated_data)


class PublicStudentProfileSerializer(serializers.ModelSerializer):

    username = serializers.CharField(
        source="user.username",
        read_only=True
    )

    first_name = serializers.CharField(
        source="user.first_name",
        read_only=True
    )

    last_name = serializers.CharField(
        source="user.last_name",
        read_only=True
    )

    class Meta:
        model = StudentProfile

        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "institution",
            "course",
            "year_of_study",
            "bio",
            "avatar",
        ]

        read_only_fields = fields
