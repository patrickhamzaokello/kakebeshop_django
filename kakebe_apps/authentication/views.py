from django.core.cache import cache
from django.shortcuts import render
from rest_framework import generics, status, views, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from .email_templates import get_email_template
from .serializers import (
    RegisterSerializer, SetNewPasswordSerializer, ResetPasswordEmailRequestSerializer,
    EmailVerificationSerializer, LoginSerializer, LogoutSerializer, VerifyResetCodeSerializer,
    ResendVerificationCodeSerializer, ResendPhoneVerificationSerializer, UpdatePhoneNumberSerializer,
    VerifyPhoneNumberSerializer, AddPhoneNumberSerializer
)
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .twilio_utils import TwilioVerification
from .utils import Util
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .renderers import UserRenderer
from django.http import HttpResponsePermanentRedirect
import os
import random
import string
import logging

logger = logging.getLogger(__name__)


def generate_token_code():
    """Generate a 6-digit random code"""
    return ''.join(random.choices(string.digits, k=6))


class CustomRedirect(HttpResponsePermanentRedirect):
    allowed_schemes = [os.environ.get('APP_SCHEME'), 'http', 'https']


class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    renderer_classes = (UserRenderer,)

    @swagger_auto_schema(
        operation_description="Register a new user account",
        responses={
            201: "User registered successfully",
            400: "Validation error",
            500: "Internal server error"
        }
    )
    def post(self, request):
        try:
            # Validate and save user
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            # Generate verification code
            verification_code = generate_token_code()

            # Store in cache
            cache_key = f"email_verification_{user.pk}"
            cache.set(cache_key, {
                'code': verification_code,
                'user_id': str(user.pk),
                'attempts': 0,
                'email': user.email
            }, timeout=1800)  # 30 minutes

            # Get email template
            template_data = get_email_template(
                'email_verification',
                user_name=user.name,
                verification_code=verification_code
            )

            # Send email
            email_sent = Util.send_templated_email(user.email, template_data)

            if not email_sent:
                logger.error(f"Failed to send verification email to {user.email}")
                return Response({
                    'email': user.email,
                    'name': user.name,
                    'user_id': str(user.id),
                    'username': user.username,
                    'warning': 'Account created but verification email failed to send.',
                    'message': 'Please use the resend verification code option.',
                    'verification_required': True
                }, status=status.HTTP_201_CREATED)

            # Success response
            return Response({
                'email': user.email,
                'name': user.name,
                'user_id': str(user.id),
                'username': user.username,
                'message': 'Registration successful. Please check your email for verification code.',
                'verification_required': True,
                'code_expires_in': '30 minutes'
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            logger.warning(f"Registration validation error: {str(e.detail)}")
            return Response({
                'error': 'Registration failed',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Unexpected error in registration: {str(e)}", exc_info=True)
            return Response({
                'error': 'Registration failed due to an unexpected error',
                'message': 'Please try again later or contact support if the problem persists'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class VerifyEmailAPIView(views.APIView):
    serializer_class = EmailVerificationSerializer

    @swagger_auto_schema(
        operation_description="Verify email with 6-digit code",
        request_body=EmailVerificationSerializer,
        responses={200: "Email verified successfully", 400: "Invalid code"}
    )
    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data['email']
            code = serializer.validated_data['code']

            # Get user
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({
                    'error': 'Invalid email or verification code'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if already verified
            if user.is_verified:
                return Response({
                    'success': True,
                    'message': 'Email is already verified',
                    'user_id': str(user.id),
                    'email': user.email
                }, status=status.HTTP_200_OK)

            # Get cached verification data
            cache_key = f"email_verification_{user.pk}"
            cached_data = cache.get(cache_key)

            if not cached_data:
                return Response({
                    'error': 'Verification code has expired',
                    'message': 'Please request a new verification code'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check attempts
            if cached_data.get('attempts', 0) >= 5:
                cache.delete(cache_key)
                return Response({
                    'error': 'Too many failed attempts',
                    'message': 'Please request a new verification code'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify code
            if cached_data['code'] != code:
                cached_data['attempts'] = cached_data.get('attempts', 0) + 1
                cache.set(cache_key, cached_data, timeout=1800)

                return Response({
                    'error': 'Invalid verification code',
                    'attempts_remaining': 5 - cached_data['attempts']
                }, status=status.HTTP_400_BAD_REQUEST)

            # Code is valid - verify user
            user.is_verified = True
            user.save()

            # Clear cache
            cache.delete(cache_key)

            # Send welcome email
            try:
                welcome_template = get_email_template(
                    'welcome_verified',
                    user_name=user.name,
                    username=user.username
                )
                Util.send_templated_email(user.email, welcome_template)
            except Exception as e:
                logger.warning(f"Failed to send welcome email: {str(e)}")

            # Generate tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'success': True,
                'message': 'Email verified successfully',
                'user_id': str(user.id),
                'email': user.email,
                'username': user.username,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token)
                }
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({
                'error': 'Validation failed',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in email verification: {str(e)}", exc_info=True)
            return Response({
                'error': 'Email verification failed',
                'message': 'Please try again or request a new code'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResendVerificationCodeAPIView(views.APIView):
    serializer_class = ResendVerificationCodeSerializer

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data['email']

            # Get user
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({
                    'error': 'No account found with this email address'
                }, status=status.HTTP_404_NOT_FOUND)

            # Check if already verified
            if user.is_verified:
                return Response({
                    'message': 'Email is already verified',
                    'user_id': str(user.id)
                }, status=status.HTTP_200_OK)

            # Generate new code
            verification_code = generate_token_code()

            # Store in cache
            cache_key = f"email_verification_{user.pk}"
            cache.set(cache_key, {
                'code': verification_code,
                'user_id': str(user.pk),
                'attempts': 0,
                'email': user.email
            }, timeout=1800)

            # Get email template
            template_data = get_email_template(
                'resend_verification',
                user_name=user.name,
                verification_code=verification_code
            )

            # Send email
            email_sent = Util.send_templated_email(user.email, template_data)

            if not email_sent:
                logger.error(f"Failed to resend verification email to {user.email}")
                cache.delete(cache_key)
                return Response({
                    'error': 'Failed to send verification code',
                    'message': 'Please try again later'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                'success': True,
                'message': 'New verification code sent to your email',
                'code_expires_in': '30 minutes'
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({
                'error': 'Validation failed',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error resending verification code: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to resend verification code',
                'message': 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginAPIView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({
                'error': 'Login failed',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Unexpected error in login: {str(e)}", exc_info=True)
            return Response({
                'error': 'Login failed due to an unexpected error',
                'message': 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RequestPasswordResetEmail(generics.GenericAPIView):
    serializer_class = ResetPasswordEmailRequestSerializer

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data['email']

            # Check if user exists
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)

                # Generate reset code
                reset_code = generate_token_code()

                # Store in cache
                cache_key = f"password_reset_{user.pk}"
                cache.set(cache_key, {
                    'code': reset_code,
                    'user_id': str(user.pk),
                    'attempts': 0
                }, timeout=900)  # 15 minutes

                # Get email template
                template_data = get_email_template(
                    'password_reset',
                    user_name=user.name,
                    reset_code=reset_code
                )

                # Send email
                email_sent = Util.send_templated_email(user.email, template_data)

                if not email_sent:
                    logger.error(f"Failed to send password reset email to {user.email}")
                    cache.delete(cache_key)

            # Always return success (security best practice)
            return Response({
                'success': True,
                'message': 'If an account with this email exists, a password reset code has been sent.',
                'code_expires_in': '15 minutes'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in password reset request: {str(e)}", exc_info=True)
            return Response({
                'error': 'Password reset request failed',
                'message': 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class VerifyResetCodeAPIView(generics.GenericAPIView):
    serializer_class = VerifyResetCodeSerializer

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data['email']
            code = serializer.validated_data['code']

            # Get user
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({
                    'error': 'Invalid email or code'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get cached data
            cache_key = f"password_reset_{user.pk}"
            cached_data = cache.get(cache_key)

            if not cached_data:
                return Response({
                    'error': 'Reset code has expired',
                    'message': 'Please request a new password reset'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check attempts
            if cached_data.get('attempts', 0) >= 3:
                cache.delete(cache_key)
                return Response({
                    'error': 'Too many failed attempts',
                    'message': 'Please request a new reset code'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify code
            if cached_data['code'] != code:
                cached_data['attempts'] = cached_data.get('attempts', 0) + 1
                cache.set(cache_key, cached_data, timeout=900)

                return Response({
                    'error': 'Invalid reset code',
                    'attempts_remaining': 3 - cached_data['attempts']
                }, status=status.HTTP_400_BAD_REQUEST)

            # Code is valid - generate reset token
            reset_token = default_token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

            # Store validated session
            reset_session_key = f"reset_session_{user.pk}"
            cache.set(reset_session_key, {
                'token': reset_token,
                'uidb64': uidb64,
                'verified': True
            }, timeout=600)  # 10 minutes

            # Clear code cache
            cache.delete(cache_key)

            return Response({
                'success': True,
                'message': 'Code verified successfully',
                'reset_token': reset_token,
                'uidb64': uidb64,
                'expires_in': '10 minutes'
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({
                'error': 'Validation failed',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error verifying reset code: {str(e)}", exc_info=True)
            return Response({
                'error': 'Code verification failed',
                'message': 'Please try again'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SetNewPasswordAPIView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def patch(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Get user
            uidb64 = request.data.get('uidb64')
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)

            # Clear session
            reset_session_key = f"reset_session_{user.pk}"
            cache.delete(reset_session_key)

            # Send confirmation email
            try:
                confirmation_template = get_email_template(
                    'password_reset_success',
                    user_name=user.name
                )
                Util.send_templated_email(user.email, confirmation_template)
            except Exception as e:
                logger.warning(f"Failed to send password reset confirmation: {str(e)}")

            return Response({
                'success': True,
                'message': 'Password reset successful',
                'user_id': str(user.id),
                'email': user.email
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({
                'error': 'Password reset failed',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in password reset: {str(e)}", exc_info=True)
            return Response({
                'error': 'Password reset failed',
                'message': 'Please try again or request a new reset'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutAPIView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({
                "success": True,
                "message": "Successfully logged out"
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({
                'error': 'Logout failed',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in logout: {str(e)}", exc_info=True)
            return Response({
                "error": "Logout failed",
                "message": "Please try again"
            }, status=status.HTTP_400_BAD_REQUEST)


# Phone verification views remain largely the same but with consistent error handling
class AddPhoneNumberView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddPhoneNumberSerializer

    def post(self, request):
        try:
            serializer = self.serializer_class(
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)

            phone = serializer.validated_data['phone']
            user = request.user

            # Update phone
            user.phone = phone
            user.phone_verified = False
            user.save()

            # Send verification
            twilio = TwilioVerification()
            result = twilio.send_verification_code(phone)

            if result['success']:
                return Response({
                    'success': True,
                    'message': 'Phone number added. Verification code sent via SMS.',
                    'phone': phone,
                    'expires_in': '10 minutes'
                }, status=status.HTTP_200_OK)
            else:
                # Rollback
                user.phone = None
                user.save()

                return Response({
                    'error': 'Failed to send verification code',
                    'message': result.get('message', 'SMS service unavailable')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except ValidationError as e:
            return Response({
                'error': 'Validation failed',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error adding phone: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to add phone number',
                'message': 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyPhoneNumberView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VerifyPhoneNumberSerializer

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            code = serializer.validated_data['code']
            user = request.user

            if not user.phone:
                return Response({
                    'error': 'No phone number found',
                    'message': 'Please add a phone number first'
                }, status=status.HTTP_400_BAD_REQUEST)

            if user.phone_verified:
                return Response({
                    'success': True,
                    'message': 'Phone number is already verified',
                    'phone': user.phone
                }, status=status.HTTP_200_OK)

            # Verify with Twilio
            twilio = TwilioVerification()
            result = twilio.verify_code(user.phone, code)

            if result['success']:
                user.phone_verified = True
                user.save()

                return Response({
                    'success': True,
                    'message': 'Phone number verified successfully',
                    'phone': user.phone,
                    'verified': True
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Verification failed',
                    'message': result.get('message', 'Invalid code')
                }, status=status.HTTP_400_BAD_REQUEST)

        except ValidationError as e:
            return Response({
                'error': 'Validation failed',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error verifying phone: {str(e)}", exc_info=True)
            return Response({
                'error': 'Verification failed',
                'message': 'Please try again'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResendPhoneVerificationView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ResendPhoneVerificationSerializer

    def post(self, request):
        try:
            user = request.user

            if not user.phone:
                return Response({
                    'error': 'No phone number found',
                    'message': 'Please add a phone number first'
                }, status=status.HTTP_400_BAD_REQUEST)

            if user.phone_verified:
                return Response({
                    'message': 'Phone number is already verified',
                    'phone': user.phone
                }, status=status.HTTP_200_OK)

            twilio = TwilioVerification()
            result = twilio.send_verification_code(user.phone)

            if result['success']:
                return Response({
                    'success': True,
                    'message': 'Verification code resent successfully',
                    'phone': user.phone,
                    'expires_in': '10 minutes'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Failed to resend verification code',
                    'message': result.get('message', 'SMS service unavailable')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error resending phone verification: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to resend verification code',
                'message': 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdatePhoneNumberView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdatePhoneNumberSerializer

    def put(self, request):
        try:
            serializer = self.serializer_class(
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)

            phone = serializer.validated_data['phone']
            user = request.user

            user.phone = phone
            user.phone_verified = False
            user.save()

            twilio = TwilioVerification()
            result = twilio.send_verification_code(phone)

            if result['success']:
                return Response({
                    'success': True,
                    'message': 'Phone number updated. Verification code sent.',
                    'phone': phone,
                    'verified': False,
                    'expires_in': '10 minutes'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Failed to send verification code',
                    'message': result.get('message', 'SMS service unavailable')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except ValidationError as e:
            return Response({
                'error': 'Validation failed',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error updating phone: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to update phone number',
                'message': 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RemovePhoneNumberView(views.APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            user = request.user

            if not user.phone:
                return Response({
                    'message': 'No phone number to remove'
                }, status=status.HTTP_200_OK)

            user.phone = None
            user.phone_verified = False
            user.save()

            return Response({
                'success': True,
                'message': 'Phone number removed successfully'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error removing phone: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to remove phone number',
                'message': 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetPhoneStatusView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user

            return Response({
                'phone': user.phone,
                'phone_verified': user.phone_verified,
                'has_phone': bool(user.phone)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting phone status: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to get phone status',
                'message': 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)