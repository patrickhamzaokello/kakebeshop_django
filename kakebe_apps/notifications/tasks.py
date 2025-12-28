# kakebe_apps/notifications/tasks.py
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
import requests
from typing import List, Dict, Any

from .models import (
    Notification,
    NotificationDelivery,
    NotificationChannel,
    NotificationStatus,
)
from .email_service import EmailNotificationService
from .push_service import PushNotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_notification_task(self, notification_id: str):
    """
    Send a single notification through all pending channels

    Args:
        notification_id: UUID of the notification
    """
    try:
        notification = Notification.objects.get(id=notification_id)

        # Get all pending deliveries
        pending_deliveries = notification.deliveries.filter(
            status=NotificationStatus.PENDING
        )

        for delivery in pending_deliveries:
            try:
                if delivery.channel == NotificationChannel.EMAIL:
                    send_email_notification.delay(str(delivery.id))
                elif delivery.channel == NotificationChannel.PUSH:
                    send_push_notification.delay(str(delivery.id))
                elif delivery.channel == NotificationChannel.IN_APP:
                    # In-app notifications are already created, just mark as sent
                    delivery.status = NotificationStatus.SENT
                    delivery.sent_at = timezone.now()
                    delivery.save()
            except Exception as e:
                logger.error(
                    f"Error scheduling delivery {delivery.id}: {str(e)}",
                    exc_info=True
                )

        return f"Notification {notification_id} processing initiated"

    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
        return f"Notification {notification_id} not found"

    except Exception as exc:
        logger.error(
            f"Error sending notification {notification_id}: {str(exc)}",
            exc_info=True
        )
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_email_notification(self, delivery_id: str):
    """
    Send email notification

    Args:
        delivery_id: UUID of the delivery record
    """
    try:
        delivery = NotificationDelivery.objects.get(id=delivery_id)
        notification = delivery.notification

        # Send email
        success = EmailNotificationService.send_notification_email(
            notification=notification,
            recipient_email=delivery.recipient,
        )

        if success:
            delivery.status = NotificationStatus.SENT
            delivery.sent_at = timezone.now()
            logger.info(f"Email sent successfully: {delivery_id}")
        else:
            delivery.status = NotificationStatus.FAILED
            delivery.error_message = "Failed to send email"
            delivery.retry_count += 1

            if delivery.can_retry():
                delivery.next_retry_at = timezone.now() + timedelta(minutes=5)

            logger.error(f"Failed to send email: {delivery_id}")

        delivery.save()
        return f"Email delivery {delivery_id} processed"

    except NotificationDelivery.DoesNotExist:
        logger.error(f"Delivery {delivery_id} not found")
        return f"Delivery {delivery_id} not found"

    except Exception as exc:
        logger.error(
            f"Error sending email {delivery_id}: {str(exc)}",
            exc_info=True
        )
        raise self.retry(exc=exc, countdown=120)


@shared_task(bind=True, max_retries=3)
def send_push_notification(self, delivery_id: str):
    """
    Send push notification

    Args:
        delivery_id: UUID of the delivery record
    """
    try:
        delivery = NotificationDelivery.objects.get(id=delivery_id)
        notification = delivery.notification

        # Get device tokens
        device_tokens = delivery.recipient.split(',')

        # Send push notification
        result = PushNotificationService.send_push_notification(
            notification=notification,
            device_tokens=device_tokens,
        )

        if result.get('success'):
            delivery.status = NotificationStatus.SENT
            delivery.sent_at = timezone.now()
            delivery.external_id = result.get('message_id')
            delivery.response_data = result
            logger.info(f"Push notification sent successfully: {delivery_id}")
        else:
            delivery.status = NotificationStatus.FAILED
            delivery.error_message = result.get('error', 'Unknown error')
            delivery.retry_count += 1
            delivery.response_data = result

            if delivery.can_retry():
                delivery.next_retry_at = timezone.now() + timedelta(minutes=5)

            logger.error(f"Failed to send push notification: {delivery_id}")

        delivery.save()
        return f"Push delivery {delivery_id} processed"

    except NotificationDelivery.DoesNotExist:
        logger.error(f"Delivery {delivery_id} not found")
        return f"Delivery {delivery_id} not found"

    except Exception as exc:
        logger.error(
            f"Error sending push notification {delivery_id}: {str(exc)}",
            exc_info=True
        )
        raise self.retry(exc=exc, countdown=120)


@shared_task
def process_pending_notifications():
    """
    Process all pending notifications (runs every minute)
    This ensures near real-time delivery
    """
    try:
        # Get all pending deliveries
        pending_deliveries = NotificationDelivery.objects.filter(
            status=NotificationStatus.PENDING
        ).select_related('notification')[:100]  # Process in batches

        count = 0
        for delivery in pending_deliveries:
            try:
                if delivery.channel == NotificationChannel.EMAIL:
                    send_email_notification.delay(str(delivery.id))
                elif delivery.channel == NotificationChannel.PUSH:
                    send_push_notification.delay(str(delivery.id))
                count += 1
            except Exception as e:
                logger.error(
                    f"Error processing delivery {delivery.id}: {str(e)}",
                    exc_info=True
                )

        logger.info(f"Scheduled {count} pending notifications for delivery")
        return f"Processed {count} pending notifications"

    except Exception as e:
        logger.error(f"Error in process_pending_notifications: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


@shared_task
def retry_failed_notifications():
    """
    Retry failed notifications that are eligible for retry
    Runs every 5 minutes
    """
    try:
        # Get failed deliveries that can be retried
        failed_deliveries = NotificationDelivery.objects.filter(
            status=NotificationStatus.FAILED,
            retry_count__lt=models.F('max_retries'),
            next_retry_at__lte=timezone.now()
        ).select_related('notification')[:50]

        count = 0
        for delivery in failed_deliveries:
            try:
                # Reset status to pending
                delivery.status = NotificationStatus.PENDING
                delivery.save()

                # Schedule for delivery
                if delivery.channel == NotificationChannel.EMAIL:
                    send_email_notification.delay(str(delivery.id))
                elif delivery.channel == NotificationChannel.PUSH:
                    send_push_notification.delay(str(delivery.id))

                count += 1
            except Exception as e:
                logger.error(
                    f"Error retrying delivery {delivery.id}: {str(e)}",
                    exc_info=True
                )

        logger.info(f"Retried {count} failed notifications")
        return f"Retried {count} failed notifications"

    except Exception as e:
        logger.error(f"Error in retry_failed_notifications: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


@shared_task
def cleanup_old_notifications():
    """
    Clean up old read notifications (runs daily)
    Keep notifications for 30 days
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=30)

        deleted_count = Notification.objects.filter(
            is_read=True,
            read_at__lt=cutoff_date
        ).delete()[0]

        logger.info(f"Deleted {deleted_count} old notifications")
        return f"Deleted {deleted_count} old notifications"

    except Exception as e:
        logger.error(f"Error in cleanup_old_notifications: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


@shared_task
def send_bulk_notifications(notifications_data: List[Dict[str, Any]]):
    """
    Send notifications in bulk for efficiency

    Args:
        notifications_data: List of notification data dictionaries
    """
    try:
        count = 0
        for notif_data in notifications_data:
            try:
                send_notification_task.delay(notif_data['notification_id'])
                count += 1
            except Exception as e:
                logger.error(
                    f"Error scheduling notification {notif_data.get('notification_id')}: {str(e)}",
                    exc_info=True
                )

        logger.info(f"Scheduled {count} bulk notifications")
        return f"Scheduled {count} bulk notifications"

    except Exception as e:
        logger.error(f"Error in send_bulk_notifications: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"