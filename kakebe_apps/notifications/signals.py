# kakebe_apps/notifications/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from kakebe_apps.orders.models import OrderIntent
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.listings.models import Listing
from .services import NotificationService
from .models import NotificationType


@receiver(pre_save, sender=OrderIntent)
def store_order_previous_state(sender, instance, **kwargs):
    """Attach previous status to the instance so post_save can compare."""
    if instance.pk:
        try:
            instance._previous_status = OrderIntent.objects.values_list(
                'status', flat=True
            ).get(pk=instance.pk)
        except OrderIntent.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=OrderIntent)
def handle_order_created_or_updated(sender, instance, created, **kwargs):
    """Send notifications when an order is created or its status changes."""
    if created:
        # Notify buyer about order creation
        NotificationService.create_order_notification(
            user=instance.buyer,
            order=instance,
            notification_type=NotificationType.ORDER_CREATED,
        )

        # Notify merchant about new order
        if hasattr(instance, 'merchant') and instance.merchant:
            NotificationService.create_merchant_order_notification(
                merchant_user=instance.merchant.user,
                order=instance,
            )
    else:
        old_status = getattr(instance, '_previous_status', None)

        if old_status and old_status != instance.status:
            status_to_type = {
                'CONTACTED': NotificationType.ORDER_CONTACTED,
                'CONFIRMED': NotificationType.ORDER_CONFIRMED,
                'COMPLETED': NotificationType.ORDER_COMPLETED,
                'CANCELLED': NotificationType.ORDER_CANCELLED,
            }
            notification_type = status_to_type.get(instance.status)

            if notification_type:
                NotificationService.create_order_notification(
                    user=instance.buyer,
                    order=instance,
                    notification_type=notification_type,
                )


@receiver(pre_save, sender=Merchant)
def store_merchant_previous_state(sender, instance, **kwargs):
    """Attach previous status/verified to the instance so post_save can compare."""
    if instance.pk:
        try:
            prev = Merchant.objects.values('status', 'verified').get(pk=instance.pk)
            instance._previous_status = prev['status']
            instance._previous_verified = prev['verified']
        except Merchant.DoesNotExist:
            instance._previous_status = None
            instance._previous_verified = None
    else:
        instance._previous_status = None
        instance._previous_verified = None


@receiver(post_save, sender=Merchant)
def handle_merchant_status_change(sender, instance, created, **kwargs):
    """Send notifications when a merchant account status or verification changes."""
    if created:
        return

    old_status = getattr(instance, '_previous_status', None)
    old_verified = getattr(instance, '_previous_verified', None)

    notification_type = None

    # Newly approved: first time becoming ACTIVE+verified
    if (instance.status == 'ACTIVE'
            and instance.verified
            and not old_verified):
        notification_type = NotificationType.MERCHANT_APPROVED

    # Reactivated: coming back from SUSPENDED or BANNED to ACTIVE (already verified)
    elif (instance.status == 'ACTIVE'
          and instance.verified
          and old_status in ('SUSPENDED', 'BANNED')
          and old_verified):
        notification_type = NotificationType.MERCHANT_REACTIVATED

    # Suspended
    elif instance.status == 'SUSPENDED' and old_status != 'SUSPENDED':
        notification_type = NotificationType.MERCHANT_SUSPENDED

    # Banned
    elif instance.status == 'BANNED' and old_status != 'BANNED':
        notification_type = NotificationType.MERCHANT_BANNED

    if notification_type:
        NotificationService.create_merchant_status_notification(
            merchant_user=instance.user,
            merchant=instance,
            notification_type=notification_type,
        )


# ── Listing signals ──────────────────────────────────────────────────────────

@receiver(pre_save, sender=Listing)
def store_listing_previous_state(sender, instance, **kwargs):
    """Attach previous status and is_verified so post_save can detect changes."""
    if instance.pk:
        try:
            prev = Listing.objects.values('status', 'is_verified').get(pk=instance.pk)
            instance._previous_status = prev['status']
            instance._previous_verified = prev['is_verified']
        except Listing.DoesNotExist:
            instance._previous_status = None
            instance._previous_verified = None
    else:
        instance._previous_status = None
        instance._previous_verified = None


@receiver(post_save, sender=Listing)
def handle_listing_status_change(sender, instance, created, **kwargs):
    """Send push/email notifications to the merchant when a listing changes state."""
    merchant_user = instance.merchant.user

    if created:
        # Only notify on submit — skip drafts saved silently
        if instance.status == 'PENDING':
            NotificationService.create_listing_notification(
                merchant_user=merchant_user,
                listing=instance,
                notification_type=NotificationType.LISTING_SUBMITTED,
            )
        return

    old_status = getattr(instance, '_previous_status', None)
    old_verified = getattr(instance, '_previous_verified', None)

    # Approved: became ACTIVE + verified for the first time
    if (instance.status == 'ACTIVE'
            and instance.is_verified
            and (old_status != 'ACTIVE' or not old_verified)):
        NotificationService.create_listing_notification(
            merchant_user=merchant_user,
            listing=instance,
            notification_type=NotificationType.LISTING_APPROVED,
        )

    # Rejected
    elif instance.status == 'REJECTED' and old_status != 'REJECTED':
        NotificationService.create_listing_notification(
            merchant_user=merchant_user,
            listing=instance,
            notification_type=NotificationType.LISTING_REJECTED,
        )