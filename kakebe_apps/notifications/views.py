# kakebe_apps/notifications/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Notification, UserNotificationPreference
from .serializers import (
    NotificationSerializer,
    UserNotificationPreferenceSerializer,
    DeviceTokenSerializer,
)
from .services import NotificationService


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing notifications

    list: Get all notifications for current user
    retrieve: Get a specific notification
    mark_as_read: Mark notification as read
    mark_all_as_read: Mark all notifications as read
    unread_count: Get count of unread notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get only unread notifications"""
        unread_notifications = self.get_queryset().filter(is_read=False)
        serializer = self.get_serializer(unread_notifications, many=True)
        return Response({
            'count': unread_notifications.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = NotificationService.get_unread_count(request.user)
        return Response({'unread_count': count})

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({
            'message': 'Notification marked as read',
            'notification': self.get_serializer(notification).data
        })

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        count = NotificationService.mark_all_as_read(request.user)
        return Response({
            'message': f'{count} notifications marked as read',
            'count': count
        })


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification preferences

    retrieve: Get user's notification preferences
    update: Update notification preferences
    add_device_token: Add a device token for push notifications
    remove_device_token: Remove a device token
    """
    serializer_class = UserNotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'put', 'patch']

    def get_object(self):
        """Get or create preferences for current user"""
        obj, created = UserNotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj

    def list(self, request):
        """Get current user's preferences"""
        preference = self.get_object()
        serializer = self.get_serializer(preference)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_device_token(self, request):
        """Add a device token for push notifications"""
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        preference = self.get_object()
        preference.add_device_token(token)

        return Response({
            'message': 'Device token added successfully',
            'device_tokens': preference.device_tokens
        })

    @action(detail=False, methods=['post'])
    def remove_device_token(self, request):
        """Remove a device token"""
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        preference = self.get_object()
        preference.remove_device_token(token)

        return Response({
            'message': 'Device token removed successfully',
            'device_tokens': preference.device_tokens
        })