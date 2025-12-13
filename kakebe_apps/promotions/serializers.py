# kakebe_apps/promotions/serializers.py

from rest_framework import serializers
from django.utils import timezone

from .models import (
    PromotionalCampaign, CampaignListing,
    CampaignCreative, CampaignPlacement
)
from kakebe_apps.listings.models import Listing


class CampaignListingSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    listing_image = serializers.URLField(source='listing.main_image', read_only=True)

    class Meta:
        model = CampaignListing
        fields = [
            'id', 'listing', 'listing_title', 'listing_image',
            'impressions', 'clicks', 'conversions', 'created_at'
        ]
        read_only_fields = ['impressions', 'clicks', 'conversions', 'created_at']


class CampaignPlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignPlacement
        fields = [
            'id', 'placement', 'target_type', 'target_id',
            'target_url', 'created_at'
        ]
        read_only_fields = ['created_at']


class CampaignCreativeSerializer(serializers.ModelSerializer):
    placements = CampaignPlacementSerializer(many=True, read_only=True)

    class Meta:
        model = CampaignCreative
        fields = [
            'id', 'creative_type', 'title', 'subtitle', 'image',
            'thumbnail', 'platform', 'cta_text', 'sort_order',
            'is_active', 'start_date', 'end_date', 'created_at',
            'placements'
        ]
        read_only_fields = ['created_at']


class PromotionalCampaignSerializer(serializers.ModelSerializer):
    creatives = CampaignCreativeSerializer(many=True, read_only=True)
    # FIXED: Removed redundant source='listings' since field name matches the relation name
    listings = CampaignListingSerializer(many=True, read_only=True)

    class Meta:
        model = PromotionalCampaign
        fields = [
            'id', 'name', 'description', 'campaign_type',
            'start_date', 'end_date', 'budget', 'status',
            'created_at', 'updated_at',
            'creatives', 'listings'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        start_date = attrs.get('start_date', self.instance.start_date if self.instance else None)
        end_date = attrs.get('end_date', self.instance.end_date if self.instance else None)

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("end_date cannot be before start_date.")

        status = attrs.get('status')
        if status == 'ACTIVE':
            now = timezone.now()
            if start_date and start_date > now:
                raise serializers.ValidationError("Cannot activate campaign before start_date.")
            if end_date and end_date < now:
                raise serializers.ValidationError("Cannot activate campaign after end_date.")

        return attrs


# Read-only serializer for public active creatives (e.g., home page banners)
class ActiveCreativeSerializer(serializers.ModelSerializer):
    placements = CampaignPlacementSerializer(many=True, read_only=True)

    class Meta:
        model = CampaignCreative
        fields = [
            'id', 'creative_type', 'title', 'subtitle', 'image',
            'thumbnail', 'platform', 'cta_text', 'sort_order',
            'placements'
        ]
        read_only_fields = fields  # All fields are read-only