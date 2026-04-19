import logging

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from .serializers import (
    AppleSocialAuthSerializer,
    FacebookSocialAuthSerializer,
    GoogleSocialAuthSerializer,
    TwitterAuthSerializer,
)
from kakebe_apps.analytics import events as analytics

logger = logging.getLogger(__name__)


def _handle_social_auth_error(e):
    """Return a consistent error Response from a caught social-auth exception."""
    if isinstance(e, AuthenticationFailed):
        return Response(
            {'error': str(e.detail)},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if isinstance(e, ValidationError):
        detail = e.detail
        if isinstance(detail, list):
            return Response(
                {'error': str(detail[0]) if detail else 'Authentication failed'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'errors': detail}, status=status.HTTP_400_BAD_REQUEST)
    # Unexpected
    logger.error('Unexpected social auth error: %s', e, exc_info=True)
    return Response(
        {
            'error': 'Authentication failed due to an unexpected error',
            'message': 'Please try again later',
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class GoogleSocialAuthView(GenericAPIView):
    serializer_class = GoogleSocialAuthSerializer

    def post(self, request):
        """POST with "auth_token" — send a Google ID token to authenticate."""
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data['auth_token']
            is_new_user = data.pop('is_new_user', False)
            analytics.user_logged_in_social(
                data.get('user_id'), 'google',
                is_new_user=is_new_user,
                email=data.get('email'), name=data.get('name'), username=data.get('username'),
            )
            return Response(data, status=status.HTTP_200_OK)
        except (AuthenticationFailed, ValidationError) as e:
            return _handle_social_auth_error(e)
        except Exception as e:
            return _handle_social_auth_error(e)


class AppleSocialAuthView(GenericAPIView):
    serializer_class = AppleSocialAuthSerializer

    def post(self, request):
        """POST with "auth_token" — send an Apple identity token to authenticate."""
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data['auth_token']
            is_new_user = data.pop('is_new_user', False)
            analytics.user_logged_in_social(
                data.get('user_id'), 'apple',
                is_new_user=is_new_user,
                email=data.get('email'), name=data.get('name'), username=data.get('username'),
            )
            return Response(data, status=status.HTTP_200_OK)
        except (AuthenticationFailed, ValidationError) as e:
            return _handle_social_auth_error(e)
        except Exception as e:
            return _handle_social_auth_error(e)


class FacebookSocialAuthView(GenericAPIView):
    serializer_class = FacebookSocialAuthSerializer

    def post(self, request):
        """POST with "auth_token" — send a Facebook access token to authenticate."""
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data['auth_token']
            is_new_user = data.pop('is_new_user', False)
            analytics.user_logged_in_social(
                data.get('user_id'), 'facebook',
                is_new_user=is_new_user,
                email=data.get('email'), name=data.get('name'), username=data.get('username'),
            )
            return Response(data, status=status.HTTP_200_OK)
        except (AuthenticationFailed, ValidationError) as e:
            return _handle_social_auth_error(e)
        except Exception as e:
            return _handle_social_auth_error(e)


class TwitterSocialAuthView(GenericAPIView):
    serializer_class = TwitterAuthSerializer

    def post(self, request):
        """POST with "access_token_key" and "access_token_secret" to authenticate via Twitter."""
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            is_new_user = data.pop('is_new_user', False)
            analytics.user_logged_in_social(
                data.get('user_id'), 'twitter',
                is_new_user=is_new_user,
                email=data.get('email'), name=data.get('name'), username=data.get('username'),
            )
            return Response(data, status=status.HTTP_200_OK)
        except (AuthenticationFailed, ValidationError) as e:
            return _handle_social_auth_error(e)
        except Exception as e:
            return _handle_social_auth_error(e)