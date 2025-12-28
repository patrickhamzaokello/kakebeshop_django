# kakebe_apps/notifications/services.py
from typing import List, Optional, Dict, Any
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    Notification,
    NotificationDelivery,
    NotificationType,
    NotificationChannel,
    NotificationStatus,
    UserNotificationPreference,
)
from .tasks import send_notification_task

User = get_user_model()


class NotificationService:
    """Service for creating and managing notifications"""

    @staticmethod
    def create_notification(
            user,
            notification_type: str,
            title: str,
            message: str,
            order_id: Optional[str] = None,
            merchant_id: Optional[str] = None,
            listing_id: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
            channels: Optional[List[str]] = None,
            send_immediately: bool = True,
    ) -> Notification:
        """
        Create a notification and schedule delivery

        Args:
            user: User instance
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            order_id: Related order ID
            merchant_id: Related merchant ID
            listing_id: Related listing ID
            metadata: Additional data
            channels: List of channels to send to (defaults to all enabled)
            send_immediately: Whether to send immediately or wait for batch

        Returns:
            Notification instance
        """
        # Create notification
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            order_id=order_id,
            merchant_id=merchant_id,
            listing_id=listing_id,
            metadata=metadata or {},
        )

        # Get user preferences
        preferences, _ = UserNotificationPreference.objects.get_or_create(
            user=user
        )

        # Determine channels to use
        if channels is None:
            channels = []
            if preferences.email_enabled:
                channels.append(NotificationChannel.EMAIL)
            if preferences.push_enabled and preferences.device_tokens:
                channels.append(NotificationChannel.PUSH)
            channels.append(NotificationChannel.IN_APP)  # Always create in-app

        # Create delivery records
        for channel in channels:
            if channel == NotificationChannel.EMAIL:
                recipient = user.email
            elif channel == NotificationChannel.PUSH:
                recipient = ','.join(preferences.device_tokens)
            else:
                recipient = str(user.id)

            NotificationDelivery.objects.create(
                notification=notification,
                channel=channel,
                recipient=recipient,
                status=NotificationStatus.PENDING,
            )

        # Send immediately if requested
        if send_immediately:
            send_notification_task.delay(str(notification.id))

        return notification

    @staticmethod
    def create_order_notification(
            user,
            order,
            notification_type: str,
            additional_data: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """Create order-related notification"""

        # Define notification content based on type
        notification_content = {
            NotificationType.ORDER_CREATED: {
                'title': 'Order Placed Successfully',
                'message': f'Your order {order.order_number} has been placed successfully. Total: UGX {order.total_amount:,.0f}',
            },
            NotificationType.ORDER_CONTACTED: {
                'title': 'Merchant Contacted',
                'message': f'The merchant has been contacted for your order {order.order_number}.',
            },
            NotificationType.ORDER_CONFIRMED: {
                'title': 'Order Confirmed',
                'message': f'Your order {order.order_number} has been confirmed by the merchant.',
            },
            NotificationType.ORDER_COMPLETED: {
                'title': 'Order Completed',
                'message': f'Your order {order.order_number} has been delivered. Thank you for shopping with us!',
            },
            NotificationType.ORDER_CANCELLED: {
                'title': 'Order Cancelled',
                'message': f'Your order {order.order_number} has been cancelled.',
            },
        }

        content = notification_content.get(notification_type, {
            'title': 'Order Update',
            'message': f'Your order {order.order_number} has been updated.',
        })

        metadata = {
            'order_number': order.order_number,
            'order_status': order.status,
            'total_amount': str(order.total_amount),
            'merchant_name': order.merchant.display_name if hasattr(order, 'merchant') else None,
        }

        if additional_data:
            metadata.update(additional_data)

        return NotificationService.create_notification(
            user=user,
            notification_type=notification_type,
            title=content['title'],
            message=content['message'],
            order_id=order.id,
            metadata=metadata,
        )

    @staticmethod
    def create_merchant_order_notification(
            merchant_user,
            order,
    ) -> Notification:
        """Create notification for merchant about new order"""

        metadata = {
            'order_number': order.order_number,
            'buyer_name': order.buyer.name if hasattr(order.buyer, 'name') else order.buyer.email,
            'total_amount': str(order.total_amount),
            'items_count': order.items.count(),
        }

        return NotificationService.create_notification(
            user=merchant_user,
            notification_type=NotificationType.MERCHANT_NEW_ORDER,
            title='New Order Received!',
            message=f'You have a new order {order.order_number} worth UGX {order.total_amount:,.0f}',
            order_id=order.id,
            metadata=metadata,
        )

    @staticmethod
    def create_merchant_status_notification(
            merchant_user,
            merchant,
            notification_type: str,
    ) -> Notification:
        """Create notification for merchant status changes"""

        notification_content = {
            NotificationType.MERCHANT_APPROVED: {
                'title': 'Merchant Account Approved! 🎉',
                'message': f'Congratulations! Your merchant account "{merchant.business_name}" has been approved. You can now start listing your products.',
            },
            NotificationType.MERCHANT_DEACTIVATED: {
                'title': 'Merchant Account Deactivated',
                'message': f'Your merchant account "{merchant.business_name}" has been deactivated. Please contact support for more information.',
            },
            NotificationType.MERCHANT_SUSPENDED: {
                'title': 'Merchant Account Suspended',
                'message': f'Your merchant account "{merchant.business_name}" has been temporarily suspended. Please contact support.',
            },
        }

        content = notification_content.get(notification_type, {
            'title': 'Merchant Account Update',
            'message': f'Your merchant account "{merchant.business_name}" has been updated.',
        })

        metadata = {
            'merchant_id': str(merchant.id),
            'business_name': merchant.business_name,
            'display_name': merchant.display_name,
            'status': merchant.status,
        }

        return NotificationService.create_notification(
            user=merchant_user,
            notification_type=notification_type,
            title=content['title'],
            message=content['message'],
            merchant_id=merchant.id,
            metadata=metadata,
        )

    @staticmethod
    def get_user_notifications(
            user,
            unread_only: bool = False,
            limit: Optional[int] = None,
    ) -> List[Notification]:
        """Get notifications for a user"""
        queryset = Notification.objects.filter(user=user)

        if unread_only:
            queryset = queryset.filter(is_read=False)

        if limit:
            queryset = queryset[:limit]

        return list(queryset)

    @staticmethod
    def mark_as_read(notification_id: str) -> bool:
        """Mark a notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id)
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False

    @staticmethod
    def mark_all_as_read(user) -> int:
        """Mark all notifications as read for a user"""
        return Notification.objects.filter(
            user=user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )

    @staticmethod
    def get_unread_count(user) -> int:
        """Get count of unread notifications for a user"""
        return Notification.objects.filter(
            user=user,
            is_read=False
        ).count()