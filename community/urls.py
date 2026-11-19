from django.urls import path

from .views import (
    PostListCreateView,
    PostDetailView,
    CommentListCreateView,
    CommentDetailView,
    PostLikeToggleView,
)


app_name = "community"

urlpatterns = [
    path(
        "posts/",
        PostListCreateView.as_view(),
        name="post_list_create",
    ),
    path(
        "posts/<int:pk>/",
        PostDetailView.as_view(),
        name="post_detail",
    ),
    path(
        "posts/<int:post_id>/comments/",
        CommentListCreateView.as_view(),
        name="comment_list_create",
    ),
    path(
        "posts/<int:post_id>/comments/<int:pk>/",
        CommentDetailView.as_view(),
        name="comment_detail",
    ),
    path(
        "posts/<int:post_id>/like/",
        PostLikeToggleView.as_view(),
        name="post_like_toggle",
    ),
]