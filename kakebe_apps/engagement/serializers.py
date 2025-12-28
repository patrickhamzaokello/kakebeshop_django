# kakebe_apps/interactions/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
     SavedSearch, Conversation, Message,
    ListingReview, MerchantReview, Report, FollowUpRule, FollowUpLog,
    AdminUser, AuditLog, ApiUsage, ActivityLog, MerchantScore, PushToken
)
from kakebe_apps.listings.models import Listing
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.orders.models import OrderIntent

from .models import UserIntent, OnboardingStatus
from ..authentication.models import User
from ..merchants.serializers import MerchantDetailSerializer



class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = '__all__'
        read_only_fields = ['user', 'last_notified_at', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'sender_name', 'message', 'attachment', 'is_read', 'sent_at']
        read_only_fields = ['sender', 'is_read', 'sent_at']

    def validate(self, attrs):
        conversation = self.context['view'].get_object() if self.instance else self.context.get('conversation')
        if attrs['sender'] != self.context['request'].user:
            raise serializers.ValidationError("You can only send messages as yourself.")
        return attrs


class ConversationSerializer(serializers.ModelSerializer):
    buyer_name = serializers.CharField(source='buyer.get_full_name', read_only=True)
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    last_message = MessageSerializer(source='messages.last', read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'listing', 'listing_title', 'order_intent', 'buyer', 'buyer_name',
            'seller', 'seller_name', 'status', 'last_message_at', 'created_at',
            'last_message', 'unread_count'
        ]
        read_only_fields = ['buyer', 'seller', 'status', 'last_message_at', 'created_at']

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()



class ListingReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = ListingReview
        fields = ['id', 'listing', 'rating', 'comment', 'user_name', 'created_at', 'updated_at']
        read_only_fields = ['user_name', 'created_at', 'updated_at']

    def validate(self, attrs):
        user = self.context['request'].user
        listing = attrs['listing']

        # One review per user per listing
        if ListingReview.objects.filter(user=user, listing=listing).exists():
            raise serializers.ValidationError("You have already reviewed this listing.")

        # Optional: only if completed order
        if not OrderIntent.objects.filter(buyer=user, items__listing=listing, status='COMPLETED').exists():
            raise serializers.ValidationError("You can only review listings from completed orders.")

        return attrs


class MerchantReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = MerchantReview
        fields = ['id', 'merchant', 'rating', 'comment', 'user_name', 'created_at', 'updated_at']
        read_only_fields = ['user_name', 'created_at', 'updated_at']

    def validate(self, attrs):
        user = self.context['request'].user
        merchant = attrs['merchant']

        if MerchantReview.objects.filter(user=user, merchant=merchant).exists():
            raise serializers.ValidationError("You have already reviewed this merchant.")

        return attrs


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'
        read_only_fields = ['status', 'reviewed_by', 'review_notes', 'created_at', 'updated_at']


# Read-only serializers for logs/scores
# FIXED: Cannot use '__all__' with read_only_fields
# For read-only serializers, simply don't include read_only_fields
# OR override create/update methods to make them read-only

class MerchantScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantScore
        fields = '__all__'

    def create(self, validated_data):
        raise serializers.ValidationError("This is a read-only endpoint")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("This is a read-only endpoint")


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = '__all__'

    def create(self, validated_data):
        raise serializers.ValidationError("This is a read-only endpoint")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("This is a read-only endpoint")


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'

    def create(self, validated_data):
        raise serializers.ValidationError("This is a read-only endpoint")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("This is a read-only endpoint")


class ApiUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiUsage
        fields = '__all__'

    def create(self, validated_data):
        raise serializers.ValidationError("This is a read-only endpoint")

    def update(self, instance, validated_data):
        raise serializers.ValidationError("This is a read-only endpoint")


class UserIntentSerializer(serializers.ModelSerializer):
    """Serializer for UserIntent model"""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    intent_display = serializers.CharField(source='get_intent_display', read_only=True)

    class Meta:
        model = UserIntent
        fields = [
            'id',
            'user_email',
            'user_name',
            'intent',
            'intent_display',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user_email', 'user_name', 'created_at', 'updated_at']

    def validate_intent(self, value):
        """Validate intent value"""
        valid_intents = ['buy', 'sell', 'both']
        if value not in valid_intents:
            raise serializers.ValidationError(
                f"Invalid intent. Must be one of: {', '.join(valid_intents)}"
            )
        return value

    def create(self, validated_data):
        """Create or update user intent"""
        user = self.context['request'].user
        intent_obj, created = UserIntent.objects.update_or_create(
            user=user,
            defaults={'intent': validated_data['intent']}
        )

        # Update onboarding status
        onboarding, _ = OnboardingStatus.objects.get_or_create(user=user)
        onboarding.intent_completed = True
        onboarding.check_completion()

        return intent_obj


class OnboardingStatusSerializer(serializers.ModelSerializer):
    """Serializer for OnboardingStatus model"""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingStatus
        fields = [
            'id',
            'user_email',
            'user_name',
            'intent_completed',
            'categories_completed',
            'profile_completed',
            'is_onboarding_complete',
            'progress_percentage',
            'completed_at',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'user_email',
            'user_name',
            'is_onboarding_complete',
            'completed_at',
            'created_at',
            'updated_at'
        ]

    def get_progress_percentage(self, obj):
        """Calculate onboarding progress percentage"""
        completed_steps = sum([
            obj.intent_completed,
            obj.categories_completed,
            obj.profile_completed,
        ])
        total_steps = 3
        return round((completed_steps / total_steps) * 100, 2)


class UserProfileSerializer(serializers.ModelSerializer):
    """Extended user serializer with intent and onboarding status"""

    intent = UserIntentSerializer(source='marketplace_intent', read_only=True)
    onboarding = OnboardingStatusSerializer(source='onboarding_status', read_only=True)
    merchant = serializers.SerializerMethodField()
    is_merchant = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'name',
            'email',
            'profile_image',
            'phone',
            'bio',
            'is_verified',
            'phone_verified',
            'intent',
            'onboarding',
            'merchant',
            'is_merchant',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'email', 'username', 'created_at', 'updated_at']

    def get_merchant(self, obj):
        """
        Return merchant details if user has a merchant profile
        """
        try:
            if hasattr(obj, 'merchant_profile'):
                return MerchantDetailSerializer(obj.merchant_profile).data
            return None
        except Exception:
            return None

    def get_is_merchant(self, obj):
        """
        Check if user has a merchant profile
        """
        return hasattr(obj, 'merchant_profile')


class PushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushToken
        fields = ['id', 'token', 'device_id', 'platform', 'is_active', 'last_used', 'created_at']
        read_only_fields = ['id', 'last_used', 'created_at']

    def validate_token(self, value):
        """Validate push token format"""
        if not value.strip():
            raise serializers.ValidationError("Token cannot be empty.")

        # Validate Expo push token format
        if value.startswith('ExponentPushToken['):
            if not value.endswith(']') or len(value) < 20:
                raise serializers.ValidationError("Invalid Expo push token format.")

        return value


class PushTokenCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushToken
        fields = ['token', 'device_id', 'platform']

    def validate_token(self, value):
        """Validate push token format"""
        if not value.strip():
            raise serializers.ValidationError("Token cannot be empty.")

        # Validate Expo push token format
        if value.startswith('ExponentPushToken['):
            if not value.endswith(']') or len(value) < 20:
                raise serializers.ValidationError("Invalid Expo push token format.")

        return value

class PushTokenUpdateUsageSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=200)

    def validate_token(self, value):
        if not value.strip():
            raise serializers.ValidationError("Token cannot be empty.")
        return value