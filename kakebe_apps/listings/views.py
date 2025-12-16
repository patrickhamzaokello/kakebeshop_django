# kakebe_apps/listings/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from .models import Listing, ListingImage, ListingBusinessHour
from .serializers import (
    ListingListSerializer,
    ListingDetailSerializer,
    ListingCreateSerializer,
    ListingUpdateSerializer,
    ListingImageSerializer,
    ListingImageCreateSerializer,
    ListingBusinessHourSerializer,
    ListingBusinessHourCreateSerializer
)


class ListingPagination(PageNumberPagination):
    """Custom pagination for listings"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsListingOwner(permissions.BasePermission):
    """Custom permission: only the listing owner can edit"""

    def has_object_permission(self, request, view, obj):
        return obj.merchant.user == request.user


class HasMerchantProfile(permissions.BasePermission):
    """Check if user has a merchant profile"""

    def has_permission(self, request, view):
        return hasattr(request.user, 'merchant_profile')


class ListingViewSet(viewsets.ViewSet):
    """
    ViewSet for listing operations:

    Public endpoints:
    - list: GET /listings/ - Paginated list of verified, active listings
    - retrieve: GET /listings/{id}/ - Public listing detail
    - featured: GET /listings/featured/ - Shuffled featured listings

    Authenticated merchant endpoints:
    - my_listings: GET /listings/my_listings/ - Get own listings
    - create: POST /listings/ - Create listing
    - update: PATCH /listings/{id}/ - Update own listing
    - delete: DELETE /listings/{id}/ - Soft delete own listing
    - add_image: POST /listings/{id}/add_image/ - Add image to listing
    - remove_image: DELETE /listings/{id}/remove_image/{image_id}/ - Remove image
    - add_business_hour: POST /listings/{id}/add_business_hour/ - Add business hours
    - increment_views: POST /listings/{id}/increment_views/ - Track views
    - increment_contacts: POST /listings/{id}/increment_contacts/ - Track contacts
    """

    pagination_class = ListingPagination

    def get_queryset(self):
        """Base queryset for verified, active listings only"""
        return Listing.objects.filter(
            status='ACTIVE',
            is_verified=True,
            deleted_at__isnull=True,
            merchant__verified=True  # Only show listings from verified merchants
        ).select_related('merchant', 'merchant__user', 'category', 'location').prefetch_related('images', 'tags')

    def list(self, request):
        """List verified and active listings with filtering and search"""
        queryset = self.get_queryset()

        # Search functionality
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        # Filter by listing type
        listing_type = request.query_params.get('listing_type', None)
        if listing_type and listing_type in ['PRODUCT', 'SERVICE']:
            queryset = queryset.filter(listing_type=listing_type)

        # Filter by category
        category_id = request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Filter by location
        location_id = request.query_params.get('location', None)
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        # Filter by merchant
        merchant_id = request.query_params.get('merchant', None)
        if merchant_id:
            queryset = queryset.filter(merchant_id=merchant_id)

        # Filter by price range
        min_price = request.query_params.get('min_price', None)
        max_price = request.query_params.get('max_price', None)
        if min_price:
            try:
                queryset = queryset.filter(
                    Q(price__gte=float(min_price)) |
                    Q(price_min__gte=float(min_price))
                )
            except ValueError:
                pass
        if max_price:
            try:
                queryset = queryset.filter(
                    Q(price__lte=float(max_price)) |
                    Q(price_max__lte=float(max_price))
                )
            except ValueError:
                pass

        # Sorting
        sort_by = request.query_params.get('sort_by', '-created_at')
        valid_sort_fields = [
            'created_at', '-created_at',
            'price', '-price',
            'views_count', '-views_count',
            'title', '-title'
        ]
        if sort_by in valid_sort_fields:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-created_at')

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = ListingListSerializer(
                page, many=True, context={'request': request}
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = ListingListSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Retrieve single listing (must be verified and active)"""
        listing = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = ListingDetailSerializer(listing, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='featured')
    def featured(self, request):
        """
        Get featured listings in shuffled order.
        Query params:
        - limit: Number of listings to return (default: 10, max: 50)
        """
        limit = request.query_params.get('limit', 10)
        try:
            limit = min(int(limit), 50)
        except ValueError:
            limit = 10

        # Get featured, verified, and active listings in random order
        now = timezone.now()
        queryset = self.get_queryset().filter(
            is_featured=True
        ).filter(
            Q(featured_until__isnull=True) | Q(featured_until__gt=now)
        ).order_by('?')[:limit]

        serializer = ListingListSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def my_listings(self, request):
        """Get authenticated merchant's listings (all statuses)"""
        merchant = request.user.merchant_profile
        queryset = Listing.objects.filter(
            merchant=merchant,
            deleted_at__isnull=True
        ).select_related('category', 'location').prefetch_related('images', 'tags')

        # Filter by status if provided
        status_filter = request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = ListingDetailSerializer(
                page, many=True, context={'request': request}
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = ListingDetailSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    def create(self, request):
        """Create a new listing (requires merchant profile)"""
        if not hasattr(request.user, 'merchant_profile'):
            return Response(
                {'detail': 'You must have a merchant profile to create listings.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ListingCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        listing = serializer.save()

        return Response(
            ListingDetailSerializer(listing, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, pk=None):
        """Update own listing"""
        if not hasattr(request.user, 'merchant_profile'):
            return Response(
                {'detail': 'You must have a merchant profile.'},
                status=status.HTTP_403_FORBIDDEN
            )

        listing = get_object_or_404(
            Listing,
            pk=pk,
            merchant=request.user.merchant_profile
        )

        serializer = ListingUpdateSerializer(
            listing,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            ListingDetailSerializer(listing, context={'request': request}).data
        )

    def destroy(self, request, pk=None):
        """Soft delete own listing"""
        if not hasattr(request.user, 'merchant_profile'):
            return Response(
                {'detail': 'You must have a merchant profile.'},
                status=status.HTTP_403_FORBIDDEN
            )

        listing = get_object_or_404(
            Listing,
            pk=pk,
            merchant=request.user.merchant_profile
        )
        listing.soft_delete()

        return Response(
            {'detail': 'Listing deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def add_image(self, request, pk=None):
        """Add an image to listing"""
        listing = get_object_or_404(
            Listing,
            pk=pk,
            merchant=request.user.merchant_profile
        )

        serializer = ListingImageCreateSerializer(
            data=request.data,
            context={'listing': listing}
        )
        serializer.is_valid(raise_exception=True)
        image = serializer.save()

        return Response(
            ListingImageSerializer(image).data,
            status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=['delete'],
        url_path='remove_image/(?P<image_id>[^/.]+)',
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def remove_image(self, request, pk=None, image_id=None):
        """Remove an image from listing"""
        listing = get_object_or_404(
            Listing,
            pk=pk,
            merchant=request.user.merchant_profile
        )

        image = get_object_or_404(ListingImage, pk=image_id, listing=listing)
        image.delete()

        return Response(
            {'detail': 'Image removed successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def add_business_hour(self, request, pk=None):
        """Add business hours to listing"""
        listing = get_object_or_404(
            Listing,
            pk=pk,
            merchant=request.user.merchant_profile
        )

        serializer = ListingBusinessHourCreateSerializer(
            data=request.data,
            context={'listing': listing}
        )
        serializer.is_valid(raise_exception=True)
        hour = serializer.save()

        return Response(
            ListingBusinessHourSerializer(hour).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        """Increment view count for a listing"""
        listing = get_object_or_404(self.get_queryset(), pk=pk)
        listing.increment_views()
        return Response({'views_count': listing.views_count})

    @action(detail=True, methods=['post'])
    def increment_contacts(self, request, pk=None):
        """Increment contact count for a listing"""
        listing = get_object_or_404(self.get_queryset(), pk=pk)
        listing.increment_contacts()
        return Response({'contact_count': listing.contact_count})