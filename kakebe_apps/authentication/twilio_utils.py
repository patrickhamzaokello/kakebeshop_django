from twilio.rest import Client
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TwilioVerification:
    """
    Utility class for Twilio phone verification using Verify API
    """

    def __init__(self):
        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        self.verify_service_sid = settings.TWILIO_VERIFY_SERVICE_SID

    def send_verification_code(self, phone_number):
        """
        Send verification code to phone number

        Args:
            phone_number: Phone number in E.164 format (e.g., +256700000000)

        Returns:
            dict: {'success': bool, 'message': str, 'status': str}
        """
        try:
            verification = self.client.verify \
                .v2 \
                .services(self.verify_service_sid) \
                .verifications \
                .create(to=phone_number, channel='sms')

            logger.info(f"Verification code sent to {phone_number}, status: {verification.status}")

            return {
                'success': True,
                'message': 'Verification code sent successfully',
                'status': verification.status
            }

        except Exception as e:
            logger.error(f"Failed to send verification code to {phone_number}: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to send verification code: {str(e)}',
                'status': 'failed'
            }

    def verify_code(self, phone_number, code):
        """
        Verify the code sent to phone number

        Args:
            phone_number: Phone number in E.164 format
            code: 6-digit verification code

        Returns:
            dict: {'success': bool, 'message': str, 'status': str}
        """
        try:
            verification_check = self.client.verify \
                .v2 \
                .services(self.verify_service_sid) \
                .verification_checks \
                .create(to=phone_number, code=code)

            if verification_check.status == 'approved':
                logger.info(f"Phone {phone_number} verified successfully")
                return {
                    'success': True,
                    'message': 'Phone number verified successfully',
                    'status': verification_check.status
                }
            else:
                logger.warning(f"Verification failed for {phone_number}, status: {verification_check.status}")
                return {
                    'success': False,
                    'message': 'Invalid or expired verification code',
                    'status': verification_check.status
                }

        except Exception as e:
            logger.error(f"Error verifying code for {phone_number}: {str(e)}")
            return {
                'success': False,
                'message': f'Verification failed: {str(e)}',
                'status': 'failed'
            }

    def cancel_verification(self, phone_number):
        """
        Cancel any pending verifications for a phone number

        Args:
            phone_number: Phone number in E.164 format
        """
        try:
            # This is optional - Twilio will auto-expire pending verifications
            pass
        except Exception as e:
            logger.error(f"Error canceling verification for {phone_number}: {str(e)}")
