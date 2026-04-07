# kakebe_apps/notifications/push_service.py
import requests
from django.conf import settings
from typing import List, Dict, Any
import logging

from .models import Notification

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


class PushNotificationService:
    """Service for sending push notifications via external API"""

    PUSH_API_URL = getattr(
        settings,
        'PUSH_NOTIFICATION_API_URL',
        'http://notification-service:4000/api/push-notification',
    )
    PUSH_API_KEY = getattr(settings, 'PUSH_NOTIFICATION_API_KEY', '')

    @classmethod
    def _build_messages(cls, notification: Notification, device_tokens: List[str]) -> List[Dict]:
        """Build per-token message list expected by the push service."""
        metadata = {
            'notificationId': str(notification.id),
            'notificationType': notification.notification_type,
            'orderId': str(notification.order_id) if notification.order_id else None,
            'merchantId': str(notification.merchant_id) if notification.merchant_id else None,
            **notification.metadata,
        }
        return [
            {
                'token': token,
                'title': notification.title,
                'body': notification.message,
                'metadata': metadata,
            }
            for token in device_tokens
        ]

    @classmethod
    def _send_batch(cls, messages: List[Dict]) -> bool:
        """POST a single batch of messages to the push service. Returns True on success."""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {cls.PUSH_API_KEY}',
        }
        response = requests.post(
            cls.PUSH_API_URL,
            json={'messages': messages},
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return True

    @classmethod
    def send_push_notification(
            cls,
            notification: Notification,
            device_tokens: List[str],
    ) -> Dict[str, Any]:
        """
        Send push notification to one or more devices.

        Builds per-token messages and posts them in batches to the push service
        endpoint as ``{"messages": [...]}``.
        """
        if not device_tokens:
            return {'success': False, 'error': 'No device tokens provided', 'sent_count': 0, 'failed_count': 0}

        messages = cls._build_messages(notification, device_tokens)

        try:
            success_count = 0
            for i in range(0, len(messages), BATCH_SIZE):
                cls._send_batch(messages[i:i + BATCH_SIZE])
                success_count += len(messages[i:i + BATCH_SIZE])

            logger.info(
                f"Push notification sent: {notification.id}, tokens: {success_count}"
            )
            return {
                'success': True,
                'sent_count': success_count,
                'failed_count': 0,
            }

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error sending push notification {notification.id}: {str(e)}",
                exc_info=True,
            )
            return {
                'success': False,
                'error': str(e),
                'sent_count': 0,
                'failed_count': len(device_tokens),
            }

        except Exception as e:
            logger.error(
                f"Unexpected error sending push notification {notification.id}: {str(e)}",
                exc_info=True,
            )
            return {
                'success': False,
                'error': str(e),
                'sent_count': 0,
                'failed_count': len(device_tokens),
            }

    @classmethod
    def send_bulk_push_notifications(
            cls,
            notifications_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Send pre-built message dicts in bulk.

        Each item in ``notifications_data`` must already be a message dict with
        ``token``, ``title``, ``body``, and ``metadata`` keys.
        """
        try:
            success_count = 0
            for i in range(0, len(notifications_data), BATCH_SIZE):
                cls._send_batch(notifications_data[i:i + BATCH_SIZE])
                success_count += len(notifications_data[i:i + BATCH_SIZE])

            logger.info(f"Bulk push notifications sent: {success_count}")
            return {
                'success': True,
                'total_sent': success_count,
                'total_failed': 0,
            }

        except Exception as e:
            logger.error(f"Error sending bulk push notifications: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'total_sent': 0,
                'total_failed': len(notifications_data),
            }

    @classmethod
    def validate_device_token(cls, device_token: str) -> bool:
        """
        Validate a device token with the push service

        Args:
            device_token: Device token to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {cls.PUSH_API_KEY}',
            }

            response = requests.post(
                f"{cls.PUSH_API_URL}/validate",
                json={'token': device_token},
                headers=headers,
                timeout=5,
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error validating device token: {str(e)}")
            return False