
from rest_framework import serializers

from .models import Post, Comment, Like


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(
        source="author.username",
        read_only=True,
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "author",
            "author_username",
            "content",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "post",
            "author",
            "author_username",
            "created_at",
            "updated_at",
        ]

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "A comment cannot be empty."
            )
        return value


class LikeSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    class Meta:
        model = Like
        fields = [
            "id",
            "user",
            "username",
            "created_at",
        ]
        read_only_fields = fields


class PostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(
        source="author.username",
        read_only=True,
    )

    comments_count = serializers.IntegerField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)

    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "author_username",
            "content",
            "image",
            "comments_count",
            "likes_count",
            "is_liked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "author",
            "author_username",
            "comments_count",
            "likes_count",
            "is_liked",
            "created_at",
            "updated_at",
        ]

    def get_is_liked(self, obj):
        return bool(getattr(obj, "is_liked", False))
    
    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "A post cannot be empty."
            )
        return value
