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
    MerchantCreateSerializer
)


class MerchantPagination(PageNumberPagination):
    """Custom pagination for merchants"""
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

    @action(detail=False, methods=['delete'], permission_classes=[permissions.IsAuthenticated])
    def delete_me(self, request):
        """Soft delete authenticated user's merchant profile"""
        merchant = get_object_or_404(Merchant, user=request.user)
        merchant.soft_delete()
        return Response(
            {'detail': 'Merchant profile deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )