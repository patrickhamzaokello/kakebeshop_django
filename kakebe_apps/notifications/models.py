# kakebe_apps/notifications/models.py
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class NotificationType(models.TextChoices):
    """Types of notifications"""
    ORDER_CREATED = 'ORDER_CREATED', 'Order Created'
    ORDER_CONTACTED = 'ORDER_CONTACTED', 'Order Contacted'
    ORDER_CONFIRMED = 'ORDER_CONFIRMED', 'Order Confirmed'
    ORDER_COMPLETED = 'ORDER_COMPLETED', 'Order Completed'
    ORDER_CANCELLED = 'ORDER_CANCELLED', 'Order Cancelled'

    MERCHANT_NEW_ORDER = 'MERCHANT_NEW_ORDER', 'New Order Received'
    MERCHANT_APPROVED = 'MERCHANT_APPROVED', 'Merchant Account Approved'
    MERCHANT_DEACTIVATED = 'MERCHANT_DEACTIVATED', 'Merchant Account Deactivated'
    MERCHANT_SUSPENDED = 'MERCHANT_SUSPENDED', 'Merchant Account Suspended'

    LISTING_APPROVED = 'LISTING_APPROVED', 'Listing Approved'
    LISTING_REJECTED = 'LISTING_REJECTED', 'Listing Rejected'


class NotificationChannel(models.TextChoices):
    """Notification delivery channels"""
    EMAIL = 'EMAIL', 'Email'
    PUSH = 'PUSH', 'Push Notification'
    IN_APP = 'IN_APP', 'In-App Notification'


class NotificationStatus(models.TextChoices):
    """Status of notification delivery"""
    PENDING = 'PENDING', 'Pending'
    SENT = 'SENT', 'Sent'
    DELIVERED = 'DELIVERED', 'Delivered'
    FAILED = 'FAILED', 'Failed'
    READ = 'READ', 'Read'


class Notification(models.Model):
    """Base notification model for tracking all notifications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Recipient
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # Notification details
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices
    )
    title = models.CharField(max_length=255)
    message = models.TextField()

    # Related objects (generic foreign keys would be better, but keeping it simple)
    order_id = models.UUIDField(null=True, blank=True)
    merchant_id = models.UUIDField(null=True, blank=True)
    listing_id = models.UUIDField(null=True, blank=True)

    # Additional data (JSON for flexibility)
    metadata = models.JSONField(default=dict, blank=True)

    # Status tracking
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type} - {self.user.email}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationDelivery(models.Model):
    """Track delivery attempts for each notification channel"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='deliveries'
    )

    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices
    )

    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING
    )

    # Delivery details
    recipient = models.CharField(max_length=255)  # Email or device token
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    # External service response
    external_id = models.CharField(max_length=255, blank=True, null=True)
    response_data = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['channel', 'status']),
        ]
        verbose_name_plural = 'Notification Deliveries'

    def __str__(self):
        return f"{self.channel} - {self.notification.notification_type} - {self.status}"

    def can_retry(self):
        """Check if delivery can be retried"""
        return (
                self.status == NotificationStatus.FAILED and
                self.retry_count < self.max_retries and
                (self.next_retry_at is None or self.next_retry_at <= timezone.now())
        )


class UserNotificationPreference(models.Model):
    """User preferences for notification channels"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    # Email preferences
    email_enabled = models.BooleanField(default=True)
    email_order_updates = models.BooleanField(default=True)
    email_merchant_updates = models.BooleanField(default=True)
    email_marketing = models.BooleanField(default=False)

    # Push notification preferences
    push_enabled = models.BooleanField(default=True)
    push_order_updates = models.BooleanField(default=True)
    push_merchant_updates = models.BooleanField(default=True)

    # Device tokens for push notifications
    device_tokens = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.email}"

    def add_device_token(self, token):
        """Add a new device token"""
        if token not in self.device_tokens:
            self.device_tokens.append(token)
            self.save(update_fields=['device_tokens'])

    def remove_device_token(self, token):
        """Remove a device token"""
        if token in self.device_tokens:
            self.device_tokens.remove(token)
            self.save(update_fields=['device_tokens'])