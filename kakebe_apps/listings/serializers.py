# kakebe_apps/listings/serializers.py
# CORRECTED VERSION - Fixed validation bug in ListingUpdateSerializer

from rest_framework import serializers
from django.utils import timezone
from .models import Listing, ListingTag, ListingBusinessHour
from kakebe_apps.categories.serializers import CategoryListSerializer as CategorySerializer, TagSerializer
from kakebe_apps.merchants.serializers import MerchantListSerializer
from ..imagehandler.models import ImageAsset


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
        return obj.primary_image


class ListingDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detailed listing view"""
    merchant = MerchantListSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    business_hours = ListingBusinessHourSerializer(many=True, read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    images = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id', 'merchant', 'title', 'description', 'listing_type',
            'category', 'tags', 'price_type', 'price',
            'price_min', 'price_max', 'currency', 'is_price_negotiable',
            'status', 'rejection_reason', 'is_verified', 'verified_at',
            'is_featured', 'featured_until', 'views_count', 'contact_count',
            'metadata', 'expires_at', 'created_at', 'updated_at',
            'business_hours', 'is_active', 'images'
        ]
        read_only_fields = [
            'id', 'merchant', 'is_verified', 'verified_at',
            'is_featured', 'featured_until', 'views_count',
            'contact_count', 'created_at', 'updated_at', 'is_active', 'images'
        ]

    def get_images(self, obj):
        return obj.images


class ListingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating listings"""
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    image_group_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text="List of image group IDs to attach to this listing"
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
            'tag_ids', 'image_group_ids', 'business_hours_data', 'metadata'
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

        # Validate image groups if provided
        image_group_ids = attrs.get('image_group_ids', [])
        if image_group_ids:
            user = self.context['request'].user

            # Check ownership and availability of image groups
            existing_groups = ImageAsset.objects.filter(
                owner=user,
                image_group_id__in=image_group_ids,
                is_confirmed=False,
                object_id__isnull=True
            ).values_list('image_group_id', flat=True).distinct()

            missing_groups = set(image_group_ids) - set(existing_groups)
            if missing_groups:
                raise serializers.ValidationError({
                    'image_group_ids': f"Image groups not found or already assigned: {missing_groups}"
                })

        return attrs

    def create(self, validated_data):
        tag_ids = validated_data.pop('tag_ids', [])
        image_group_ids = validated_data.pop('image_group_ids', [])
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

        # Attach images to listing
        if image_group_ids:
            ImageAsset.objects.filter(
                image_group_id__in=image_group_ids
            ).update(
                object_id=listing.id,
                is_confirmed=True
            )

        # Add business hours
        for hours_data in business_hours_data:
            ListingBusinessHour.objects.create(
                listing=listing,
                **hours_data
            )

        return listing


class ListingUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating listings by owner

    FIXED: Validation logic was previously unreachable - now properly structured
    """
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    add_image_group_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text="List of image group IDs to add to this listing"
    )
    remove_image_group_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text="List of image group IDs to remove from this listing"
    )

    class Meta:
        model = Listing
        fields = [
            'title', 'description', 'listing_type', 'category',
            'price_type', 'price', 'price_min',
            'price_max', 'currency', 'is_price_negotiable',
            'tag_ids', 'metadata', 'status',
            'add_image_group_ids', 'remove_image_group_ids'
        ]

    def validate(self, attrs):
        """
        FIXED: Previously the validation code after status validation was unreachable.
        Now all validation is properly executed.
        """
        # Validate status changes
        status_value = attrs.get('status')
        if status_value:
            allowed_statuses = ['DRAFT', 'PENDING']
            if status_value not in allowed_statuses:
                raise serializers.ValidationError({
                    'status': f"You can only set status to {', '.join(allowed_statuses)}."
                })

        # Validate price consistency
        price_type = attrs.get('price_type', self.instance.price_type)

        if price_type == 'FIXED':
            price = attrs.get('price', self.instance.price)
            if not price:
                raise serializers.ValidationError({
                    'price': 'Price is required for fixed price type.'
                })

        elif price_type == 'RANGE':
            price_min = attrs.get('price_min', self.instance.price_min)
            price_max = attrs.get('price_max', self.instance.price_max)

            if not price_min or not price_max:
                raise serializers.ValidationError({
                    'price_range': 'Both min and max prices are required for range price type.'
                })

            if price_min >= price_max:
                raise serializers.ValidationError({
                    'price_range': 'Minimum price must be less than maximum price.'
                })

        # Validate image group operations
        user = self.context['request'].user
        listing = self.instance

        add_groups = attrs.get('add_image_group_ids', [])
        remove_groups = attrs.get('remove_image_group_ids', [])

        if add_groups:
            # Verify user owns the draft image groups
            existing_groups = ImageAsset.objects.filter(
                owner=user,
                image_group_id__in=add_groups,
                is_confirmed=False,
                object_id__isnull=True
            ).values_list('image_group_id', flat=True).distinct()

            missing_groups = set(add_groups) - set(existing_groups)
            if missing_groups:
                raise serializers.ValidationError({
                    'add_image_group_ids': f"Image groups not found or not available: {list(missing_groups)}"
                })

        if remove_groups:
            # Verify user owns the attached image groups
            existing_groups = ImageAsset.objects.filter(
                owner=user,
                image_group_id__in=remove_groups,
                object_id=listing.id,
                is_confirmed=True
            ).values_list('image_group_id', flat=True).distinct()

            missing_groups = set(remove_groups) - set(existing_groups)
            if missing_groups:
                raise serializers.ValidationError({
                    'remove_image_group_ids': f"Image groups not found or not attached: {list(missing_groups)}"
                })

        return attrs

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop('tag_ids', None)
        add_image_groups = validated_data.pop('add_image_group_ids', [])
        remove_image_groups = validated_data.pop('remove_image_group_ids', [])

        # Update listing fields
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

        # Add image groups
        if add_image_groups:
            # Get current max order
            current_count = ImageAsset.objects.filter(
                object_id=instance.id,
                image_type="listing"
            ).count()

            ImageAsset.objects.filter(
                image_group_id__in=add_image_groups
            ).update(
                object_id=instance.id,
                is_confirmed=True,
                order=current_count
            )

        # Remove image groups
        if remove_image_groups:
            ImageAsset.objects.filter(
                image_group_id__in=remove_image_groups,
                object_id=instance.id
            ).update(
                object_id=None,
                is_confirmed=False,
                order=0
            )

        return instance


class ListingBusinessHourCreateSerializer(serializers.ModelSerializer):
    """Serializer for adding business hours to existing listings"""

    class Meta:
        model = ListingBusinessHour
        fields = ['day', 'opens_at', 'closes_at', 'is_closed']

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

    def create(self, validated_data):
        listing = self.context['listing']
        return ListingBusinessHour.objects.create(listing=listing, **validated_data)