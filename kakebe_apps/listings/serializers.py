# kakebe_apps/listings/serializers.py

from rest_framework import serializers
from django.utils import timezone
from .models import Listing, ListingTag, ListingBusinessHour
from kakebe_apps.categories.serializers import CategoryListSerializer as CategorySerializer, TagSerializer
from kakebe_apps.merchants.serializers import MerchantListSerializer



class ListingBusinessHourSerializer(serializers.ModelSerializer):
    day_display = serializers.CharField(source='get_day_display', read_only=True)

    class Meta:
        model = ListingBusinessHour
        fields = [
            'id', 'day', 'day_display', 'opens_at',
            'closes_at', 'is_closed', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        if not attrs.get('is_closed'):
            if not attrs.get('opens_at') or not attrs.get('closes_at'):
                raise serializers.ValidationError(
                    "Opening and closing times are required when not closed."
                )
            if attrs['opens_at'] >= attrs['closes_at']:
                raise serializers.ValidationError(
                    "Opening time must be before closing time."
                )
        return attrs


class ListingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing in lists"""
    merchant = MerchantListSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id', 'merchant', 'title', 'listing_type',
            'category_name', 'price_type',
            'price', 'price_min', 'price_max', 'currency',
            'is_featured', 'is_verified', 'views_count',
            'primary_image', 'created_at'
        ]

    def get_primary_image(self, obj):
        image = obj.primary_image
        if image:
            return {
                'image': image.image,
                'thumbnail': image.thumbnail
            }
        return None


class ListingDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detailed listing view"""
    merchant = MerchantListSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    business_hours = ListingBusinessHourSerializer(many=True, read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'merchant', 'title', 'description', 'listing_type',
            'category', 'tags', 'price_type', 'price',
            'price_min', 'price_max', 'currency', 'is_price_negotiable',
            'status', 'rejection_reason', 'is_verified', 'verified_at',
            'is_featured', 'featured_until', 'views_count', 'contact_count',
            'metadata', 'expires_at', 'created_at', 'updated_at',
            'business_hours', 'is_active'
        ]
        read_only_fields = [
            'id', 'merchant', 'is_verified', 'verified_at',
            'is_featured', 'featured_until', 'views_count',
            'contact_count', 'created_at', 'updated_at', 'is_active'
        ]


class ListingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating listings"""
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    images_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    business_hours_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Listing
        fields = [
            'title', 'description', 'listing_type', 'category',
            'price_type', 'price', 'price_min',
            'price_max', 'currency', 'is_price_negotiable',
            'tag_ids', 'images_data', 'business_hours_data', 'metadata'
        ]

    def validate(self, attrs):
        price_type = attrs.get('price_type')

        if price_type == 'FIXED':
            if not attrs.get('price'):
                raise serializers.ValidationError(
                    "Price is required for fixed price type."
                )
        elif price_type == 'RANGE':
            if not attrs.get('price_min') or not attrs.get('price_max'):
                raise serializers.ValidationError(
                    "Price min and max are required for range price type."
                )
            if attrs['price_min'] >= attrs['price_max']:
                raise serializers.ValidationError(
                    "Minimum price must be less than maximum price."
                )

        return attrs

    def create(self, validated_data):
        tag_ids = validated_data.pop('tag_ids', [])
        business_hours_data = validated_data.pop('business_hours_data', [])

        # Get merchant from request user
        merchant = self.context['request'].user.merchant_profile

        # Create listing with PENDING status
        listing = Listing.objects.create(
            merchant=merchant,
            status='PENDING',
            is_verified=False,
            **validated_data
        )

        # Add tags
        if tag_ids:
            from kakebe_apps.categories.models import Tag
            tags = Tag.objects.filter(id__in=tag_ids)
            listing.tags.set(tags)



        # Add business hours
        for hours_data in business_hours_data:
            ListingBusinessHour.objects.create(
                listing=listing,
                **hours_data
            )

        return listing


class ListingUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating listings by owner"""
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Listing
        fields = [
            'title', 'description', 'listing_type', 'category',
            'price_type', 'price', 'price_min',
            'price_max', 'currency', 'is_price_negotiable',
            'tag_ids', 'metadata', 'status'
        ]

    def validate_status(self, value):
        # Only allow merchants to change between DRAFT and PENDING
        allowed_statuses = ['DRAFT', 'PENDING']
        if value not in allowed_statuses:
            raise serializers.ValidationError(
                f"You can only set status to {', '.join(allowed_statuses)}."
            )
        return value

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop('tag_ids', None)

        # Update listing
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # If status changed to PENDING, reset verification
        if 'status' in validated_data and validated_data['status'] == 'PENDING':
            instance.is_verified = False
            instance.verified_at = None

        instance.save()

        # Update tags if provided
        if tag_ids is not None:
            from kakebe_apps.categories.models import Tag
            tags = Tag.objects.filter(id__in=tag_ids)
            instance.tags.set(tags)

        return instance




class ListingBusinessHourCreateSerializer(serializers.ModelSerializer):
    """Serializer for adding business hours to existing listings"""

    class Meta:
        model = ListingBusinessHour
        fields = ['day', 'opens_at', 'closes_at', 'is_closed']

    def create(self, validated_data):
        listing = self.context['listing']
        return ListingBusinessHour.objects.create(listing=listing, **validated_data)