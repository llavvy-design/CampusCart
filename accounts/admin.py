
from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "student_id",
        "institution",
        "course",
        "year_of_study",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "student_id",
        "course",
    )

    list_filter = (
        "institution",
        "year_of_study",
    )
