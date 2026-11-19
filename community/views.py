from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.parsers import (
    JSONParser,
    MultiPartParser,
    FormParser,
)
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Post, Comment, Like
from .permissions import IsAuthorOrReadOnly
from .serializers import PostSerializer, CommentSerializer
from .pagination import CommunityPagination
from notifications.services.notification_service import (
    create_notification,
)

class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    pagination_class = CommunityPagination

    def get_queryset(self):
        user = self.request.user

        queryset = Post.objects.select_related(
            "author"
        ).annotate(
            comments_count=Count("comments", distinct=True),
            likes_count=Count("likes", distinct=True),
        )

        if user.is_authenticated:
            user_likes = Like.objects.filter(
                post_id=OuterRef("pk"),
                user=user,
            )
            queryset = queryset.annotate(
                is_liked=Exists(user_likes)
            )
        else:
            queryset = queryset.annotate(
                is_liked=Exists(
                    Like.objects.none().filter(
                        post_id=OuterRef("pk")
                    )
                )
            )

        return queryset.order_by("-created_at", "-pk")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PostSerializer
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly,
    ]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user

        queryset = Post.objects.select_related(
            "author"
        ).annotate(
            comments_count=Count("comments", distinct=True),
            likes_count=Count("likes", distinct=True),
        )

        if user.is_authenticated:
            queryset = queryset.annotate(
                is_liked=Exists(
                    Like.objects.filter(
                        post_id=OuterRef("pk"),
                        user=user,
                    )
                )
            )
        else:
            queryset = queryset.annotate(
                is_liked=Exists(
                    Like.objects.none().filter(
                        post_id=OuterRef("pk")
                    )
                )
            )

        return queryset


class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Comment.objects.filter(
            post_id=self.kwargs["post_id"]
        ).select_related("author", "post")

    def perform_create(self, serializer):
        post = get_object_or_404(
            Post,
            pk=self.kwargs["post_id"],
        )

        comment = serializer.save(
            post=post,
            author=self.request.user,
        )

        create_notification(
            recipient=post.author,
            actor=self.request.user,
            notification_type="post_commented",
            message="Someone commented on your post.",
            target_url=f"/community/posts/{post.pk}/",
    )
class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly,
    ]

    def get_queryset(self):
        return Comment.objects.filter(
            post_id=self.kwargs["post_id"]
        ).select_related("author", "post")

class PostLikeToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)

        like, created = Like.objects.get_or_create(
            post=post,
            user=request.user,
        )

        if not created:
            like.delete()
            liked = False
        else:
            liked = True

            create_notification(
                recipient=post.author,
                actor=request.user,
                notification_type="post_liked",
                message="Someone liked your post.",
                target_url=f"/community/posts/{post.pk}/",
            )

        return Response(
            {
                "liked": liked,
                "likes_count": post.likes.count(),
            },
            status=status.HTTP_200_OK,
        )
