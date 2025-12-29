# kakebe_apps/notifications/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from kakebe_apps.orders.models import OrderIntent
from kakebe_apps.merchants.models import Merchant
from .services import NotificationService
from .models import NotificationType

# Store previous state for comparison
_order_previous_state = {}
_merchant_previous_state = {}


@receiver(pre_save, sender=OrderIntent)
def store_order_previous_state(sender, instance, **kwargs):
    """Store the previous state of the order before save"""
    if instance.pk:
        try:
            previous = OrderIntent.objects.get(pk=instance.pk)
            _order_previous_state[instance.pk] = {
                'status': previous.status,
            }
        except OrderIntent.DoesNotExist:
            pass


@receiver(post_save, sender=OrderIntent)
def handle_order_created_or_updated(sender, instance, created, **kwargs):
    """
    Send notifications when order is created or updated
    """
    if created:
        # Notify buyer about order creation
        NotificationService.create_order_notification(
            user=instance.buyer,
            order=instance,
            notification_type=NotificationType.ORDER_CREATED,
        )

        # Notify merchant about new order
        if hasattr(instance, 'merchant') and instance.merchant:
            merchant_user = instance.merchant.user
            NotificationService.create_merchant_order_notification(
                merchant_user=merchant_user,
                order=instance,
            )
    else:
        # Check if status changed
        previous_state = _order_previous_state.get(instance.pk, {})
        old_status = previous_state.get('status')

        if old_status and old_status != instance.status:
            # Status changed - send notification
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

        # Clean up stored state
        if instance.pk in _order_previous_state:
            del _order_previous_state[instance.pk]


@receiver(pre_save, sender=Merchant)
def store_merchant_previous_state(sender, instance, **kwargs):
    """Store the previous state of the merchant before save"""
    if instance.pk:
        try:
            previous = Merchant.objects.get(pk=instance.pk)
            _merchant_previous_state[instance.pk] = {
                'status': previous.status,
                'verified': previous.verified,
            }
        except Merchant.DoesNotExist:
            pass


@receiver(post_save, sender=Merchant)
def handle_merchant_status_change(sender, instance, created, **kwargs):
    """
    Send notifications when merchant account status changes
    """
    if not created:
        previous_state = _merchant_previous_state.get(instance.pk, {})
        old_status = previous_state.get('status')
        old_verified = previous_state.get('verified')

        notification_type = None

        # Check for approval (status becomes ACTIVE and verified becomes True)
        if (instance.status == 'ACTIVE' and instance.verified and
                (old_status != 'ACTIVE' or not old_verified)):
            notification_type = NotificationType.MERCHANT_APPROVED

        # Check for deactivation
        elif instance.status == 'INACTIVE' and old_status != 'INACTIVE':
            notification_type = NotificationType.MERCHANT_DEACTIVATED

        # Check for suspension
        elif instance.status == 'SUSPENDED' and old_status != 'SUSPENDED':
            notification_type = NotificationType.MERCHANT_SUSPENDED

        if notification_type:
            NotificationService.create_merchant_status_notification(
                merchant_user=instance.user,
                merchant=instance,
                notification_type=notification_type,
            )

        # Clean up stored state
        if instance.pk in _merchant_previous_state:
            del _merchant_previous_state[instance.pk]