# kakebe_apps/notifications/push_service.py
import requests
from django.conf import settings
from typing import List, Dict, Any
import logging

from .models import Notification

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Service for sending push notifications via external API"""

    # External push notification API endpoint
    PUSH_API_URL = getattr(settings, 'PUSH_NOTIFICATION_API_URL', '')
    PUSH_API_KEY = getattr(settings, 'PUSH_NOTIFICATION_API_KEY', '')

    @classmethod
    def send_push_notification(
            cls,
            notification: Notification,
            device_tokens: List[str],
    ) -> Dict[str, Any]:
        """
        Send push notification to devices

        Args:
            notification: Notification instance
            device_tokens: List of device tokens

        Returns:
            Dictionary with success status and details
        """
        try:
            # Prepare payload for external API
            payload = {
                'tokens': device_tokens,
                'notification': {
                    'title': notification.title,
                    'body': notification.message,
                },
                'data': {
                    'notification_id': str(notification.id),
                    'notification_type': notification.notification_type,
                    'order_id': str(notification.order_id) if notification.order_id else None,
                    'merchant_id': str(notification.merchant_id) if notification.merchant_id else None,
                    **notification.metadata,
                },
                'priority': 'high',
                'ttl': 86400,  # 24 hours
            }

            # Send request to external API
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {cls.PUSH_API_KEY}',
            }

            response = requests.post(
                cls.PUSH_API_URL,
                json=payload,
                headers=headers,
                timeout=10,
            )

            response.raise_for_status()
            result = response.json()

            logger.info(
                f"Push notification sent successfully: {notification.id}, "
                f"Tokens: {len(device_tokens)}"
            )

            return {
                'success': True,
                'message_id': result.get('message_id'),
                'sent_count': result.get('sent_count', len(device_tokens)),
                'failed_count': result.get('failed_count', 0),
                'response': result,
            }

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error sending push notification {notification.id}: {str(e)}",
                exc_info=True
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
                exc_info=True
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
        Send multiple push notifications in bulk

        Args:
            notifications_data: List of notification data
                Each item should have: tokens, title, body, data

        Returns:
            Dictionary with success status and counts
        """
        try:
            # Prepare bulk payload
            payload = {
                'notifications': notifications_data,
                'priority': 'high',
            }

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {cls.PUSH_API_KEY}',
            }

            # Send bulk request
            response = requests.post(
                f"{cls.PUSH_API_URL}/bulk",
                json=payload,
                headers=headers,
                timeout=30,
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"Bulk push notifications sent: {len(notifications_data)}")

            return {
                'success': True,
                'total_sent': result.get('total_sent', 0),
                'total_failed': result.get('total_failed', 0),
                'response': result,
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