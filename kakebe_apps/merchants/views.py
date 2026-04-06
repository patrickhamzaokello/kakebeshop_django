# kakebe_apps/merchants/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Merchant
from .serializers import (
    MerchantListSerializer,
    MerchantDetailSerializer,
    MerchantUpdateSerializer,
    MerchantCreateSerializer,
    MerchantImageUpdateSerializer
)


class MerchantPagination(PageNumberPagination):
    """Custom pagination for merchants"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ListingPagination(PageNumberPagination):
    """Custom pagination for merchant listings"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsMerchantOwner(permissions.BasePermission):
    """Custom permission: only the owner can edit their merchant profile"""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class MerchantViewSet(viewsets.ViewSet):
    """
    ViewSet for merchant operations:

    Public endpoints:
    - list: GET /merchants/ - Paginated list of verified, active merchants
    - retrieve: GET /merchants/{id}/ - Public merchant profile
    - featured: GET /merchants/featured/ - Shuffled featured merchants
    - listings: GET /merchants/{id}/listings/ - Paginated active listings for a merchant

    Authenticated endpoints:
    - me: GET /merchants/me/ - Get own merchant profile
    - update_me: PATCH /merchants/me/ - Update own merchant profile
    - create_profile: POST /merchants/create/ - Create merchant profile
    """

    pagination_class = MerchantPagination

    def get_queryset(self):
        """Base queryset for verified, active merchants only"""
        return Merchant.objects.filter(
            status='ACTIVE',
            verified=True,
            deleted_at__isnull=True
        ).select_related('user')

    def list(self, request):
        """List verified and active merchants with filtering and search"""
        queryset = self.get_queryset()

        # Search functionality
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(display_name__icontains=search) |
                Q(business_name__icontains=search) |
                Q(description__icontains=search)
            )

        # Filter by minimum rating
        min_rating = request.query_params.get('min_rating', None)
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=float(min_rating))
            except ValueError:
                pass

        # Filter by location
        location_id = request.query_params.get('location', None)
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        # Sorting
        sort_by = request.query_params.get('sort_by', '-rating')
        valid_sort_fields = ['rating', '-rating', 'display_name',
                             '-display_name', 'created_at', '-created_at']
        if sort_by in valid_sort_fields:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-rating', 'display_name')

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = MerchantListSerializer(
                page, many=True, context={'request': request}
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = MerchantListSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Retrieve single merchant profile (must be verified and active)"""
        merchant = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = MerchantDetailSerializer(merchant, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='featured')
    def featured(self, request):
        """
        Get featured merchants in shuffled order.
        Query params:
        - limit: Number of merchants to return (default: 10, max: 50)
        """
        limit = request.query_params.get('limit', 10)
        try:
            limit = min(int(limit), 50)  # Cap at 50
        except ValueError:
            limit = 10

        # Get featured, verified, and active merchants in random order
        queryset = self.get_queryset().filter(featured=True).order_by('?')[:limit]

        serializer = MerchantListSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='listings')
    def listings(self, request, pk=None):
        """
        Get paginated active listings for a specific merchant.

        Only returns listings with status='ACTIVE' and is_verified=True.
        The merchant itself must also be verified and active.

        Query params:
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20, max: 100)
        - listing_type: Filter by type - 'PRODUCT' or 'SERVICE'
        - sort_by: One of 'created_at', '-created_at', 'price', '-price',
                   'views_count', '-views_count' (default: '-created_at')
        """
        # Ensure the merchant exists and is publicly visible
        merchant = get_object_or_404(self.get_queryset(), pk=pk)

        # Import here to avoid circular imports
        from kakebe_apps.listings.models import Listing
        from kakebe_apps.listings.serializers import ListingListSerializer

        queryset = Listing.objects.filter(
            merchant=merchant,
            status='ACTIVE',
            is_verified=True,
            deleted_at__isnull=True
        ).select_related('merchant', 'category')

        # Filter by listing type
        listing_type = request.query_params.get('listing_type', None)
        if listing_type and listing_type in ('PRODUCT', 'SERVICE'):
            queryset = queryset.filter(listing_type=listing_type)

        # Sorting
        sort_by = request.query_params.get('sort_by', '-created_at')
        valid_sort_fields = [
            'created_at', '-created_at',
            'price', '-price',
            'views_count', '-views_count',
        ]
        if sort_by in valid_sort_fields:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-created_at')

        # Apply pagination
        paginator = ListingPagination()
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

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Get authenticated user's merchant profile (regardless of verification status)"""
        try:
            # Allow user to see their own profile even if not verified
            merchant = Merchant.objects.get(user=request.user)
            serializer = MerchantDetailSerializer(merchant, context={'request': request})
            return Response(serializer.data)
        except Merchant.DoesNotExist:
            return Response(
                {'detail': 'You do not have a merchant profile.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @me.mapping.patch
    def update_me(self, request):
        """Update authenticated user's merchant profile"""
        merchant = get_object_or_404(Merchant, user=request.user)
        serializer = MerchantUpdateSerializer(
            merchant,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return full detail serializer
        return Response(
            MerchantDetailSerializer(merchant, context={'request': request}).data
        )

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def create_profile(self, request):
        """Create a merchant profile for authenticated user (starts unverified)"""
        serializer = MerchantCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        merchant = serializer.save()

        return Response(
            MerchantDetailSerializer(merchant, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='me/orders')
    def me_orders(self, request):
        """
        Get orders for the authenticated merchant's profile.

        Query params:
        - status: Filter by order status (NEW, CONTACTED, CONFIRMED, COMPLETED, CANCELLED)
        - page / page_size: Pagination
        """
        merchant = get_object_or_404(Merchant, user=request.user)

        from kakebe_apps.orders.models import OrderIntent
        from kakebe_apps.orders.serializers import OrderIntentSerializer

        queryset = OrderIntent.objects.filter(
            merchant=merchant
        ).select_related(
            'buyer', 'merchant', 'address', 'order_group'
        ).prefetch_related('items__listing').order_by('-created_at')

        order_status = request.query_params.get('status')
        if order_status:
            queryset = queryset.filter(status=order_status.upper())

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = OrderIntentSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = OrderIntentSerializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='me/update-logo')
    def update_logo(self, request):
        """
        Set merchant logo from a previously uploaded image group.

        Expects a confirmed 'profile' image uploaded via the standard
        presign → upload → confirm flow.

        Body: { "image_group_id": "<uuid>" }
        """
        merchant = get_object_or_404(Merchant, user=request.user)

        serializer = MerchantImageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image_group_id = serializer.validated_data['image_group_id']

        from kakebe_apps.imagehandler.models import ImageAsset

        assets = ImageAsset.objects.filter(
            image_group_id=image_group_id,
            owner=request.user,
            image_type='profile',
            is_confirmed=True
        )
        if not assets.exists():
            return Response(
                {'detail': 'No confirmed profile image found for this image_group_id.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Attach assets to this merchant
        assets.update(object_id=merchant.id)

        # Prefer medium variant for the logo URL, fall back to thumb
        asset = assets.filter(variant='medium').first() or assets.first()
        merchant.logo = asset.cdn_url()
        merchant.save(update_fields=['logo', 'updated_at'])

        return Response(MerchantDetailSerializer(merchant, context={'request': request}).data)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='me/update-cover-image')
    def update_cover_image(self, request):
        """
        Set merchant cover image from a previously uploaded image group.

        Expects a confirmed 'store_banner' image uploaded via the standard
        presign → upload → confirm flow.

        Body: { "image_group_id": "<uuid>" }
        """
        merchant = get_object_or_404(Merchant, user=request.user)

        serializer = MerchantImageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image_group_id = serializer.validated_data['image_group_id']

        from kakebe_apps.imagehandler.models import ImageAsset

        assets = ImageAsset.objects.filter(
            image_group_id=image_group_id,
            owner=request.user,
            image_type='store_banner',
            is_confirmed=True
        )
        if not assets.exists():
            return Response(
                {'detail': 'No confirmed store_banner image found for this image_group_id.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Attach assets to this merchant
        assets.update(object_id=merchant.id)

        # store_banner only has a large variant
        asset = assets.filter(variant='large').first() or assets.first()
        merchant.cover_image = asset.cdn_url()
        merchant.save(update_fields=['cover_image', 'updated_at'])

        return Response(MerchantDetailSerializer(merchant, context={'request': request}).data)

    @action(detail=False, methods=['delete'], permission_classes=[permissions.IsAuthenticated])
    def delete_me(self, request):
        """Soft delete authenticated user's merchant profile"""
        merchant = get_object_or_404(Merchant, user=request.user)
        merchant.soft_delete()
        return Response(
            {'detail': 'Merchant profile deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )