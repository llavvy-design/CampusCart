from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

from .models import Notification
from .pagination import NotificationPagination
from .serializers import NotificationSerializer


class NotificationListView(ListAPIView):
    """
    Return notifications belonging to the authenticated user.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination

    def get_queryset(self):
        return (
            Notification.objects
            .filter(recipient=self.request.user)
            .select_related("actor")
            .order_by("-created_at", "-pk")
        )


class UnreadNotificationCountView(APIView):
    """
    Return the number of unread notifications for the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()

        return Response(
            {"unread_count": unread_count},
            status=status.HTTP_200_OK,
        )


class MarkNotificationReadView(APIView):
    """
    Mark one of the authenticated user's notifications as read.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        notification = get_object_or_404(
            Notification,
            pk=notification_id,
            recipient=request.user,
        )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(
                update_fields=["is_read", "read_at"]
            )

        return Response(
            {
                "message": "Notification marked as read.",
                "notification_id": notification.pk,
                "is_read": notification.is_read,
                "read_at": notification.read_at,
            },
            status=status.HTTP_200_OK,
        )


class MarkAllNotificationsReadView(APIView):
    """
    Mark all unread notifications belonging to the authenticated user as read.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        read_at = timezone.now()

        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(
            is_read=True,
            read_at=read_at,
        )

        return Response(
            {
                "message": "All notifications marked as read.",
                "updated_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )