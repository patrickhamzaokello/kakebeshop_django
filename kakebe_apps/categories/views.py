from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from .models import Category, Tag
from .serializers import (
    CategoryListSerializer,
    CategoryDetailSerializer,
    CategoryTreeSerializer,
    TagSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Enhanced category viewset with multiple endpoints:
    - list: paginated list of all active categories
    - retrieve: detailed view with children and breadcrumbs
    - featured: get featured parent categories
    - tree: hierarchical tree structure
    - subcategories: paginated subcategories of a parent
    """
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'sort_order', 'created_at']
    ordering = ['sort_order', 'name']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Base queryset with optimizations"""
        queryset = Category.objects.filter(is_active=True).annotate(
            children_count=Count('children', filter=Q(children__is_active=True))
        ).select_related('parent').prefetch_related('children')

        # Filter by parent if provided
        parent_id = self.request.query_params.get('parent_id', None)
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)

        # Filter top-level only
        if self.request.query_params.get('top_level', '').lower() == 'true':
            queryset = queryset.filter(parent=None)

        # Filter featured only
        if self.request.query_params.get('featured', '').lower() == 'true':
            queryset = queryset.filter(is_featured=True)

        return queryset

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'retrieve':
            return CategoryDetailSerializer
        elif self.action == 'tree':
            return CategoryTreeSerializer
        return CategoryListSerializer

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        Get featured parent categories (no pagination, sorted by sort_order)
        Query: /api/categories/featured/
        """
        categories = self.get_queryset().filter(
            is_featured=True,
            parent=None
        ).order_by('sort_order', 'name')

        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """
        Get complete category tree (top-level with nested children)
        Query: /api/categories/tree/
        Warning: This can be heavy for large datasets
        """
        categories = Category.objects.filter(
            is_active=True,
            parent=None
        ).prefetch_related('children').order_by('sort_order', 'name')

        serializer = CategoryTreeSerializer(categories, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def subcategories(self, request, slug=None):
        """
        Get paginated subcategories of a specific parent category
        Query: /api/categories/{id}/subcategories/
        Supports pagination, search, and ordering
        """
        parent = self.get_object()

        queryset = Category.objects.filter(
            is_active=True,
            parent=parent
        ).annotate(
            children_count=Count('children', filter=Q(children__is_active=True))
        ).order_by('sort_order', 'name')

        # Apply search if provided
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)

        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CategoryListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CategoryListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def parents(self, request):
        """
        Get all parent categories (categories without a parent)
        Query: /api/categories/parents/
        Supports pagination and search
        """
        queryset = self.get_queryset().filter(parent=None)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for tags with pagination and search
    """
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'slug']
    pagination_class = StandardResultsSetPagination