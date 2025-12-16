# kakebe_apps/listings/serializers.py

from rest_framework import serializers
from .models import Listing, ListingTag, ListingImage, ListingBusinessHour
from kakebe_apps.categories.serializers import CategorySerializer, TagSerializer  # Assuming serializers exist in categories app
from kakebe_apps.location.serializers import LocationSerializer  # Assuming serializer exists in location app
from kakebe_apps.merchants.serializers import MerchantDetailSerializer  # Assuming serializer exists in merchants app

class ListingTagSerializer(serializers.ModelSerializer):
    tag = TagSerializer(read_only=True)

    class Meta:
        model = ListingTag
        fields = ['id', 'tag', 'created_at']

class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ['id', 'image', 'thumbnail', 'is_primary', 'sort_order', 'created_at']

class ListingBusinessHourSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingBusinessHour
        fields = ['id', 'day', 'opens_at', 'closes_at', 'is_closed', 'created_at']

class ListingSerializer(serializers.ModelSerializer):
    merchant = MerchantDetailSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    images = ListingImageSerializer(many=True, read_only=True)
    business_hours = ListingBusinessHourSerializer(many=True, read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'merchant', 'title', 'description', 'listing_type', 'category', 'location',
            'tags', 'price_type', 'price', 'price_min', 'price_max', 'currency',
            'is_price_negotiable', 'status', 'rejection_reason', 'is_verified',
            'is_featured', 'featured_until', 'views_count', 'contact_count',
            'metadata', 'expires_at', 'created_at', 'updated_at', 'deleted_at',
            'images', 'business_hours'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'views_count', 'contact_count']

    def create(self, validated_data):
        # Handle creation with related fields if needed, but for now, basic create
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Handle update with related fields if needed
        return super().update(instance, validated_data)