
from django.db import transaction

from notifications.models import Notification


@transaction.atomic
def create_notification(
    recipient,
    notification_type,
    message,
    actor=None,
    target_url="",
):
    """
    Create a notification for a recipient.

    Returns the created Notification object.
    Returns None when the actor and recipient are the same user.
    """

    # Prevent users from receiving notifications
    # triggered by their own actions.
    if actor is not None and actor.pk == recipient.pk:
        return None

    # Validate the notification type.
    valid_types = Notification.NotificationType.values

    if notification_type not in valid_types:
        raise ValueError(
            f"Invalid notification type: {notification_type}"
        )

    # Create and save the notification.
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        message=message,
        target_url=target_url,
    )

    return notification
