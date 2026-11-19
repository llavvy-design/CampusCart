from django.conf import settings
from django.db import models


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        POST_LIKED = "post_liked", "Post Liked"
        POST_COMMENTED = "post_commented", "Post Commented"
        ORDER_PLACED = "order_placed", "Order Placed"
        ORDER_STATUS_UPDATED = (
            "order_status_updated",
            "Order Status Updated",
        )
        PAYMENT_SUCCESSFUL = (
            "payment_successful",
            "Payment Successful",
        )
        PAYMENT_FAILED = (
            "payment_failed",
            "Payment Failed",
        )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
    )

    message = models.CharField(max_length=255)

    target_url = models.CharField(
        max_length=500,
        blank=True,
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(
                fields=["recipient", "-created_at"],
                name="notif_recipient_created_idx",
            ),
            models.Index(
                fields=["recipient", "is_read"],
                name="notif_recipient_read_idx",
            ),
        ]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return (
            f"{self.notification_type} "
            f"for {self.recipient.username}"
        )