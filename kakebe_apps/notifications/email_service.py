# kakebe_apps/notifications/email_service.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

from .models import Notification, NotificationType

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Service for sending email notifications"""

    # Template mapping for different notification types
    TEMPLATE_MAP = {
        NotificationType.ORDER_CREATED: 'emails/order_created.html',
        NotificationType.ORDER_CONTACTED: 'emails/order_contacted.html',
        NotificationType.ORDER_CONFIRMED: 'emails/order_confirmed.html',
        NotificationType.ORDER_COMPLETED: 'emails/order_completed.html',
        NotificationType.ORDER_CANCELLED: 'emails/order_cancelled.html',
        NotificationType.MERCHANT_NEW_ORDER: 'emails/merchant_new_order.html',
        NotificationType.MERCHANT_APPROVED: 'emails/merchant_approved.html',
        NotificationType.MERCHANT_REACTIVATED: 'emails/merchant_approved.html',
        NotificationType.MERCHANT_SUSPENDED: 'emails/merchant_suspended.html',
        NotificationType.MERCHANT_BANNED: 'emails/merchant_suspended.html',
    }

    @classmethod
    def send_notification_email(
            cls,
            notification: Notification,
            recipient_email: str,
    ) -> str | None:
        """
        Send notification email.

        Returns:
            None on success, or an error string describing the failure.
        """
        try:
            template_name = cls.TEMPLATE_MAP.get(
                notification.notification_type,
                'emails/generic_notification.html'
            )

            context = {
                'notification': notification,
                'user': notification.user,
                'title': notification.title,
                'message': notification.message,
                'metadata': notification.metadata,
                'site_name': 'Kakebe',
                'site_url': settings.FRONTEND_URL,
                'current_year': notification.created_at.year,
            }

            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject=notification.title,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)

            logger.info(f"Email sent to {recipient_email} for notification {notification.id}")
            return None

        except Exception as e:
            error = str(e)
            logger.error(
                f"Error sending email to {recipient_email} for notification {notification.id}: {error}",
                exc_info=True,
            )
            return error

    @classmethod
    def send_test_email(cls, recipient_email: str) -> bool:
        """Send a test email"""
        try:
            context = {
                'title': 'Test Email',
                'message': 'This is a test email from Kakebe notifications system.',
                'site_name': 'Kakebe',
                'site_url': settings.FRONTEND_URL,
            }

            html_content = render_to_string('emails/generic_notification.html', context)
            text_content = strip_tags(html_content)

            email = EmailMultiAlternatives(
                subject='Test Email from Kakebe',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )

            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)

            logger.info(f"Test email sent to {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Error sending test email to {recipient_email}: {str(e)}", exc_info=True)
            return False