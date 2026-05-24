# ===== serializers.py =====
from rest_framework import serializers
from .models import PromotionalBanner, BannerListing


class BannerListingSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    listing_image = serializers.SerializerMethodField()

    class Meta:
        model = BannerListing
        fields = ['id', 'listing', 'listing_title', 'listing_image', 'sort_order']

    def get_listing_image(self, obj):
        primary_image = obj.listing.primary_image
        return primary_image['image'] if primary_image else None


class PromotionalBannerSerializer(serializers.ModelSerializer):
    featured_listings = BannerListingSerializer(many=True, read_only=True)
    is_currently_active = serializers.BooleanField(read_only=True)
    click_through_rate = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='link_category.name', read_only=True)
    merchant_name = serializers.CharField(source='link_merchant.display_name', read_only=True)
    target = serializers.SerializerMethodField()

    class Meta:
        model = PromotionalBanner
        fields = [
            'id', 'title', 'description', 'display_type', 'placement', 'platform',
            'image', 'mobile_image', 'link_type', 'link_url', 'link_category',
            'category_name', 'link_merchant', 'merchant_name', 'image_asset',
            'mobile_image_asset', 'cta_text', 'start_date', 'end_date',
            'is_verified', 'is_active', 'sort_order', 'impressions', 'clicks',
            'click_through_rate', 'featured_listings', 'is_currently_active',
            'target', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'impressions', 'clicks', 'verified_at', 'image_asset',
            'mobile_image_asset', 'target', 'created_at', 'updated_at'
        ]

    def get_click_through_rate(self, obj):
        return round(obj.get_click_through_rate(), 2)

    def get_target(self, obj):
        return obj.get_target_payload()

    def validate(self, data):
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] <= data['start_date']:
                raise serializers.ValidationError("End date must be after start date")

        if data.get('link_type') == 'URL' and not data.get('link_url'):
            raise serializers.ValidationError("Link URL is required when link type is URL")

        if data.get('link_type') == 'CATEGORY' and not data.get('link_category'):
            raise serializers.ValidationError("Category is required when link type is Category")

        if data.get('link_type') == 'MERCHANT' and not data.get('link_merchant'):
            raise serializers.ValidationError("Merchant is required when link type is Merchant")

        return data


class PromotionalBannerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    category_name = serializers.CharField(source='link_category.name', read_only=True)
    merchant_name = serializers.CharField(source='link_merchant.display_name', read_only=True)
    target = serializers.SerializerMethodField()

    class Meta:
        model = PromotionalBanner
        fields = [
            'id', 'title', 'display_type', 'placement', 'image', 'mobile_image',
            'link_type', 'link_url', 'link_category', 'category_name',
            'link_merchant', 'merchant_name', 'cta_text', 'target',
            'start_date', 'end_date', 'is_verified', 'is_active', 'sort_order'
        ]

    def get_target(self, obj):
        return obj.get_target_payload()


class BannerListingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BannerListing
        fields = ['listing', 'sort_order']
