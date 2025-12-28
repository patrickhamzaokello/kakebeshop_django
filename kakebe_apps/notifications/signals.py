# kakebe_apps/notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from kakebe_apps.orders.models import OrderIntent
from kakebe_apps.merchants.models import Merchant
from .services import NotificationService
from .models import NotificationType


@receiver(post_save, sender=OrderIntent)
def handle_order_created(sender, instance, created, **kwargs):
    """
    Send notifications when order is created or updated
    """
    if created:
        # Notify buyer
        NotificationService.create_order_notification(
            user=instance.buyer,
            order=instance,
            notification_type=NotificationType.ORDER_CREATED,
        )

        # Notify merchant
        if hasattr(instance, 'merchant') and instance.merchant:
            merchant_user = instance.merchant.user
            NotificationService.create_merchant_order_notification(
                merchant_user=merchant_user,
                order=instance,
            )
    else:
        # Order updated - check for status changes
        if instance.tracker.has_changed('status'):
            notification_type = None

            if instance.status == 'CONTACTED':
                notification_type = NotificationType.ORDER_CONTACTED
            elif instance.status == 'CONFIRMED':
                notification_type = NotificationType.ORDER_CONFIRMED
            elif instance.status == 'COMPLETED':
                notification_type = NotificationType.ORDER_COMPLETED
            elif instance.status == 'CANCELLED':
                notification_type = NotificationType.ORDER_CANCELLED

            if notification_type:
                NotificationService.create_order_notification(
                    user=instance.buyer,
                    order=instance,
                    notification_type=notification_type,
                )


@receiver(post_save, sender=Merchant)
def handle_merchant_status_change(sender, instance, created, **kwargs):
    """
    Send notifications when merchant account status changes
    """
    if not created and instance.tracker.has_changed('status'):
        notification_type = None

        if instance.status == 'ACTIVE' and instance.verified:
            notification_type = NotificationType.MERCHANT_APPROVED
        elif instance.status == 'INACTIVE':
            notification_type = NotificationType.MERCHANT_DEACTIVATED
        elif instance.status == 'SUSPENDED':
            notification_type = NotificationType.MERCHANT_SUSPENDED

        if notification_type:
            NotificationService.create_merchant_status_notification(
                merchant_user=instance.user,
                merchant=instance,
                notification_type=notification_type,
            )