from django.core.cache import cache
from rest_framework import serializers
from .models import User
from django.contrib import auth
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
import phonenumbers
from phonenumbers import NumberParseException


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        max_length=68,
        min_length=6,
        write_only=True,
        style={'input_type': 'password'}
    )
    user_id = serializers.UUIDField(source='id', read_only=True)
    username = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['email', 'name', 'password', 'user_id', 'username']
        read_only_fields = ['user_id', 'username']

    def validate_email(self, value):
        """Validate email format and uniqueness"""
        email = value.lower().strip()

        if not email:
            raise serializers.ValidationError("Email is required")

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "An account with this email already exists. Please login or use a different email."
            )

        return email

    def validate_name(self, value):
        """Validate name field"""
        name = value.strip()

        if not name:
            raise serializers.ValidationError("Name is required")

        if len(name) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long")

        if len(name) > 255:
            raise serializers.ValidationError("Name must not exceed 255 characters")

        return name

    def validate_password(self, value):
        """Validate password strength"""
        if len(value) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters long")

        if len(value) > 68:
            raise serializers.ValidationError("Password must not exceed 68 characters")

        # Optional: Add more password strength checks
        if value.isdigit():
            raise serializers.ValidationError("Password cannot be entirely numeric")

        if value.lower() in ['password', '123456', 'password123']:
            raise serializers.ValidationError("Password is too common. Please choose a stronger password")

        return value

    def create(self, validated_data):
        """Create user with validated data"""
        try:
            user = User.objects.create_user(
                name=validated_data['name'],
                email=validated_data['email'],
                password=validated_data['password']
            )
            return user
        except Exception as e:
            raise serializers.ValidationError(
                f"Failed to create user account. Please try again."
            )


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_email(self, value):
        """Validate and normalize email"""
        return value.lower().strip()

    def validate_code(self, value):
        """Validate verification code format"""
        if not value.isdigit():
            raise serializers.ValidationError("Code must contain only digits")

        if len(value) != 6:
            raise serializers.ValidationError("Code must be exactly 6 digits")

        return value


class ResendVerificationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate and normalize email"""
        email = value.lower().strip()

        # Check if user exists
        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "No account found with this email address"
            )

        return email


class LoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255, min_length=3)
    password = serializers.CharField(
        max_length=68,
        min_length=6,
        write_only=True,
        style={'input_type': 'password'}
    )
    username = serializers.CharField(read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    tokens = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['email', 'name', 'password', 'username', 'user_id', 'tokens']
        read_only_fields = ['name', 'username', 'user_id', 'tokens']

    def validate_email(self, value):
        """Validate and normalize email"""
        return value.lower().strip()

    def get_tokens(self, obj):
        """Generate tokens for authenticated user"""
        user = self.context.get('user')
        if not user:
            raise serializers.ValidationError("User not found in context")
        return user.tokens()

    def validate(self, attrs):
        """Validate login credentials"""
        email = attrs.get('email', '')
        password = attrs.get('password', '')

        if not email or not password:
            raise AuthenticationFailed('Email and password are required')

        # Check if user exists
        try:
            user_query = User.objects.filter(email=email)

            if not user_query.exists():
                raise AuthenticationFailed('Invalid credentials. Please check your email and password.')

            user_obj = user_query.first()

            # Check auth provider
            if user_obj.auth_provider != 'email':
                raise AuthenticationFailed(
                    f'This account uses {user_obj.auth_provider} authentication. '
                    f'Please login using {user_obj.auth_provider}.'
                )

            # Authenticate user
            user = auth.authenticate(email=email, password=password)

            if not user:
                raise AuthenticationFailed('Invalid credentials. Please check your email and password.')

            if not user.is_active:
                raise AuthenticationFailed('Your account has been disabled. Please contact support.')

            if not user.is_verified:
                raise AuthenticationFailed(
                    'Your email is not verified. Please check your email for the verification code.'
                )

            # Store user in context for token generation
            self.context['user'] = user

            return attrs

        except User.DoesNotExist:
            raise AuthenticationFailed('Invalid credentials. Please check your email and password.')

    def to_representation(self, instance):
        """Return user data with tokens"""
        user = self.context.get('user')
        if not user:
            raise serializers.ValidationError("User not found in context")

        return {
            'email': user.email,
            'name': user.name,
            'username': user.username,
            'user_id': str(user.id),
            'tokens': self.get_tokens(user)
        }


class ResetPasswordEmailRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(min_length=2)

    def validate_email(self, value):
        """Validate and normalize email"""
        return value.lower().strip()


class VerifyResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)

    def validate_email(self, value):
        """Validate and normalize email"""
        return value.lower().strip()

    def validate_code(self, value):
        """Validate reset code format"""
        if not value.isdigit():
            raise serializers.ValidationError("Code must contain only digits")

        if len(value) != 6:
            raise serializers.ValidationError("Code must be exactly 6 digits")

        return value


class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        min_length=6,
        max_length=68,
        write_only=True,
        style={'input_type': 'password'}
    )
    token = serializers.CharField(min_length=1, write_only=True)
    uidb64 = serializers.CharField(min_length=1, write_only=True)

    def validate_password(self, value):
        """Validate new password strength"""
        if len(value) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters long")

        if value.isdigit():
            raise serializers.ValidationError("Password cannot be entirely numeric")

        if value.lower() in ['password', '123456', 'password123']:
            raise serializers.ValidationError("Password is too common. Please choose a stronger password")

        return value

    def validate(self, attrs):
        """Validate token and update password"""
        try:
            password = attrs.get('password')
            token = attrs.get('token')
            uidb64 = attrs.get('uidb64')

            # Decode user ID
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)

            # Verify token
            if not default_token_generator.check_token(user, token):
                raise AuthenticationFailed(
                    'The reset token is invalid or has expired. Please request a new password reset.',
                    401
                )

            # Check reset session
            reset_session_key = f"reset_session_{user.pk}"
            session_data = cache.get(reset_session_key)

            if not session_data or not session_data.get('verified'):
                raise AuthenticationFailed(
                    'Reset session has expired. Please verify your code again.',
                    401
                )

            # Update password
            user.set_password(password)
            user.save()

            # Clear cache
            cache.delete(reset_session_key)

            return attrs

        except (TypeError, ValueError, OverflowError):
            raise AuthenticationFailed('The reset link is invalid. Please request a new password reset.', 401)
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found. Please request a new password reset.', 401)
        except Exception as e:
            raise AuthenticationFailed('Password reset failed. Please try again.', 401)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        """Validate and blacklist refresh token"""
        self.token = attrs.get('refresh')
        return attrs

    def save(self, **kwargs):
        """Blacklist the refresh token"""
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except TokenError:
            raise serializers.ValidationError("Token is invalid or has already been blacklisted")


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile information"""
    user_id = serializers.UUIDField(source='id', read_only=True)

    class Meta:
        model = User
        fields = [
            'user_id', 'username', 'name', 'email',
            'phone', 'bio', 'profile_image', 'phone_verified',
            'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user_id', 'username', 'email', 'is_verified',
            'phone_verified', 'created_at', 'updated_at'
        ]


class AddPhoneNumberSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, required=True)

    def validate_phone(self, value):
        """Validate and format phone number"""
        try:
            # Remove whitespace
            phone = value.strip()

            # Parse the phone number
            parsed_number = phonenumbers.parse(phone, None)

            # Validate the number
            if not phonenumbers.is_valid_number(parsed_number):
                raise serializers.ValidationError(
                    "Invalid phone number. Please check the number and try again."
                )

            # Format to E.164
            e164_number = phonenumbers.format_number(
                parsed_number,
                phonenumbers.PhoneNumberFormat.E164
            )

            return e164_number

        except NumberParseException:
            raise serializers.ValidationError(
                "Invalid phone number format. Please include the country code (e.g., +256700000000)"
            )

    def validate(self, attrs):
        """Check phone number availability"""
        phone = attrs.get('phone')
        request = self.context.get('request')

        if request and request.user:
            # Check if another verified user has this phone
            existing_user = User.objects.filter(
                phone=phone,
                phone_verified=True
            ).exclude(id=request.user.id).first()

            if existing_user:
                raise serializers.ValidationError({
                    'phone': 'This phone number is already registered to another account'
                })

        return attrs


class VerifyPhoneNumberSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6, required=True)

    def validate_code(self, value):
        """Validate verification code format"""
        if not value.isdigit():
            raise serializers.ValidationError("Code must contain only digits")

        if len(value) != 6:
            raise serializers.ValidationError("Code must be exactly 6 digits")

        return value


class UpdatePhoneNumberSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, required=True)

    def validate_phone(self, value):
        """Validate and format phone number"""
        try:
            phone = value.strip()
            parsed_number = phonenumbers.parse(phone, None)

            if not phonenumbers.is_valid_number(parsed_number):
                raise serializers.ValidationError(
                    "Invalid phone number. Please check the number and try again."
                )

            e164_number = phonenumbers.format_number(
                parsed_number,
                phonenumbers.PhoneNumberFormat.E164
            )

            return e164_number

        except NumberParseException:
            raise serializers.ValidationError(
                "Invalid phone number format. Please include the country code"
            )

    def validate(self, attrs):
        """Check phone number availability"""
        phone = attrs.get('phone')
        request = self.context.get('request')

        if request and request.user:
            existing_user = User.objects.filter(
                phone=phone,
                phone_verified=True
            ).exclude(id=request.user.id).first()

            if existing_user:
                raise serializers.ValidationError({
                    'phone': 'This phone number is already in use by another account'
                })

        return attrs


class ResendPhoneVerificationSerializer(serializers.Serializer):
    """Serializer for resending phone verification code"""
    pass