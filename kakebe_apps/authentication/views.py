from django.core.cache import cache
from rest_framework import generics, status, views, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError


from .serializers import (
    RegisterSerializer, SetNewPasswordSerializer, ResetPasswordEmailRequestSerializer,
    EmailVerificationSerializer, LoginSerializer, LogoutSerializer, VerifyResetCodeSerializer,
    ResendVerificationCodeSerializer, ResendPhoneVerificationSerializer, UpdatePhoneNumberSerializer,
    VerifyPhoneNumberSerializer, AddPhoneNumberSerializer
)
from .tasks import (
    send_verification_email_task,
    send_resend_verification_email_task,
    send_welcome_email_task,
    send_password_reset_email_task,
    send_password_reset_success_email_task,
    send_phone_otp_task,
)
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from .models import User
from .twilio_utils import TwilioVerification
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.http import HttpResponsePermanentRedirect
import os
import random
import string
import logging

from ..engagement.serializers import UserProfileSerializer
from kakebe_apps.analytics import events as analytics

logger = logging.getLogger(__name__)


def generate_token_code():
    """Generate a 6-digit random code"""
    return ''.join(random.choices(string.digits, k=6))


class CustomRedirect(HttpResponsePermanentRedirect):
    allowed_schemes = [os.environ.get('APP_SCHEME'), 'http', 'https']


class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer

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

            # Dispatch email in the background — does not block registration
            send_verification_email_task.delay(
                user.email,
                user.name,
                verification_code,
            )

            analytics.user_registered(user)

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
            detail = e.detail
            if isinstance(detail, list):
                return Response(
                    {'error': str(detail[0]) if detail else 'Registration failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response({'errors': detail}, status=status.HTTP_400_BAD_REQUEST)

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

            analytics.email_verified(user)

            # Dispatch welcome email in the background
            send_welcome_email_task.delay(user.email, user.name, user.username)

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

            # Dispatch email in the background — does not block the response
            send_resend_verification_email_task.delay(
                user.email,
                user.name,
                verification_code,
            )

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
            analytics.user_logged_in(serializer.context['user'])
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValidationError as e:
            detail = e.detail
            if isinstance(detail, list):
                # Non-field error (e.g. invalid credentials, unverified email)
                return Response(
                    {'error': str(detail[0]) if detail else 'Login failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Field-level errors
            return Response({'errors': detail}, status=status.HTTP_400_BAD_REQUEST)

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

                # Dispatch email in the background
                send_password_reset_email_task.delay(user.email, user.name, reset_code)

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

            # Dispatch confirmation email in the background
            send_password_reset_success_email_task.delay(user.email, user.name)

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
            analytics.user_logged_out(request.user.id)
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

            user.phone = phone
            user.phone_verified = False
            user.save()

            analytics.phone_number_added(user.id, phone)
            send_phone_otp_task.delay(phone, str(user.id))

            return Response({
                'success': True,
                'message': f'Verification code sent to {phone}',
            }, status=status.HTTP_200_OK)

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

                analytics.phone_number_verified(user.id, user.phone)
                return Response({
                    'success': True,
                    'message': 'Phone number verified successfully',
                    'phone': user.phone,
                    'verified': True
                }, status=status.HTTP_200_OK)
            else:
                analytics.phone_verification_failed(user.id)
                return Response({
                    'error': 'Verification failed',
                    'details': {
                        'code': ['Invalid or expired verification code.']
                    }
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

            send_phone_otp_task.delay(user.phone, str(user.id))

            return Response({
                'success': True,
                'message': 'Verification code resent successfully',
                'phone': user.phone,
                'expires_in': '10 minutes'
            }, status=status.HTTP_200_OK)

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

            analytics.phone_number_updated(user.id, phone)
            send_phone_otp_task.delay(phone, str(user.id))

            return Response({
                'success': True,
                'message': 'Phone number updated. Verification code sent.',
                'phone': phone,
                'verified': False,
            }, status=status.HTTP_200_OK)

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

            analytics.phone_number_removed(user.id)
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

class UpdateProfileImageView(views.APIView):
    """
    Update authenticated user's profile image using a confirmed image_group_id.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Update authenticated user's profile image",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['image_group_id'],
            properties={
                'image_group_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='uuid',
                    description='Confirmed profile image group id'
                )
            }
        ),
        responses={
            200: "Profile image updated successfully",
            404: "No confirmed profile image found",
            400: "Validation error"
        }
    )
    def post(self, request):
        try:
            user = request.user
            image_group_id = request.data.get("image_group_id")

            if not image_group_id:
                return Response({
                    "error": "Validation failed",
                    "details": {
                        "image_group_id": ["This field is required."]
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            from kakebe_apps.imagehandler.models import ImageAsset

            assets = ImageAsset.objects.filter(
                image_group_id=image_group_id,
                owner=request.user,
                image_type='profile',
                is_confirmed=True
            )

            if not assets.exists():
                return Response(
                    {
                        "error": "No confirmed profile image found for this image_group_id."
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            assets.update(object_id=user.id)

            asset = assets.filter(variant='medium').first() or assets.first()
            user.profile_image = asset.cdn_url()
            user.save(update_fields=['profile_image', 'updated_at'])

            return Response({
                "success": True,
                "message": "Profile image updated successfully",
                "profile_image": user.profile_image
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating profile image: {str(e)}", exc_info=True)
            return Response({
                "error": "Failed to update profile image",
                "message": "Please try again later"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AnalyticsTokenRefreshView(TokenRefreshView):
    """
    Wraps SimpleJWT's TokenRefreshView to call PostHog identify on every
    successful refresh, keeping returning users tracked across sessions.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            try:
                raw_token = request.data.get('refresh', '')
                refresh = RefreshToken(raw_token)
                user_id = refresh.payload.get('user_id')
                if user_id:
                    user = User.objects.filter(pk=user_id).first()
                    analytics.session_resumed(user_id, user)
            except (TokenError, InvalidToken, Exception):
                pass  # Never block a refresh for analytics
        return response


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    View to retrieve and update authenticated user's profile
    GET: Retrieve user profile
    PUT/PATCH: Update user profile
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        """Return the authenticated user with related data"""
        return User.objects.select_related(
            'marketplace_intent',
            'onboarding_status',
            'merchant_profile'
        ).get(pk=self.request.user.pk)

    def get(self, request, *args, **kwargs):
        """Get user profile details"""
        try:
            user = self.get_object()
            serializer = self.get_serializer(user)

            return Response({
                'success': True,
                'user': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving user profile: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to retrieve profile',
                'message': 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Update user profile"""
        try:
            partial = kwargs.pop('partial', False)
            user = self.get_object()
            serializer = self.get_serializer(user, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response({
                'success': True,
                'message': 'Profile updated successfully',
                'user': serializer.data
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response({
                'error': 'Validation failed',
                'details': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}", exc_info=True)
            return Response({
                'error': 'Failed to update profile',
                'message': 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)