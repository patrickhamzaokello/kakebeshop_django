from rest_framework import serializers
from django.contrib.auth import get_user_model

from kakebe_apps.orders.models import OrderIntent, OrderGroup
from kakebe_apps.categories.models import Category, Tag
from kakebe_apps.listings.models import Listing
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.imagehandler.models import ImageAsset

User = get_user_model()


# ─────────────────────────── Users ───────────────────────────

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'name', 'email', 'username', 'phone',
            'profile_image', 'is_active', 'is_staff', 'is_verified',
            'auth_provider', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'email', 'username', 'auth_provider', 'created_at', 'updated_at']


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active', 'is_staff', 'is_verified', 'name', 'phone']


# ─────────────────────────── Merchants ───────────────────────────

class AdminMerchantSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)

    class Meta:
        model = Merchant
        fields = [
            'id', 'user_id', 'user_name', 'user_email',
            'display_name', 'business_name', 'description',
            'business_phone', 'business_email', 'logo', 'cover_image',
            'verified', 'verification_date', 'featured', 'featured_order',
            'rating', 'total_reviews', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user_id', 'user_name', 'user_email', 'created_at', 'updated_at']


class AdminMerchantUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = [
            'verified', 'verification_date', 'featured', 'featured_order',
            'status', 'rating', 'display_name', 'business_name',
            'description', 'business_phone', 'business_email',
        ]


# ─────────────────────────── Listings ───────────────────────────

class AdminListingSerializer(serializers.ModelSerializer):
    merchant_name = serializers.CharField(source='merchant.display_name', read_only=True)
    merchant_id = serializers.UUIDField(source='merchant.id', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'merchant_id', 'merchant_name', 'title', 'description',
            'listing_type', 'category', 'category_name',
            'price_type', 'price', 'price_min', 'price_max', 'currency',
            'is_price_negotiable', 'status', 'is_verified', 'is_featured',
            'featured_until', 'views_count', 'contact_count',
            'created_at', 'updated_at', 'deleted_at',
        ]
        read_only_fields = [
            'id', 'merchant_id', 'merchant_name', 'category_name',
            'views_count', 'contact_count', 'created_at', 'updated_at',
        ]


class AdminListingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = [
            'status', 'is_verified', 'is_featured', 'featured_until',
            'title', 'description', 'category', 'price_type',
            'price', 'price_min', 'price_max', 'currency',
        ]


# ─────────────────────────── Categories ───────────────────────────

class AdminCategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True, allow_null=True)
    listings_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'icon',
            'parent', 'parent_name', 'is_active', 'is_featured',
            'sort_order', 'allows_order_intent', 'allows_cart',
            'is_contact_only', 'listings_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'parent_name', 'listings_count', 'created_at', 'updated_at']

    def get_listings_count(self, obj):
        return obj.listings.filter(deleted_at__isnull=True).count()


class AdminCategoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'name', 'description', 'icon', 'parent', 'is_active',
            'is_featured', 'sort_order', 'allows_order_intent',
            'allows_cart', 'is_contact_only',
        ]


# ─────────────────────────── Orders ───────────────────────────

class AdminOrderItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    listing_id = serializers.UUIDField(source='listing.id')
    listing_title = serializers.CharField(source='listing.title')
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2)


class AdminOrderSerializer(serializers.ModelSerializer):
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)
    buyer_email = serializers.EmailField(source='buyer.email', read_only=True)
    buyer_phone = serializers.CharField(source='buyer.phone', read_only=True)
    merchant_name = serializers.CharField(source='merchant.display_name', read_only=True)
    items = AdminOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = OrderIntent
        fields = [
            'id', 'order_number', 'status',
            'buyer', 'buyer_name', 'buyer_email', 'buyer_phone',
            'merchant', 'merchant_name',
            'total_amount', 'delivery_fee', 'notes',
            'cancellation_reason', 'cancelled_by',
            'expected_delivery_date',
            'items', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'order_number', 'buyer', 'buyer_name', 'buyer_email',
            'buyer_phone', 'merchant', 'merchant_name', 'items',
            'created_at', 'updated_at',
        ]


class AdminOrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderIntent
        fields = ['status', 'notes', 'cancellation_reason', 'cancelled_by']

    def validate_status(self, value):
        valid = ['NEW', 'CONTACTED', 'CONFIRMED', 'COMPLETED', 'CANCELLED']
        if value not in valid:
            raise serializers.ValidationError(f'Must be one of: {", ".join(valid)}')
        return value


# ─────────────────────────── Images ───────────────────────────

class AdminImageAssetSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    cdn_url = serializers.SerializerMethodField()

    class Meta:
        model = ImageAsset
        fields = [
            'id', 'owner', 'owner_email', 'image_group_id', 'object_id',
            'image_type', 'variant', 's3_key', 'cdn_url',
            'width', 'height', 'size_bytes', 'order',
            'is_confirmed', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_cdn_url(self, obj):
        return obj.cdn_url()


# ─────────────────────────── Stats ───────────────────────────

class AdminStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    staff_users = serializers.IntegerField()

    total_merchants = serializers.IntegerField()
    verified_merchants = serializers.IntegerField()
    pending_merchants = serializers.IntegerField()

    total_listings = serializers.IntegerField()
    active_listings = serializers.IntegerField()
    pending_listings = serializers.IntegerField()

    total_orders = serializers.IntegerField()
    new_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()

    total_categories = serializers.IntegerField()
    total_images = serializers.IntegerField()
