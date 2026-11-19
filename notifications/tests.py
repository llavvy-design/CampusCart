
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from notifications.models import Notification
from notifications.services.notification_service import (
    create_notification,
)

User = get_user_model()


class NotificationServiceTests(TestCase):

    def setUp(self):
        self.recipient = User.objects.create_user(
            username="notification_recipient",
            password="TestPassword123!",
        )

        self.actor = User.objects.create_user(
            username="notification_actor",
            password="TestPassword123!",
        )

    def test_create_notification_successfully(self):
        notification = create_notification(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=(
                Notification.NotificationType.POST_LIKED
            ),
            message="Someone liked your post.",
            target_url="/community/posts/1/",
        )

        self.assertIsNotNone(notification)
        self.assertEqual(notification.recipient, self.recipient)
        self.assertEqual(notification.actor, self.actor)
        self.assertEqual(
            notification.notification_type,
            "post_liked",
        )
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_prevent_self_notification(self):
        notification = create_notification(
            recipient=self.recipient,
            actor=self.recipient,
            notification_type=(
                Notification.NotificationType.POST_LIKED
            ),
            message="You liked your own post.",
        )

        self.assertIsNone(notification)

        self.assertEqual(
            Notification.objects.count(),
            0,
        )

    def test_reject_invalid_notification_type(self):
        with self.assertRaises(ValueError):
            create_notification(
                recipient=self.recipient,
                actor=self.actor,
                notification_type="invalid_type",
                message="Invalid notification.",
            )

        self.assertEqual(
            Notification.objects.count(),
            0,
        )

    def test_create_system_notification_without_actor(self):
        notification = create_notification(
            recipient=self.recipient,
            notification_type=(
                Notification.NotificationType.PAYMENT_SUCCESSFUL
            ),
            message="Your payment was successful.",
        )

        self.assertIsNotNone(notification)
        self.assertEqual(notification.recipient, self.recipient)
        self.assertIsNone(notification.actor)

    def test_notification_uses_default_empty_target_url(self):
        notification = create_notification(
            recipient=self.recipient,
            notification_type=(
                Notification.NotificationType.ORDER_PLACED
            ),
            message="You have received a new order.",
        )

        self.assertEqual(notification.target_url, "")

class NotificationAPITests(TestCase):

    def setUp(self):
        self.recipient = User.objects.create_user(
            username="api_notification_user",
            password="TestPassword123!",
        )

        self.other_user = User.objects.create_user(
            username="other_notification_user",
            password="TestPassword123!",
        )

        self.actor = User.objects.create_user(
            username="api_notification_actor",
            password="TestPassword123!",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.recipient)

        self.notification = Notification.objects.create(
            recipient=self.recipient,
            actor=self.actor,
            notification_type=Notification.NotificationType.POST_LIKED,
            message="Someone liked your post.",
            target_url="/community/posts/1/",
        )

        self.list_url = "/api/notifications/"
        self.unread_count_url = "/api/notifications/unread-count/"
        self.mark_all_url = "/api/notifications/mark-all-read/"

    def test_authenticated_user_can_list_own_notifications(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["message"],
            "Someone liked your post.",
        )
        self.assertEqual(
            response.data["results"][0]["actor_username"],
            self.actor.username,
        )

    def test_user_cannot_see_another_users_notifications(self):
        Notification.objects.create(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.PAYMENT_SUCCESSFUL,
            message="Private payment notification.",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        messages = [
            item["message"]
            for item in response.data["results"]
        ]

        self.assertNotIn("Private payment notification.", messages)

    def test_notification_list_is_paginated(self):
        for index in range(24):
            Notification.objects.create(
                recipient=self.recipient,
                notification_type=Notification.NotificationType.POST_COMMENTED,
                message=f"Test notification {index}",
            )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])

    def test_notification_page_size_is_limited(self):
        for index in range(55):
            Notification.objects.create(
                recipient=self.recipient,
                notification_type=Notification.NotificationType.POST_COMMENTED,
                message=f"Test notification {index}",
            )

        response = self.client.get(
            self.list_url,
            {"page_size": 100},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 50)

    def test_unread_notification_count(self):
        Notification.objects.create(
            recipient=self.recipient,
            notification_type=Notification.NotificationType.PAYMENT_SUCCESSFUL,
            message="Payment received.",
        )

        self.notification.is_read = True
        self.notification.save(update_fields=["is_read"])

        response = self.client.get(self.unread_count_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["unread_count"], 1)

    def test_user_can_mark_own_notification_as_read(self):
        url = f"{self.list_url}{self.notification.pk}/mark-read/"

        response = self.client.post(url)

        self.notification.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.notification.is_read)
        self.assertIsNotNone(self.notification.read_at)

    def test_user_cannot_mark_another_users_notification_as_read(self):
        other_notification = Notification.objects.create(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.POST_LIKED,
            message="Another user's notification.",
        )

        url = f"{self.list_url}{other_notification.pk}/mark-read/"

        response = self.client.post(url)

        other_notification.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertFalse(other_notification.is_read)

    def test_marking_all_notifications_as_read(self):
        second_notification = Notification.objects.create(
            recipient=self.recipient,
            notification_type=Notification.NotificationType.POST_COMMENTED,
            message="Someone commented on your post.",
        )

        other_notification = Notification.objects.create(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.POST_LIKED,
            message="Private notification.",
        )

        response = self.client.post(self.mark_all_url)

        self.notification.refresh_from_db()
        second_notification.refresh_from_db()
        other_notification.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated_count"], 2)

        self.assertTrue(self.notification.is_read)
        self.assertTrue(second_notification.is_read)

        self.assertFalse(other_notification.is_read)

    def test_unauthenticated_user_cannot_access_notification_endpoints(self):
        self.client.force_authenticate(user=None)

        urls = [
            self.list_url,
            self.unread_count_url,
            self.mark_all_url,
            f"{self.list_url}{self.notification.pk}/mark-read/",
        ]

        for url in urls:
            with self.subTest(url=url):
                if url.endswith("mark-read/") or url == self.mark_all_url:
                    response = self.client.post(url)
                else:
                    response = self.client.get(url)

                self.assertEqual(response.status_code, 401)
