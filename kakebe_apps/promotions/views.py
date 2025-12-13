# kakebe_apps/promotions/views.py

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import PromotionalCampaign, CampaignCreative, CampaignListing
from .serializers import (
    PromotionalCampaignSerializer, CampaignCreativeSerializer,
    ActiveCreativeSerializer, CampaignListingSerializer
)


class PromotionalCampaignViewSet(viewsets.ModelViewSet):
    queryset = PromotionalCampaign.objects.prefetch_related(
        'creatives__placements', 'listings__listing'
    )
    serializer_class = PromotionalCampaignSerializer
    permission_classes = [IsAuthenticated]  # Merchants or admins
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        # Assuming merchants can only manage their own campaigns
        # Adjust if you have a Merchant model link
        # return self.queryset.filter(...)  
        return self.queryset  # Or add merchant filter when available


class CampaignCreativeViewSet(viewsets.ModelViewSet):
    queryset = CampaignCreative.objects.select_related('campaign').prefetch_related('placements')
    serializer_class = CampaignCreativeSerializer
    permission_classes = [IsAuthenticated]


class CampaignListingViewSet(viewsets.ModelViewSet):
    queryset = CampaignListing.objects.select_related('campaign', 'listing')
    serializer_class = CampaignListingSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def increment_impressions(self, request, pk=None):
        campaign_listing = self.get_object()
        campaign_listing.impressions += 1
        campaign_listing.save(update_fields=['impressions'])
        return Response({'impressions': campaign_listing.impressions})

    @action(detail=True, methods=['post'])
    def increment_clicks(self, request, pk=None):
        campaign_listing = self.get_object()
        campaign_listing.clicks += 1
        campaign_listing.save(update_fields=['clicks'])
        return Response({'clicks': campaign_listing.clicks})


# Public read-only viewset for active creatives (no auth required)
class ActiveCreativeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActiveCreativeSerializer
    permission_classes = []  # Public access

    def get_queryset(self):
        now = timezone.now()
        return CampaignCreative.objects.filter(
            is_active=True,
            campaign__status='ACTIVE',
            campaign__start_date__lte=now,
            campaign__end_date__gte=now,
            # Optional: filter by platform from request header/query
        ).prefetch_related('placements').order_by('sort_order')