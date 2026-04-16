from kakebe_apps.authentication.models import User
from rest_framework.exceptions import AuthenticationFailed


def register_social_user(provider, user_id, email, name):
    """
    Register or retrieve a user for social authentication.
    Returns user data with tokens.
    """
    # Check if the email is already registered under a different provider
    email_user = User.objects.filter(email=email).first()
    if email_user and email_user.auth_provider != provider:
        raise AuthenticationFailed(
            f'This email is already registered with {email_user.auth_provider}. '
            f'Please login using {email_user.auth_provider}.'
        )

    if email_user:
        # Existing user with the same provider
        if not email_user.is_active:
            raise AuthenticationFailed('Your account has been disabled. Please contact support.')
        if not email_user.is_verified:
            raise AuthenticationFailed(
                'Your email is not verified. Please check your email for the verification code.'
            )
        return {
            'email': email_user.email,
            'name': email_user.name,
            'username': email_user.username,
            'user_id': str(email_user.id),
            'tokens': email_user.tokens()
        }

    # Create new user
    try:
        user = User.objects.create_user(
            name=name,
            email=email,
            password=None  # Social users don't need a password
        )
        user.auth_provider = provider
        user.is_verified = True  # Social auth verifies email
        user.save()

        return {
            'email': user.email,
            'name': user.name,
            'username': user.username,
            'user_id': str(user.id),
            'tokens': user.tokens()
        }
    except Exception as e:
        raise AuthenticationFailed('Failed to create account. Please try again.')