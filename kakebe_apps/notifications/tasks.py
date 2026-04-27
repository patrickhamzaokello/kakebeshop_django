# kakebe_apps/notifications/tasks.py
from celery import shared_task
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from datetime import timedelta
import logging
import requests
from typing import List, Dict, Any

from .models import (
    BroadcastNotificationCampaign,
    Notification,
    NotificationDelivery,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from .email_service import EmailNotificationService
from .push_service import PushNotificationService
from kakebe_apps.engagement.models import PushToken

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

        if delivery.status != NotificationStatus.PENDING:
            return f"Delivery {delivery_id} already processed (status: {delivery.status})"

        notification = delivery.notification

        # Send email — returns None on success, error string on failure
        error = EmailNotificationService.send_notification_email(
            notification=notification,
            recipient_email=delivery.recipient,
        )

        if error is None:
            delivery.status = NotificationStatus.SENT
            delivery.sent_at = timezone.now()
            logger.info(f"Email sent successfully: {delivery_id}")
        else:
            delivery.status = NotificationStatus.FAILED
            delivery.error_message = error
            delivery.retry_count += 1

            if delivery.can_retry():
                delivery.next_retry_at = timezone.now() + timedelta(minutes=5)

            logger.error(f"Failed to send email {delivery_id}: {error}")

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

        if delivery.status != NotificationStatus.PENDING:
            return f"Delivery {delivery_id} already processed (status: {delivery.status})"

        notification = delivery.notification

        # Get device tokens, filtering out any blank entries
        device_tokens = [t for t in delivery.recipient.split(',') if t.strip()]

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
        count = 0
        with transaction.atomic():
            # Use skip_locked so concurrent workers don't schedule the same deliveries
            pending_deliveries = list(
                NotificationDelivery.objects.select_for_update(skip_locked=True).filter(
                    status=NotificationStatus.PENDING
                ).select_related('notification')[:100]
            )

            delivery_ids_to_schedule = []
            for delivery in pending_deliveries:
                if delivery.channel in (NotificationChannel.EMAIL, NotificationChannel.PUSH):
                    delivery_ids_to_schedule.append(delivery)
                    count += 1

        # Schedule outside the transaction so the lock is released first
        for delivery in delivery_ids_to_schedule:
            try:
                if delivery.channel == NotificationChannel.EMAIL:
                    send_email_notification.delay(str(delivery.id))
                elif delivery.channel == NotificationChannel.PUSH:
                    send_push_notification.delay(str(delivery.id))
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
        count = 0
        with transaction.atomic():
            failed_deliveries = list(
                NotificationDelivery.objects.select_for_update(skip_locked=True).filter(
                    status=NotificationStatus.FAILED,
                    retry_count__lt=models.F('max_retries'),
                    next_retry_at__lte=timezone.now()
                ).select_related('notification')[:50]
            )

            # Reset to PENDING inside the transaction so process_pending picks them up
            for delivery in failed_deliveries:
                delivery.status = NotificationStatus.PENDING
                delivery.save(update_fields=['status'])

        for delivery in failed_deliveries:
            try:
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


@shared_task(bind=True)
def send_broadcast_campaign(self, campaign_id: str):
    """Create and queue a scheduled admin broadcast for all eligible users."""
    try:
        campaign = BroadcastNotificationCampaign.objects.get(id=campaign_id)
    except BroadcastNotificationCampaign.DoesNotExist:
        logger.error(f"Broadcast campaign {campaign_id} not found")
        return f"Broadcast campaign {campaign_id} not found"

    if campaign.status in ('SENT', 'CANCELLED'):
        return f"Broadcast campaign {campaign_id} already {campaign.status}"

    try:
        campaign.status = 'SENDING'
        campaign.error_message = ''
        campaign.save(update_fields=['status', 'error_message', 'updated_at'])

        from django.contrib.auth import get_user_model

        User = get_user_model()
        queryset = User.objects.filter(is_active=True)

        if campaign.channel == NotificationChannel.EMAIL:
            queryset = queryset.exclude(email__isnull=True).exclude(email='')
        elif campaign.channel == NotificationChannel.PUSH:
            queryset = queryset.filter(push_tokens__is_active=True).distinct()
        else:
            raise ValueError(f"Unsupported campaign channel: {campaign.channel}")

        target_count = queryset.count()
        notification_count = 0
        metadata = {
            **(campaign.metadata or {}),
            'broadcast_campaign_id': str(campaign.id),
            'broadcast_channel': campaign.channel,
        }

        for user in queryset.iterator(chunk_size=500):
            notification = Notification.objects.filter(
                user=user,
                notification_type=NotificationType.ADMIN_BROADCAST,
                metadata__broadcast_campaign_id=str(campaign.id),
            ).first()

            if notification is None:
                notification = Notification.objects.create(
                    user=user,
                    notification_type=NotificationType.ADMIN_BROADCAST,
                    title=campaign.title,
                    message=campaign.message,
                    metadata=metadata,
                )

            if notification.deliveries.filter(channel=campaign.channel).exists():
                notification_count += 1
                continue

            if campaign.channel == NotificationChannel.EMAIL:
                recipient = user.email
            else:
                push_tokens = list(
                    PushToken.objects.filter(user=user, is_active=True)
                    .values_list('token', flat=True)
                )
                if not push_tokens:
                    continue
                recipient = ','.join(push_tokens)

            NotificationDelivery.objects.create(
                notification=notification,
                channel=campaign.channel,
                recipient=recipient,
                status=NotificationStatus.PENDING,
            )

            notification_count += 1

        campaign.status = 'SENT'
        campaign.target_count = target_count
        campaign.notification_count = notification_count
        campaign.sent_at = timezone.now()
        campaign.save(update_fields=[
            'status', 'target_count', 'notification_count', 'sent_at', 'updated_at'
        ])

        process_pending_notifications.delay()
        logger.info(
            f"Broadcast campaign {campaign_id} queued {notification_count} notifications"
        )
        return f"Broadcast campaign {campaign_id} queued {notification_count} notifications"

    except Exception as exc:
        campaign.status = 'FAILED'
        campaign.error_message = str(exc)
        campaign.save(update_fields=['status', 'error_message', 'updated_at'])
        logger.error(
            f"Error sending broadcast campaign {campaign_id}: {str(exc)}",
            exc_info=True,
        )
        raise self.retry(exc=exc, countdown=120, max_retries=3)
