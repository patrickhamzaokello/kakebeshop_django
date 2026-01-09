# kakebe_apps/listings/views.py
# FIXED VERSION - Resolves FieldError with select_related and only()

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.http import HttpResponse
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import csv
import logging

from .models import Listing, ListingBusinessHour
from .serializers import (
    ListingListSerializer,
    ListingDetailSerializer,
    ListingCreateSerializer,
    ListingUpdateSerializer,
    ListingBusinessHourSerializer,
    ListingBusinessHourCreateSerializer
)
from .services import ListingService

from kakebe_apps.imagehandler.serializers import (
    ListingImageUploadSerializer,
    ListingImageReorderSerializer,
    ImageAssetSerializer
)
from ..imagehandler.models import ImageAsset

logger = logging.getLogger(__name__)


class ListingPagination(PageNumberPagination):
    """Custom pagination for listings with metadata"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page_size': self.page_size,
            'results': data
        })


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
    ViewSet for listing operations.

    Public endpoints:
    - list: GET /listings/ - Paginated list of verified, active listings
    - retrieve: GET /listings/{id}/ - Public listing detail
    - featured: GET /listings/featured/ - Shuffled featured listings
    - increment_views: POST /listings/{id}/increment_views/ - Track views (rate limited)
    - increment_contacts: POST /listings/{id}/increment_contacts/ - Track contacts (rate limited)

    Authenticated merchant endpoints:
    - my_listings: GET /listings/my_listings/ - Get own listings
    - create: POST /listings/ - Create listing
    - partial_update: PATCH /listings/{id}/ - Update own listing
    - destroy: DELETE /listings/{id}/ - Soft delete own listing
    - add_images: POST /listings/{id}/add_images/ - Add images to listing
    - reorder_images: POST /listings/{id}/reorder_images/ - Reorder listing images
    - get_uploadable_images: GET /listings/{id}/get_uploadable_images/ - Get draft images
    - remove_image_group: DELETE /listings/{id}/remove_image_group/{image_group_id}/ - Remove image group
    - add_business_hour: POST /listings/{id}/add_business_hour/ - Add business hours
    - bulk_update_status: POST /listings/bulk_update_status/ - Bulk status update
    - bulk_delete: POST /listings/bulk_delete/ - Bulk soft delete
    - analytics: GET /listings/analytics/ - Get merchant analytics
    - export_csv: GET /listings/export_csv/ - Export listings to CSV
    """

    pagination_class = ListingPagination

    def get_queryset(self):
        """
        Optimized base queryset for verified, active listings.
        Uses select_related and prefetch_related to minimize database queries.

        NOTE: We removed .only() to avoid FieldError when using select_related.
        If you need to limit fields, use defer() instead, or handle it in the serializer.
        """
        return Listing.objects.filter(
            status='ACTIVE',
            is_verified=True,
            deleted_at__isnull=True,
            merchant__verified=True
        ).select_related(
            'merchant',
            'merchant__user',
            'category'
        ).prefetch_related(
            'tags'
        )

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

        # Sorting with validated fields
        ALLOWED_SORT_FIELDS = {
            'created_at': 'created_at',
            '-created_at': '-created_at',
            'price': 'price',
            '-price': '-price',
            'views': 'views_count',
            '-views': '-views_count',
            'title': 'title',
            '-title': '-title',
        }

        sort_by = request.query_params.get('sort_by', '-created_at')
        order_field = ALLOWED_SORT_FIELDS.get(sort_by, '-created_at')
        queryset = queryset.order_by(order_field)

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

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    @action(detail=False, methods=['get'], url_path='featured')
    def featured(self, request):
        """
        Get featured listings in shuffled order with caching.
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
        ).select_related('category').prefetch_related('tags')

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

        # Extract related data
        tag_ids = serializer.validated_data.pop('tag_ids', [])
        image_group_ids = serializer.validated_data.pop('image_group_ids', [])
        business_hours_data = serializer.validated_data.pop('business_hours_data', [])

        try:
            # Use service layer for business logic
            listing = ListingService.create_listing(
                merchant=request.user.merchant_profile,
                validated_data=serializer.validated_data,
                tag_ids=tag_ids,
                image_group_ids=image_group_ids,
                business_hours_data=business_hours_data
            )

            logger.info(
                f"Listing created successfully: {listing.id}",
                extra={
                    'merchant_id': str(request.user.merchant_profile.id),
                    'listing_id': str(listing.id)
                }
            )

            return Response(
                ListingDetailSerializer(listing, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(
                f"Listing creation failed: {str(e)}",
                exc_info=True,
                extra={'merchant_id': str(request.user.merchant_profile.id)}
            )
            return Response(
                {'detail': 'Failed to create listing. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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

        # Extract related data
        tag_ids = serializer.validated_data.pop('tag_ids', None)
        add_image_groups = serializer.validated_data.pop('add_image_group_ids', [])
        remove_image_groups = serializer.validated_data.pop('remove_image_group_ids', [])

        try:
            # Use service layer
            listing = ListingService.update_listing(
                listing=listing,
                validated_data=serializer.validated_data,
                tag_ids=tag_ids,
                add_image_groups=add_image_groups,
                remove_image_groups=remove_image_groups
            )

            logger.info(f"Listing updated: {listing.id}")

            return Response(
                ListingDetailSerializer(listing, context={'request': request}).data
            )
        except Exception as e:
            logger.error(f"Listing update failed: {str(e)}", exc_info=True)
            return Response(
                {'detail': 'Failed to update listing. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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

        ListingService.soft_delete_listing(listing)

        return Response(
            {'detail': 'Listing deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def add_images(self, request, pk=None):
        """Attach existing images to listing"""
        listing = get_object_or_404(
            Listing,
            pk=pk,
            merchant=request.user.merchant_profile
        )

        serializer = ListingImageUploadSerializer(
            data=request.data,
            context={'request': request, 'listing': listing}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'detail': 'Images attached successfully.'},
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def reorder_images(self, request, pk=None):
        """Reorder listing images"""
        listing = get_object_or_404(
            Listing,
            pk=pk,
            merchant=request.user.merchant_profile
        )

        serializer = ListingImageReorderSerializer(
            data=request.data,
            context={'request': request, 'listing': listing}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'detail': 'Images reordered successfully.'},
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def get_uploadable_images(self, request, pk=None):
        """Get draft images that can be attached to this listing"""
        # Verify listing ownership
        listing = get_object_or_404(
            Listing,
            pk=pk,
            merchant=request.user.merchant_profile
        )

        # Use service layer
        uploadable_images = ListingService.get_uploadable_images(request.user)
        return Response(uploadable_images)

    @action(
        detail=True,
        methods=['delete'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile],
        url_path='remove_image_group/(?P<image_group_id>[^/.]+)'
    )
    def remove_image_group(self, request, pk=None, image_group_id=None):
        """Remove an image group from listing"""
        listing = get_object_or_404(
            Listing,
            pk=pk,
            merchant=request.user.merchant_profile
        )

        try:
            # Remove image group from listing
            updated = ImageAsset.objects.filter(
                image_group_id=image_group_id,
                object_id=listing.id,
                owner=request.user
            ).update(
                object_id=None,
                is_confirmed=False,
                order=0
            )

            if updated == 0:
                return Response(
                    {'detail': 'Image group not found or not owned by you.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {'detail': 'Image group removed successfully.'},
                status=status.HTTP_200_OK
            )

        except ValueError:
            return Response(
                {'detail': 'Invalid image group ID.'},
                status=status.HTTP_400_BAD_REQUEST
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
        """
        Increment view count for a listing with rate limiting.
        Prevents abuse by limiting increments per IP address.
        """
        listing = get_object_or_404(self.get_queryset(), pk=pk)
        user_ip = request.META.get('REMOTE_ADDR', 'unknown')

        # Use service layer with rate limiting
        views_count = ListingService.increment_views(listing, user_ip)

        return Response({'views_count': views_count})

    @action(detail=True, methods=['post'])
    def increment_contacts(self, request, pk=None):
        """
        Increment contact count for a listing with rate limiting.
        Prevents abuse by limiting increments per IP address.
        """
        listing = get_object_or_404(self.get_queryset(), pk=pk)
        user_ip = request.META.get('REMOTE_ADDR', 'unknown')

        # Use service layer with rate limiting
        contact_count = ListingService.increment_contacts(listing, user_ip)

        return Response({'contact_count': contact_count})

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def bulk_update_status(self, request):
        """
        Bulk update status for merchant's own listings.

        Body:
        {
            "listing_ids": ["uuid1", "uuid2", ...],
            "status": "DRAFT" or "PENDING"
        }
        """
        listing_ids = request.data.get('listing_ids', [])
        new_status = request.data.get('status')

        if not listing_ids:
            return Response(
                {'detail': 'listing_ids is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not new_status:
            return Response(
                {'detail': 'status is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            updated = ListingService.bulk_update_status(
                listing_ids=listing_ids,
                merchant=request.user.merchant_profile,
                new_status=new_status
            )

            return Response({
                'detail': f'{updated} listing(s) updated to {new_status}.',
                'updated_count': updated
            })
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def bulk_delete(self, request):
        """
        Soft delete multiple listings.

        Body:
        {
            "listing_ids": ["uuid1", "uuid2", ...]
        }
        """
        listing_ids = request.data.get('listing_ids', [])

        if not listing_ids:
            return Response(
                {'detail': 'listing_ids is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted = ListingService.bulk_soft_delete(
            listing_ids=listing_ids,
            merchant=request.user.merchant_profile
        )

        return Response({
            'detail': f'{deleted} listing(s) deleted successfully.',
            'deleted_count': deleted
        })

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def analytics(self, request):
        """
        Get analytics for merchant's listings.

        Query params:
        - days: Number of days to include (default: 30)
        """
        days = request.query_params.get('days', 30)
        try:
            days = int(days)
            if days < 1 or days > 365:
                days = 30
        except ValueError:
            days = 30

        analytics_data = ListingService.get_merchant_analytics(
            merchant=request.user.merchant_profile,
            days=days
        )

        return Response(analytics_data)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def export_csv(self, request):
        """Export merchant's listings to CSV"""
        merchant = request.user.merchant_profile
        listings = Listing.objects.filter(
            merchant=merchant,
            deleted_at__isnull=True
        ).select_related('category').order_by('-created_at')

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="listings_{timezone.now().date()}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Title', 'Type', 'Category', 'Status',
            'Price Type', 'Price', 'Currency', 'Views',
            'Contacts', 'Is Featured', 'Is Verified', 'Created'
        ])

        for listing in listings:
            price_display = ''
            if listing.price_type == 'FIXED' and listing.price:
                price_display = f"{listing.price}"
            elif listing.price_type == 'RANGE':
                price_display = f"{listing.price_min}-{listing.price_max}"
            elif listing.price_type == 'ON_REQUEST':
                price_display = "On Request"

            writer.writerow([
                str(listing.id),
                listing.title,
                listing.get_listing_type_display(),
                listing.category.name,
                listing.get_status_display(),
                listing.get_price_type_display(),
                price_display,
                listing.currency,
                listing.views_count,
                listing.contact_count,
                'Yes' if listing.is_featured else 'No',
                'Yes' if listing.is_verified else 'No',
                listing.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])

        logger.info(f"CSV export completed for merchant {merchant.id}")
        return response

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated, HasMerchantProfile]
    )
    def stats(self, request, pk=None):
        """Get detailed statistics for a specific listing"""
        listing = get_object_or_404(
            Listing,
            pk=pk,
            merchant=request.user.merchant_profile
        )

        stats = ListingService.get_listing_stats(listing)

        return Response(stats)