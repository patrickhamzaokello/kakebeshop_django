# kakebe_apps/merchants/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Merchant

User = get_user_model()


class MerchantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing merchants"""

    class Meta:
        model = Merchant
        fields = [
            'id', 'display_name', 'business_name',
            'logo', 'rating', 'total_reviews', 'verified', 'featured'
        ]


class MerchantDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detailed merchant view"""
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Merchant
        fields = [
            'id', 'user_id', 'username', 'email',
            'display_name', 'business_name', 'description',
            'business_phone', 'business_email', 'logo', 'cover_image',
            'verified', 'verification_date', 'featured',
            'rating', 'total_reviews', 'status', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_id', 'username', 'email',
            'verified', 'verification_date', 'featured',
            'rating', 'total_reviews', 'status', 'is_active',
            'created_at', 'updated_at'
        ]


class MerchantUpdateSerializer(serializers.ModelSerializer):
    """Used for partial updates by the merchant owner"""

    class Meta:
        model = Merchant
        fields = [
            'display_name', 'business_name', 'description',
            'business_phone', 'business_email', 'logo', 'cover_image'
        ]

    def validate_business_email(self, value):
        if value:
            # Check if email is already used by another merchant
            qs = Merchant.objects.filter(business_email=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "This business email is already in use."
                )
        return value

    def validate_display_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Display name must be at least 3 characters long."
            )
        return value


class MerchantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new merchant profile"""

    class Meta:
        model = Merchant
        fields = [
            'display_name', 'business_name', 'description',
            'business_phone', 'business_email', 'logo', 'cover_image'
        ]

    def validate_business_email(self, value):
        if value and Merchant.objects.filter(business_email=value).exists():
            raise serializers.ValidationError(
                "This business email is already in use."
            )
        return value

    def validate(self, attrs):
        # Check if user already has a merchant profile
        user = self.context['request'].user
        if Merchant.objects.filter(user=user).exists():
            raise serializers.ValidationError(
                "You already have a merchant profile."
            )
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        # New merchants start as unverified
        return Merchant.objects.create(
            user=user,
            verified=False,
            **validated_data
        )