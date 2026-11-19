from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor_username = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "actor_username",
            "notification_type",
            "message",
            "target_url",
            "is_read",
            "created_at",
            "read_at",
        ]
        read_only_fields = fields

    def get_actor_username(self, obj):
        if obj.actor:
            return obj.actor.username
        return None