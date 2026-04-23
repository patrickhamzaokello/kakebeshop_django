# kakebe_apps/listings/serializers.py
# CORRECTED VERSION - Fixed validation bug in ListingUpdateSerializer

from rest_framework import serializers
from django.utils import timezone
from django.utils.text import slugify
from .models import Listing, ListingTag, ListingBusinessHour, ListingDeliveryMode
from kakebe_apps.categories.serializers import CategoryListSerializer as CategorySerializer, TagSerializer
from kakebe_apps.merchants.serializers import MerchantListSerializer
from ..imagehandler.models import ImageAsset


class ListingDeliveryModeSerializer(serializers.ModelSerializer):
    mode_display = serializers.CharField(source='get_mode_display', read_only=True)

    class Meta:
        model = ListingDeliveryMode
        fields = ['id', 'mode', 'mode_display', 'notes', 'delivery_fee', 'estimated_days', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        listing = self.context['listing']
        return ListingDeliveryMode.objects.create(listing=listing, **validated_data)


class ListingDeliveryModeWriteSerializer(serializers.Serializer):
    """Used inline inside create/update serializers."""
    mode = serializers.ChoiceField(choices=ListingDeliveryMode.DELIVERY_MODE_CHOICES)
    notes = serializers.CharField(max_length=255, required=False, default='')
    delivery_fee = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    estimated_days = serializers.IntegerField(min_value=0, required=False, allow_null=True)


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
    delivery_modes = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id', 'merchant', 'title', 'listing_type',
            'category_name', 'price_type',
            'price', 'price_min', 'price_max', 'currency',
            'is_featured', 'is_verified', 'views_count',
            'primary_image', 'delivery_modes', 'created_at'
        ]

    def get_primary_image(self, obj):
        if hasattr(obj, '_cached_primary_image'):
            return obj._cached_primary_image
        return obj.primary_image

    def get_delivery_modes(self, obj):
        return list(obj.delivery_modes.values_list('mode', flat=True))


class ListingDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detailed listing view"""
    merchant = MerchantListSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    business_hours = ListingBusinessHourSerializer(many=True, read_only=True)
    delivery_modes = ListingDeliveryModeSerializer(many=True, read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    images = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id', 'merchant', 'title', 'description', 'listing_type',
            'category', 'tags', 'price_type', 'price',
            'price_min', 'price_max', 'currency', 'is_price_negotiable',
            'status', 'rejection_reason', 'is_verified', 'verified_at',
            'is_featured', 'featured_until', 'views_count', 'contact_count',
            'metadata', 'expires_at', 'created_at', 'updated_at',
            'business_hours', 'delivery_modes', 'is_active', 'images', 'share_url'
        ]
        read_only_fields = [
            'id', 'merchant', 'is_verified', 'verified_at',
            'is_featured', 'featured_until', 'views_count',
            'contact_count', 'created_at', 'updated_at', 'is_active', 'images'
        ]

    def get_images(self, obj):
        return obj.images

    def get_share_url(self, obj):
        return f"https://kakebeshop.com/listing/{obj.id}"


class ListingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating listings"""
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False,
        default=list,
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
    delivery_modes_data = ListingDeliveryModeWriteSerializer(
        many=True, write_only=True, required=False, default=list
    )

    class Meta:
        model = Listing
        fields = [
            'title', 'description', 'listing_type', 'category',
            'price_type', 'price', 'price_min',
            'price_max', 'currency', 'is_price_negotiable',
            'tags', 'image_group_ids', 'business_hours_data',
            'delivery_modes_data', 'metadata'
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

        # Validate no duplicate modes in the submitted list
        delivery_modes_data = attrs.get('delivery_modes_data', [])
        if delivery_modes_data:
            submitted_modes = [d['mode'] for d in delivery_modes_data]
            if len(submitted_modes) != len(set(submitted_modes)):
                raise serializers.ValidationError({
                    'delivery_modes_data': ['Duplicate delivery modes are not allowed.']
                })

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
        tag_names = validated_data.pop('tags', [])
        image_group_ids = validated_data.pop('image_group_ids', [])
        business_hours_data = validated_data.pop('business_hours_data', [])
        delivery_modes_data = validated_data.pop('delivery_modes_data', [])

        # Get merchant from request user
        merchant = self.context['request'].user.merchant_profile

        # Create listing with PENDING status
        listing = Listing.objects.create(
            merchant=merchant,
            status='PENDING',
            is_verified=False,
            **validated_data
        )

        # Add tags — create any that don't exist yet
        if tag_names:
            from kakebe_apps.categories.models import Tag
            tag_objs = []
            for name in tag_names:
                name = name.strip().lower()
                if name:
                    tag, _ = Tag.objects.get_or_create(
                        slug=slugify(name),
                        defaults={'name': name}
                    )
                    tag_objs.append(tag)
            if tag_objs:
                listing.tags.set(tag_objs)

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

        # Add delivery modes
        for mode_data in delivery_modes_data:
            ListingDeliveryMode.objects.create(listing=listing, **mode_data)

        return listing


class ListingUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating listings by owner

    FIXED: Validation logic was previously unreachable - now properly structured
    """
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False,
        default=list,
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
    add_delivery_modes = ListingDeliveryModeWriteSerializer(
        many=True, write_only=True, required=False
    )
    remove_delivery_modes = serializers.ListField(
        child=serializers.ChoiceField(choices=ListingDeliveryMode.DELIVERY_MODE_CHOICES),
        write_only=True,
        required=False,
        help_text="List of mode strings to remove, e.g. ['PICKUP', 'DIGITAL']"
    )

    class Meta:
        model = Listing
        fields = [
            'title', 'description', 'listing_type', 'category',
            'price_type', 'price', 'price_min',
            'price_max', 'currency', 'is_price_negotiable',
            'tags', 'metadata', 'status',
            'add_image_group_ids', 'remove_image_group_ids',
            'add_delivery_modes', 'remove_delivery_modes',
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

        # Validate delivery mode operations
        add_modes = attrs.get('add_delivery_modes', [])
        remove_modes = attrs.get('remove_delivery_modes', [])

        if add_modes:
            submitted = [d['mode'] for d in add_modes]
            if len(submitted) != len(set(submitted)):
                raise serializers.ValidationError({
                    'add_delivery_modes': ['Duplicate delivery modes are not allowed.']
                })
            existing = set(
                self.instance.delivery_modes
                .filter(mode__in=submitted)
                .values_list('mode', flat=True)
            )
            if existing:
                raise serializers.ValidationError({
                    'add_delivery_modes': [
                        f"Delivery mode(s) already set on this listing: {sorted(existing)}"
                    ]
                })

        if remove_modes:
            existing = set(
                self.instance.delivery_modes
                .filter(mode__in=remove_modes)
                .values_list('mode', flat=True)
            )
            missing = set(remove_modes) - existing
            if missing:
                raise serializers.ValidationError({
                    'remove_delivery_modes': [
                        f"Delivery mode(s) not set on this listing: {sorted(missing)}"
                    ]
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
        tag_names = validated_data.pop('tags', None)
        add_image_groups = validated_data.pop('add_image_group_ids', [])
        remove_image_groups = validated_data.pop('remove_image_group_ids', [])
        add_delivery_modes = validated_data.pop('add_delivery_modes', [])
        remove_delivery_modes = validated_data.pop('remove_delivery_modes', [])

        # Update listing fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # If status changed to PENDING, reset verification
        if 'status' in validated_data and validated_data['status'] == 'PENDING':
            instance.is_verified = False
            instance.verified_at = None

        instance.save()

        # Update tags if provided — create any that don't exist yet
        if tag_names is not None:
            from kakebe_apps.categories.models import Tag
            tag_objs = []
            for name in tag_names:
                name = name.strip().lower()
                if name:
                    tag, _ = Tag.objects.get_or_create(
                        slug=slugify(name),
                        defaults={'name': name}
                    )
                    tag_objs.append(tag)
            instance.tags.set(tag_objs)

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

        # Add delivery modes
        for mode_data in add_delivery_modes:
            ListingDeliveryMode.objects.create(listing=instance, **mode_data)

        # Remove delivery modes
        if remove_delivery_modes:
            instance.delivery_modes.filter(mode__in=remove_delivery_modes).delete()

        return instance


class MyListingSerializer(serializers.ModelSerializer):
    """Lightweight serializer for a merchant's own listing list."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'description', 'listing_type',
            'category_name', 'price_type', 'price', 'price_min',
            'price_max', 'currency', 'status', 'is_featured',
            'is_verified', 'views_count', 'contact_count',
            'primary_image', 'created_at', 'updated_at',
        ]

    def get_primary_image(self, obj):
        if hasattr(obj, '_cached_primary_image'):
            return obj._cached_primary_image
        return obj.primary_image


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