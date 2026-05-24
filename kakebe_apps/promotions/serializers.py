# ===== serializers.py =====
from rest_framework import serializers
from .models import BannerImageImport, PromotionalBanner, BannerListing


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


class BannerImageImportSerializer(serializers.ModelSerializer):
    banner_title = serializers.CharField(source='banner.title', read_only=True)
    agent_name = serializers.CharField(source='uploaded_by_agent.name', read_only=True)
    cdn_url = serializers.SerializerMethodField()

    class Meta:
        model = BannerImageImport
        fields = [
            'id', 'banner', 'banner_title', 'uploaded_by_agent', 'agent_name',
            'source_path', 'target_field', 'status', 'image_asset', 'cdn_url',
            'error_message', 'metadata', 'processed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_cdn_url(self, obj):
        return obj.image_asset.cdn_url() if obj.image_asset else None


class BannerAgentUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
    metadata = serializers.JSONField(required=False)
    banner_id = serializers.UUIDField(required=False)
    target = serializers.ChoiceField(choices=['image', 'mobile_image'], required=False)
    title = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    display_type = serializers.ChoiceField(
        choices=[choice[0] for choice in PromotionalBanner.DISPLAY_TYPE_CHOICES],
        required=False,
    )
    placement = serializers.ChoiceField(
        choices=[choice[0] for choice in PromotionalBanner.PLACEMENT_CHOICES],
        required=False,
    )
    platform = serializers.ChoiceField(
        choices=[choice[0] for choice in PromotionalBanner.PLATFORM_CHOICES],
        required=False,
    )
    link_type = serializers.ChoiceField(
        choices=[choice[0] for choice in PromotionalBanner.LINK_TYPE_CHOICES],
        required=False,
    )
    listing_id = serializers.UUIDField(required=False)
    listing_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    category_id = serializers.UUIDField(required=False)
    merchant_id = serializers.UUIDField(required=False)
    link_url = serializers.URLField(required=False, allow_blank=True)
    cta_text = serializers.CharField(required=False, allow_blank=True, max_length=50)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    sort_order = serializers.IntegerField(required=False)

    def get_metadata(self):
        metadata = dict(self.validated_data.get('metadata') or {})
        for field, value in self.validated_data.items():
            if field in ['image', 'metadata']:
                continue
            if field in ['start_date', 'end_date']:
                metadata[field] = value.isoformat()
            elif field == 'listing_ids':
                metadata[field] = [str(item) for item in value]
            else:
                metadata[field] = str(value) if hasattr(value, 'hex') else value
        return metadata
