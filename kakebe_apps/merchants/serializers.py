# kakebe_apps/merchants/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Merchant

User = get_user_model()

class MerchantSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Merchant
        fields = [
            'id', 'user_id', 'username', 'email',
            'display_name', 'business_name', 'description',
            'business_phone', 'business_email', 'logo', 'cover_image',
            'verified', 'verification_date', 'rating', 'status',
            'created_at', 'deleted_at'
        ]
        read_only_fields = [
            'id', 'user_id', 'username', 'email',
            'verified', 'verification_date', 'rating',
            'created_at', 'deleted_at'
        ]

class MerchantUpdateSerializer(serializers.ModelSerializer):
    """
    Used for partial updates by the merchant owner.
    """
    class Meta:
        model = Merchant
        fields = [
            'display_name', 'business_name', 'description',
            'business_phone', 'business_email', 'logo', 'cover_image'
        ]

    def validate_business_email(self, value):
        if value and Merchant.objects.exclude(pk=self.instance.pk).filter(business_email=value).exists():
            raise serializers.ValidationError("This business email is already in use.")
        return value