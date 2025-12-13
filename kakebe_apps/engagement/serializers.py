# kakebe_apps/interactions/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    Favorite, SavedSearch, Conversation, Message, Notification,
    ListingReview, MerchantReview, Report, FollowUpRule, FollowUpLog,
    AdminUser, AuditLog, ApiUsage, ActivityLog, MerchantScore
)
from kakebe_apps.listings.models import Listing
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.orders.models import OrderIntent


class FavoriteSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    listing_image = serializers.URLField(source='listing.main_image', read_only=True)  # adjust field

    class Meta:
        model = Favorite
        fields = ['id', 'listing', 'listing_title', 'listing_image', 'created_at']
        read_only_fields = ['created_at']


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


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['type', 'title', 'body', 'data', 'action_url', 'created_at']


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
class MerchantScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantScore
        fields = '__all__'
        read_only_fields = '__all__'


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = '__all__'
        read_only_fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = '__all__'


class ApiUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiUsage
        fields = '__all__'
        read_only_fields = '__all__'