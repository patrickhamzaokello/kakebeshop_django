import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from KakebeShop import settings
from kakebe_apps.listings.models import Listing
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.orders.models import OrderIntent



class SavedSearch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_searches')
    name = models.CharField(max_length=255)
    search_query = models.TextField()
    filters = models.JSONField()
    notification_enabled = models.BooleanField(default=False)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saved_searches'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['notification_enabled']),
        ]

    def __str__(self):
        return f"{self.user.name} - {self.name}"

class Conversation(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
        ('BLOCKED', 'Blocked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    order_intent = models.ForeignKey(OrderIntent, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='buyer_conversations')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller_conversations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversations'
        indexes = [
            models.Index(fields=['buyer']),
            models.Index(fields=['seller']),
            models.Index(fields=['listing']),
            models.Index(fields=['status']),
            models.Index(fields=['last_message_at']),
        ]

    def __str__(self):
        return f"Conversation between {self.buyer.name} and {self.seller.name}"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField()
    attachment = models.URLField(null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'messages'
        indexes = [
            models.Index(fields=['conversation']),
            models.Index(fields=['sender']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['is_read']),
        ]
        ordering = ['sent_at']

    def __str__(self):
        return f"Message from {self.sender.name}"


class ListingReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listing_reviews')
    order_intent = models.ForeignKey(OrderIntent, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], db_index=True)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'listing_reviews'
        unique_together = ('listing', 'user')
        indexes = [
            models.Index(fields=['listing']),
            models.Index(fields=['user']),
            models.Index(fields=['rating']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Review for {self.listing.title} by {self.user.name}"


class MerchantReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='merchant_reviews')
    order_intent = models.ForeignKey(OrderIntent, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], db_index=True)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'merchant_reviews'
        unique_together = ('merchant', 'user')
        indexes = [
            models.Index(fields=['merchant']),
            models.Index(fields=['user']),
            models.Index(fields=['rating']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Review for {self.merchant.display_name} by {self.user.name}"


class MerchantScore(models.Model):
    merchant = models.OneToOneField(Merchant, on_delete=models.CASCADE, primary_key=True, related_name='score')
    active_listing_count = models.IntegerField(default=0)
    total_listing_count = models.IntegerField(default=0)
    response_rate = models.FloatField(default=0.0)
    average_response_time_minutes = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)
    report_count = models.IntegerField(default=0)
    score = models.FloatField(default=0.0, db_index=True)
    last_calculated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'merchant_scores'
        indexes = [
            models.Index(fields=['merchant']),
            models.Index(fields=['score']),
        ]

    def __str__(self):
        return f"Score for {self.merchant.display_name}"


class Report(models.Model):
    REASON_CHOICES = [
        ('SPAM', 'Spam'),
        ('INAPPROPRIATE', 'Inappropriate'),
        ('SCAM', 'Scam'),
        ('FAKE', 'Fake'),
        ('OFFENSIVE', 'Offensive'),
        ('OTHER', 'Other'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('UNDER_REVIEW', 'Under Review'),
        ('RESOLVED', 'Resolved'),
        ('DISMISSED', 'Dismissed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    reported_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='reports_received')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    reviewed_by = models.ForeignKey('AdminUser', on_delete=models.SET_NULL, null=True, blank=True)
    review_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reports'
        indexes = [
            models.Index(fields=['reporter']),
            models.Index(fields=['listing']),
            models.Index(fields=['merchant']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Report by {self.reporter.name}"


class FollowUpRule(models.Model):
    TRIGGER_TYPE_CHOICES = [
        ('ORDER_INTENT', 'Order Intent'),
        ('LISTING_EXPIRING', 'Listing Expiring'),
        ('INACTIVE_USER', 'Inactive User'),
        ('ABANDONED_CART', 'Abandoned Cart'),
    ]

    NOTIFICATION_TYPE_CHOICES = [
        ('PUSH', 'Push Notification'),
        ('SMS', 'SMS'),
        ('EMAIL', 'Email'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    trigger_type = models.CharField(max_length=30, choices=TRIGGER_TYPE_CHOICES)
    trigger_status = models.CharField(max_length=50, null=True, blank=True)
    delay_minutes = models.IntegerField()
    message_template = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'follow_up_rules'
        indexes = [
            models.Index(fields=['trigger_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class FollowUpLog(models.Model):
    STATUS_CHOICES = [
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('SKIPPED', 'Skipped'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_intent = models.ForeignKey(OrderIntent, on_delete=models.CASCADE, null=True, blank=True)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rule = models.ForeignKey(FollowUpRule, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'follow_up_logs'
        indexes = [
            models.Index(fields=['order_intent']),
            models.Index(fields=['user']),
            models.Index(fields=['rule']),
            models.Index(fields=['sent_at']),
        ]

    def __str__(self):
        return f"Follow-up for {self.user.name}"

class AdminUser(models.Model):
    ROLE_CHOICES = [
        ('SUPER_ADMIN', 'Super Admin'),
        ('MODERATOR', 'Moderator'),
        ('SUPPORT', 'Support'),
        ('FINANCE', 'Finance'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    permissions = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_users'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.user.name} ({self.role})"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.ForeignKey(AdminUser, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField()
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['admin']),
            models.Index(fields=['entity_type']),
            models.Index(fields=['entity_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.action} on {self.entity_type}"


class ApiUsage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, null=True, blank=True)
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    request_count = models.IntegerField(default=1)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_usage'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['merchant']),
            models.Index(fields=['date']),
            models.Index(fields=['endpoint']),
        ]

    def __str__(self):
        return f"{self.endpoint} - {self.date}"


class ActivityLog(models.Model):
    ACTIVITY_TYPE_CHOICES = [
        ('VIEW_LISTING', 'View Listing'),
        ('SEARCH', 'Search'),
        ('ADD_TO_CART', 'Add to Cart'),
        ('CREATE_ORDER', 'Create Order'),
        ('CONTACT_SELLER', 'Contact Seller'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPE_CHOICES)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'activity_logs'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['listing']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.activity_type} - {self.created_at}"


class UserIntent(models.Model):
    """Model to store user's marketplace intent (buy, sell, or both)"""

    INTENT_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('both', 'Both'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='marketplace_intent',
        help_text="User associated with this intent"
    )
    intent = models.CharField(
        max_length=10,
        choices=INTENT_CHOICES,
        help_text="User's marketplace intent"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_intents'
        verbose_name = 'User Intent'
        verbose_name_plural = 'User Intents'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['intent']),
            models.Index(fields=['-updated_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.get_intent_display()}"

    def clean(self):
        """Validate intent value"""
        if self.intent not in dict(self.INTENT_CHOICES):
            raise ValidationError({
                'intent': 'Invalid intent value. Must be buy, sell, or both.'
            })


class OnboardingStatus(models.Model):
    """Track user's onboarding progress"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='onboarding_status'
    )
    intent_completed = models.BooleanField(default=False)
    categories_completed = models.BooleanField(default=False)
    profile_completed = models.BooleanField(default=False)
    is_onboarding_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'onboarding_statuses'
        verbose_name = 'Onboarding Status'
        verbose_name_plural = 'Onboarding Statuses'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['is_onboarding_complete']),
            models.Index(fields=['-updated_at']),
        ]

    def __str__(self):
        status = 'Complete' if self.is_onboarding_complete else 'Incomplete'
        return f"{self.user.email} - {status}"

    def check_completion(self):
        """Check if all onboarding steps are complete"""
        from django.utils import timezone

        # Check if intent is completed (minimum requirement)
        # You can add more conditions based on your requirements
        if self.intent_completed and not self.is_onboarding_complete:
            self.is_onboarding_complete = True
            self.completed_at = timezone.now()
            self.save()
        elif not self.intent_completed and self.is_onboarding_complete:
            # If intent is uncompleted, mark onboarding as incomplete
            self.is_onboarding_complete = False
            self.completed_at = None
            self.save()

class PushToken(models.Model):
    """Model to store user push notification tokens"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_tokens'
    )
    token = models.CharField(max_length=200, unique=True)

    # Device/platform info
    device_id = models.CharField(max_length=100, blank=True)
    platform = models.CharField(
        max_length=20,
        choices=[
            ('ios', 'iOS'),
            ('android', 'Android'),
            ('web', 'Web'),
        ],
        blank=True
    )

    # Status tracking
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.token.strip():
            raise ValidationError('Push token cannot be empty.')

        # Basic validation for Expo push tokens
        if self.token.startswith('ExponentPushToken[') and not self.token.endswith(']'):
            raise ValidationError('Invalid Expo push token format.')

    def __str__(self):
        return f"Push token for {self.user.username} ({self.platform or 'unknown'})"

    class Meta:
        db_table = 'push_tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['token']),
            models.Index(fields=['last_used']),
        ]
        unique_together = ['user', 'device_id']  # One token per user per device