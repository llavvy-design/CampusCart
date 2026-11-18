from django.contrib import admin
from .models import Post, Comment, Like


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class LikeInline(admin.TabularInline):
    model = Like
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "author",
        "content_preview",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "content",
        "author__username",
        "author__email",
    )
    list_filter = ("created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CommentInline, LikeInline]

    @admin.display(description="Content")
    def content_preview(self, obj):
        return obj.content[:75]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "content_preview", "created_at")
    search_fields = (
        "content",
        "author__username",
        "post__content",
    )
    list_filter = ("created_at",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Comment")
    def content_preview(self, obj):
        return obj.content[:75]


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")
    search_fields = (
        "user__username",
        "post__content",
    )
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
    