"""
Celery tasks for authentication emails.

All tasks accept only primitive arguments (str) so they survive JSON
serialisation across the Celery message broker without issue.

Retry strategy: exponential back-off — 60 s, 120 s, 240 s — before the
task is marked failed.  The caller (view) is never blocked.
"""

from celery import shared_task
import logging

from .email_templates import get_email_template
from .utils import Util

logger = logging.getLogger(__name__)


def _retry_countdown(retries: int) -> int:
    """60 s → 120 s → 240 s exponential back-off."""
    return 60 * (2 ** retries)


@shared_task(bind=True, max_retries=3)
def send_verification_email_task(
    self,
    to_email: str,
    user_name: str,
    verification_code: str,
) -> str:
    """
    Send the initial email-verification code after registration.
    Dispatched immediately by RegisterView; does not block the response.
    """
    try:
        template_data = get_email_template(
            'email_verification',
            user_name=user_name,
            verification_code=verification_code,
        )
        success = Util.send_templated_email(to_email, template_data)
        if not success:
            raise RuntimeError(f"Plunk API returned failure for {to_email}")

        logger.info("Verification email sent to %s", to_email)
        return f"sent:{to_email}"

    except Exception as exc:
        logger.warning(
            "Verification email failed for %s (attempt %d/3): %s",
            to_email, self.request.retries + 1, exc,
        )
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_resend_verification_email_task(
    self,
    to_email: str,
    user_name: str,
    verification_code: str,
) -> str:
    """
    Send a fresh verification code when the user requests a resend.
    """
    try:
        template_data = get_email_template(
            'resend_verification',
            user_name=user_name,
            verification_code=verification_code,
        )
        success = Util.send_templated_email(to_email, template_data)
        if not success:
            raise RuntimeError(f"Plunk API returned failure for {to_email}")

        logger.info("Resend verification email sent to %s", to_email)
        return f"sent:{to_email}"

    except Exception as exc:
        logger.warning(
            "Resend verification email failed for %s (attempt %d/3): %s",
            to_email, self.request.retries + 1, exc,
        )
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_welcome_email_task(
    self,
    to_email: str,
    user_name: str,
    username: str,
) -> str:
    """
    Send the welcome email once a user's address is verified.
    """
    try:
        template_data = get_email_template(
            'welcome_verified',
            user_name=user_name,
            username=username,
        )
        success = Util.send_templated_email(to_email, template_data)
        if not success:
            raise RuntimeError(f"Plunk API returned failure for {to_email}")

        logger.info("Welcome email sent to %s", to_email)
        return f"sent:{to_email}"

    except Exception as exc:
        logger.warning(
            "Welcome email failed for %s (attempt %d/3): %s",
            to_email, self.request.retries + 1, exc,
        )
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_password_reset_email_task(
    self,
    to_email: str,
    user_name: str,
    reset_code: str,
) -> str:
    """
    Send the password-reset code email.
    """
    try:
        template_data = get_email_template(
            'password_reset',
            user_name=user_name,
            reset_code=reset_code,
        )
        success = Util.send_templated_email(to_email, template_data)
        if not success:
            raise RuntimeError(f"Plunk API returned failure for {to_email}")

        logger.info("Password reset email sent to %s", to_email)
        return f"sent:{to_email}"

    except Exception as exc:
        logger.warning(
            "Password reset email failed for %s (attempt %d/3): %s",
            to_email, self.request.retries + 1, exc,
        )
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_password_reset_success_email_task(
    self,
    to_email: str,
    user_name: str,
) -> str:
    """
    Send confirmation email once the password has been reset successfully.
    """
    try:
        template_data = get_email_template(
            'password_reset_success',
            user_name=user_name,
        )
        success = Util.send_templated_email(to_email, template_data)
        if not success:
            raise RuntimeError(f"Plunk API returned failure for {to_email}")

        logger.info("Password reset success email sent to %s", to_email)
        return f"sent:{to_email}"

    except Exception as exc:
        logger.warning(
            "Password reset success email failed for %s (attempt %d/3): %s",
            to_email, self.request.retries + 1, exc,
        )
        raise self.retry(exc=exc, countdown=_retry_countdown(self.request.retries))
