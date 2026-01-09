# kakebe_apps/listings/views.py
from django.core.cache import cache
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from .models import Listing, ListingBusinessHour
from .serializers import (
    ListingListSerializer,
    ListingDetailSerializer,
    ListingCreateSerializer,
    ListingUpdateSerializer,
    ListingBusinessHourSerializer,
    ListingBusinessHourCreateSerializer
)

from kakebe_apps.imagehandler.serializers import (
ListingImageUploadSerializer,
ListingImageReorderSerializer,
ImageAssetSerializer
)
from ..imagehandler.models import ImageAsset


class ListingPagination(PageNumberPagination):
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
            merchant__verified=True
        ).select_related('merchant', 'merchant__user', 'category').prefetch_related('tags')

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
        ).select_related('category').prefetch_related('images', 'tags')

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

        # Get draft images owned by user
        draft_images = ImageAsset.objects.filter(
            owner=request.user,
            image_type="listing",
            is_confirmed=False,
            object_id__isnull=True
        ).order_by('-created_at')

        # Group by image_group_id
        grouped_images = {}
        for img in draft_images:
            group_id = str(img.image_group_id)
            if group_id not in grouped_images:
                grouped_images[group_id] = {
                    'image_group_id': group_id,
                    'created_at': img.created_at,
                    'variants': []
                }
            grouped_images[group_id]['variants'].append({
                'id': str(img.id),
                'variant': img.variant,
                'url': img.cdn_url(),
                'width': img.width,
                'height': img.height,
                'size_bytes': img.size_bytes
            })

        return Response(list(grouped_images.values()))

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
            # Remove image group from listing (set object_id to null and is_confirmed to False)
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

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def increment_views(self, request, pk=None):
        """Increment view count - allow anonymous tracking"""
        listing = get_object_or_404(self.get_queryset(), pk=pk)

        # Add rate limiting to prevent abuse
        cache_key = f"listing_view_{pk}_{request.META.get('REMOTE_ADDR')}"
        if cache.get(cache_key):
            return Response({'views_count': listing.views_count})

        listing.increment_views()
        cache.set(cache_key, True, 300)  # 5 min cooldown
        return Response({'views_count': listing.views_count})

    @action(detail=True, methods=['post'])
    def increment_contacts(self, request, pk=None):
        """Increment contact count for a listing"""
        listing = get_object_or_404(self.get_queryset(), pk=pk)
        listing.increment_contacts()
        return Response({'contact_count': listing.contact_count})