from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.db.models import Q
from .models import PromotionalBanner, BannerListing
from .serializers import (
    PromotionalBannerSerializer,
    PromotionalBannerListSerializer,
    BannerListingSerializer,
    BannerListingCreateSerializer
)


class PromotionalBannerViewSet(viewsets.ModelViewSet):
    queryset = PromotionalBanner.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return PromotionalBannerListSerializer
        return PromotionalBannerSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'active', 'by_placement']:
            return []
        return [IsAdminUser()]

    def get_queryset(self):
        queryset = PromotionalBanner.objects.select_related('link_category')

        # Filter by placement
        placement = self.request.query_params.get('placement')
        if placement:
            queryset = queryset.filter(placement=placement)

        # Filter by display type
        display_type = self.request.query_params.get('display_type')
        if display_type:
            queryset = queryset.filter(display_type=display_type)

        # Filter by platform
        platform = self.request.query_params.get('platform')
        if platform:
            queryset = queryset.filter(Q(platform=platform) | Q(platform='ALL'))

        # Admin sees all, users see only active/verified
        if not self.request.user.is_staff:
            now = timezone.now()
            queryset = queryset.filter(
                is_active=True,
                is_verified=True,
                start_date__lte=now,
                end_date__gte=now
            )

        return queryset.prefetch_related('featured_listings__listing')

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all currently active banners"""
        now = timezone.now()
        banners = self.get_queryset().filter(
            is_active=True,
            is_verified=True,
            start_date__lte=now,
            end_date__gte=now
        )
        serializer = self.get_serializer(banners, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_placement(self, request):
        """Get banners grouped by placement"""
        placement = request.query_params.get('placement')
        if not placement:
            return Response(
                {'error': 'placement parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        banners = self.get_queryset().filter(placement=placement)
        serializer = self.get_serializer(banners, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify(self, request, pk=None):
        """Verify a banner"""
        banner = self.get_object()
        banner.is_verified = True
        banner.verified_at = timezone.now()
        banner.save()
        serializer = self.get_serializer(banner)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def unverify(self, request, pk=None):
        """Unverify a banner"""
        banner = self.get_object()
        banner.is_verified = False
        banner.verified_at = None
        banner.save()
        serializer = self.get_serializer(banner)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def track_impression(self, request, pk=None):
        """Track banner impression"""
        banner = self.get_object()
        banner.impressions += 1
        banner.save(update_fields=['impressions'])
        return Response({'status': 'impression tracked'})

    @action(detail=True, methods=['post'])
    def track_click(self, request, pk=None):
        """Track banner click"""
        banner = self.get_object()
        banner.clicks += 1
        banner.save(update_fields=['clicks'])
        return Response({'status': 'click tracked'})

    @action(detail=True, methods=['post', 'get'], permission_classes=[IsAdminUser])
    def listings(self, request, pk=None):
        """Manage banner listings"""
        banner = self.get_object()

        if request.method == 'GET':
            listings = banner.featured_listings.all()
            serializer = BannerListingSerializer(listings, many=True)
            return Response(serializer.data)

        # POST - add listings
        serializer = BannerListingCreateSerializer(data=request.data, many=isinstance(request.data, list))
        if serializer.is_valid():
            listings_data = serializer.validated_data if isinstance(request.data, list) else [serializer.validated_data]

            created_listings = []
            for listing_data in listings_data:
                banner_listing, created = BannerListing.objects.get_or_create(
                    banner=banner,
                    listing=listing_data['listing'],
                    defaults={'sort_order': listing_data.get('sort_order', 0)}
                )
                created_listings.append(banner_listing)

            response_serializer = BannerListingSerializer(created_listings, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BannerListingViewSet(viewsets.ModelViewSet):
    queryset = BannerListing.objects.all()
    serializer_class = BannerListingSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = BannerListing.objects.select_related('banner', 'listing')

        banner_id = self.request.query_params.get('banner')
        if banner_id:
            queryset = queryset.filter(banner_id=banner_id)

        return queryset
