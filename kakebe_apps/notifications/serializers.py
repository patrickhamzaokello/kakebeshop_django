# kakebe_apps/notifications/serializers.py
from rest_framework import serializers
from .models import Notification, UserNotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""

    class Meta:
        model = Notification
        fields = [
            'id',
            'notification_type',
            'title',
            'message',
            'order_id',
            'merchant_id',
            'listing_id',
            'metadata',
            'is_read',
            'read_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for User Notification Preferences"""

    class Meta:
        model = UserNotificationPreference
        fields = [
            'id',
            'email_enabled',
            'email_order_updates',
            'email_merchant_updates',
            'email_marketing',
            'push_enabled',
            'push_order_updates',
            'push_merchant_updates',
            'device_tokens',
        ]
        read_only_fields = ['id']

    def update(self, instance, validated_data):
        # Handle device_tokens separately
        device_tokens = validated_data.pop('device_tokens', None)

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class DeviceTokenSerializer(serializers.Serializer):
    """Serializer for adding/removing device tokens"""
    token = serializers.CharField(required=True, max_length=500)