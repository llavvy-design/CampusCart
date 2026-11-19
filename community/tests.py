
from io import BytesIO
import tempfile

from PIL import Image

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Post, Comment, Like


class CommunityAPITests(APITestCase):

    def setUp(self):
        self.temp_media = tempfile.TemporaryDirectory()
        self.media_override = override_settings(
            MEDIA_ROOT=self.temp_media.name
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.temp_media.cleanup)

        self.user = User.objects.create_user(
            username="student_one",
            email="studentone@example.com",
            password="CampusCartPass123!",
        )

        self.other_user = User.objects.create_user(
            username="student_two",
            email="studenttwo@example.com",
            password="CampusCartPass123!",
        )

        self.post = Post.objects.create(
            author=self.user,
            content="My first CampusCart community post.",
        )

        self.other_post = Post.objects.create(
            author=self.other_user,
            content="Another student's community post.",
        )

        self.comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            content="This is my comment.",
        )

        self.feed_url = "/api/community/posts/"
        self.post_url = f"/api/community/posts/{self.post.pk}/"
        self.other_post_url = (
            f"/api/community/posts/{self.other_post.pk}/"
        )
        self.comments_url = (
            f"/api/community/posts/{self.post.pk}/comments/"
        )
        self.like_url = (
            f"/api/community/posts/{self.post.pk}/like/"
        )

        self.client.force_authenticate(user=self.user)

    # -------------------------
    # POST TESTS
    # -------------------------

    def test_students_can_view_community_feed(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.feed_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_student_can_create_post(self):
        response = self.client.post(
            self.feed_url,
            {"content": "Hello CampusCart!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Post.objects.filter(author=self.user).count(),
            2,
        )

    def test_post_author_is_assigned_automatically(self):
        response = self.client.post(
            self.feed_url,
            {
                "content": "A new post.",
                "author": self.other_user.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"], self.user.pk)

    def test_anonymous_student_cannot_create_post(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.feed_url,
            {"content": "Anonymous post"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_student_can_update_own_post(self):
        response = self.client.patch(
            self.post_url,
            {"content": "Updated post content."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.post.refresh_from_db()
        self.assertEqual(self.post.content, "Updated post content.")

    def test_student_cannot_update_another_students_post(self):
        response = self.client.patch(
            self.other_post_url,
            {"content": "Trying to change someone else's post."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_student_cannot_delete_another_students_post(self):
        response = self.client.delete(self.other_post_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Post.objects.filter(pk=self.other_post.pk).exists()
        )

    def test_student_can_delete_own_post(self):
        response = self.client.delete(self.post_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Post.objects.filter(pk=self.post.pk).exists()
        )

    def test_empty_post_is_rejected(self):
        response = self.client.post(
            self.feed_url,
            {"content": "   "},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_student_can_upload_post_image(self):
        image_buffer = BytesIO()
        image = Image.new("RGB", (100, 100), color="green")
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        uploaded_image = SimpleUploadedFile(
            "community.png",
            image_buffer.read(),
            content_type="image/png",
        )

        response = self.client.post(
            self.feed_url,
            {
                "content": "A post with an image.",
                "image": uploaded_image,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        post = Post.objects.get(content="A post with an image.")
        self.assertTrue(post.image)

    # -------------------------
    # COMMENT TESTS
    # -------------------------

    def test_students_can_view_comments(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.comments_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_authenticated_student_can_comment(self):
        response = self.client.post(
            self.comments_url,
            {"content": "Great post!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        new_comment = Comment.objects.get(content="Great post!")
        self.assertEqual(new_comment.author, self.user)
        self.assertEqual(new_comment.post, self.post)

    def test_comment_author_is_assigned_automatically(self):
        response = self.client.post(
            self.comments_url,
            {
                "content": "My comment.",
                "author": self.other_user.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"], self.user.pk)

    def test_empty_comment_is_rejected(self):
        response = self.client.post(
            self.comments_url,
            {"content": "   "},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_student_cannot_update_another_students_comment(self):
        other_comment = Comment.objects.create(
            post=self.post,
            author=self.other_user,
            content="Another student's comment.",
        )

        url = f"{self.comments_url}{other_comment.pk}/"

        response = self.client.patch(
            url,
            {"content": "Trying to edit another comment."},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_comment_author_can_update_own_comment(self):
        url = f"{self.comments_url}{self.comment.pk}/"

        response = self.client.patch(
            url,
            {"content": "My updated comment."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "My updated comment.")

    # -------------------------
    # LIKE TESTS
    # -------------------------

    def test_student_can_like_post(self):
        response = self.client.post(self.like_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["liked"])
        self.assertEqual(Like.objects.count(), 1)

    def test_student_can_unlike_post(self):
        Like.objects.create(
            post=self.post,
            user=self.user,
        )

        response = self.client.post(self.like_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["liked"])
        self.assertEqual(Like.objects.count(), 0)

    def test_student_cannot_like_post_without_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.like_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_student_cannot_like_nonexistent_post(self):
        response = self.client.post(
            "/api/community/posts/99999/like/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


    def test_community_feed_returns_paginated_response(self):
        response = self.client.get(self.feed_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)

    def test_community_feed_respects_requested_page_size(self):
        Post.objects.bulk_create([
            Post(
                author=self.user,
                content=f"Pagination test post {number}",
            )
            for number in range(15)
        ])

        response = self.client.get(
            self.feed_url,
            {"page_size": 5},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertEqual(response.data["count"], 17)
