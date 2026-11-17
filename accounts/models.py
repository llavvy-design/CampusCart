
from django.db import models
from django.contrib.auth.models import User


class StudentProfile(models.Model):

    YEAR_CHOICES = [
        (1, "Year 1"),
        (2, "Year 2"),
        (3, "Year 3"),
        (4, "Year 4"),
        (5, "Year 5"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile"
    )

    student_id = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True
    )

    institution = models.CharField(
        max_length=150,
        blank=True
    )

    course = models.CharField(
        max_length=150,
        blank=True
    )

    year_of_study = models.PositiveSmallIntegerField(
        choices=YEAR_CHOICES,
        null=True,
        blank=True
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    bio = models.TextField(
        max_length=500,
        blank=True
    )

    avatar = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"
