from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from .models import Category, Tag
from .serializers import (
    CategoryListSerializer,
    CategoryDetailSerializer,
    CategoryTreeSerializer,
    CategoryCreateSerializer,
    CategoryUpdateSerializer,
    TagSerializer,
    TagCreateSerializer,
)
from ..listings.models import Listing
from ..listings.serializers import ListingListSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission:
    - Read access for everyone
    - Write access only for staff/admin users
    """

    def has_permission(self, request, view):
        # Allow read operations for everyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write operations only for authenticated staff
        return request.user and request.user.is_authenticated and request.user.is_staff


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Enhanced category viewset with CRUD operations:

    Public endpoints (GET):
    - list: GET /categories/ - Paginated list of all active categories
    - retrieve: GET /categories/{id}/ - Detailed view with children and breadcrumbs
    - featured: GET /categories/featured/ - Featured parent categories
    - tree: GET /categories/tree/ - Hierarchical tree structure
    - subcategories: GET /categories/{id}/subcategories/ - Up to 14 subcategories
    - listings: GET /categories/{id}/listings/ - All listings in category
    - details: GET /categories/{id}/details/ - Category details
    - parents: GET /categories/parents/ - All parent categories

    Admin endpoints (POST/PATCH/DELETE) - requires staff authentication:
    - create: POST /categories/ - Create new category
    - update: PATCH /categories/{id}/ - Update category
    - partial_update: PATCH /categories/{id}/ - Partial update
    - destroy: DELETE /categories/{id}/ - Delete category
    """
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'id'  # Changed from 'slug' to 'id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'sort_order', 'created_at']
    ordering = ['sort_order', 'name']
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Base queryset with optimizations"""
        # For admin users, show all categories
        if self.request.user and self.request.user.is_staff:
            queryset = Category.objects.all()
        else:
            # For regular users, only show active categories
            queryset = Category.objects.filter(is_active=True)

        queryset = queryset.annotate(
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
        if self.action == 'create':
            return CategoryCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CategoryUpdateSerializer
        elif self.action == 'retrieve':
            return CategoryDetailSerializer
        elif self.action == 'tree':
            return CategoryTreeSerializer
        return CategoryListSerializer

    def create(self, request, *args, **kwargs):
        """Create a new category (admin only)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()

        return Response(
            CategoryDetailSerializer(category, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Update a category (admin only)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()

        return Response(
            CategoryDetailSerializer(category, context={'request': request}).data
        )

    def destroy(self, request, *args, **kwargs):
        """
        Delete a category (admin only)
        Note: This will cascade delete all subcategories and their associations
        """
        instance = self.get_object()

        # Check if category has children
        children_count = instance.children.count()
        if children_count > 0:
            return Response(
                {
                    'error': f'Cannot delete category with {children_count} subcategories. '
                             'Delete or reassign subcategories first.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if category has listings
        listings_count = instance.listings.count()
        if listings_count > 0:
            return Response(
                {
                    'error': f'Cannot delete category with {listings_count} listings. '
                             'Reassign or delete listings first.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.delete()
        return Response(
            {'message': 'Category deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        Get featured parent categories (no pagination, sorted by sort_order)
        Query: GET /categories/featured/
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
        Query: GET /categories/tree/
        Warning: This can be heavy for large datasets
        """
        categories = Category.objects.filter(
            is_active=True,
            parent=None
        ).prefetch_related('children').order_by('sort_order', 'name')

        serializer = CategoryTreeSerializer(categories, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def subcategories(self, request, id=None):
        """
        Get up to 14 subcategories of a specific category
        Query: GET /categories/{id}/subcategories/
        """
        category = self.get_object()

        subcategories = Category.objects.filter(
            is_active=True,
            parent=category
        ).annotate(
            children_count=Count('children', filter=Q(children__is_active=True))
        ).order_by('sort_order', 'name')[:14]

        serializer = CategoryListSerializer(subcategories, many=True, context={'request': request})
        return Response({
            'category_id': str(category.id),
            'category_name': category.name,
            'subcategories': serializer.data,
            'total_count': len(subcategories)
        })

    @action(detail=True, methods=['get'])
    def listings(self, request, id=None):
        """
        Get all listings for a specific category (paginated)
        Query: GET /categories/{id}/listings/
        Optional params: ?page=1&page_size=20&search=query
        """
        category = self.get_object()

        # Get listings for this category
        listings_qs = Listing.objects.filter(
            category=category,
            is_active=True
        ).select_related('merchant', 'category').order_by('-created_at')

        # Apply search if provided
        search = request.query_params.get('search', None)
        if search:
            listings_qs = listings_qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        # Paginate
        page = self.paginate_queryset(listings_qs)
        if page is not None:
            serializer = ListingListSerializer(page, many=True, context={'request': request})
            response_data = self.get_paginated_response(serializer.data).data
            response_data['category_id'] = str(category.id)
            response_data['category_name'] = category.name
            return Response(response_data)

        serializer = ListingListSerializer(listings_qs, many=True, context={'request': request})
        return Response({
            'category_id': str(category.id),
            'category_name': category.name,
            'listings': serializer.data,
            'total_count': listings_qs.count()
        })

    @action(detail=True, methods=['get'])
    def details(self, request, id=None):
        """
        Get category details (name, description, etc.)
        Query: GET /categories/{id}/details/
        """
        category = self.get_object()

        return Response({
            'id': str(category.id),
            'name': category.name,
            'slug': category.slug,
            'icon': category.icon,
            'description': category.description,
            'parent_id': str(category.parent.id) if category.parent else None,
            'parent_name': category.parent.name if category.parent else None,
            'allows_order_intent': category.allows_order_intent,
            'allows_cart': category.allows_cart,
            'is_contact_only': category.is_contact_only,
            'is_featured': category.is_featured,
            'sort_order': category.sort_order,
            'is_active': category.is_active,
            'children_count': category.children.filter(is_active=True).count(),
            'created_at': category.created_at,
            'updated_at': category.updated_at
        })

    @action(detail=False, methods=['get'])
    def parents(self, request):
        """
        Get all parent categories (categories without a parent)
        Query: GET /categories/parents/
        Supports pagination and search
        """
        queryset = self.get_queryset().filter(parent=None)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TagViewSet(viewsets.ModelViewSet):
    """
    Tag viewset with CRUD operations:

    Public endpoints (GET):
    - list: GET /tags/ - Paginated list of all tags
    - retrieve: GET /tags/{id}/ - Single tag details

    Admin endpoints (POST/PATCH/DELETE) - requires staff authentication:
    - create: POST /tags/ - Create new tag
    - update: PATCH /tags/{id}/ - Update tag
    - partial_update: PATCH /tags/{id}/ - Partial update
    - destroy: DELETE /tags/{id}/ - Delete tag
    """
    queryset = Tag.objects.all().order_by('name')
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'id'  # Changed from 'slug' to 'id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'slug']
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return TagCreateSerializer
        return TagSerializer

    def create(self, request, *args, **kwargs):
        """Create a new tag (admin only)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tag = serializer.save()

        return Response(
            TagSerializer(tag, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Update a tag (admin only)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Only allow updating the name
        if 'name' not in request.data:
            return Response(
                {'error': 'Name field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if new name already exists
        new_name = request.data['name']
        if Tag.objects.filter(name__iexact=new_name).exclude(id=instance.id).exists():
            return Response(
                {'error': f"Tag '{new_name}' already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.name = new_name
        instance.save()

        return Response(
            TagSerializer(instance, context={'request': request}).data
        )

    def destroy(self, request, *args, **kwargs):
        """
        Delete a tag (admin only)
        Note: This will remove the tag from all listings that use it
        """
        instance = self.get_object()

        # Check if tag is used by listings
        listings_count = instance.listings.count()
        if listings_count > 0:
            return Response(
                {
                    'error': f'Cannot delete tag used by {listings_count} listings. '
                             'Remove tag from listings first or force delete.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.delete()
        return Response(
            {'message': 'Tag deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def bulk_create(self, request):
        """
        Bulk create tags from a list of names
        POST /tags/bulk_create/
        Body: {"names": ["tag1", "tag2", "tag3"]}
        """
        names = request.data.get('names', [])

        if not isinstance(names, list):
            return Response(
                {'error': 'names must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not names:
            return Response(
                {'error': 'names list cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_tags = []
        existing_tags = []
        errors = []

        for name in names:
            name = name.strip()
            if not name:
                continue

            # Check if tag already exists
            if Tag.objects.filter(name__iexact=name).exists():
                existing_tags.append(name)
                continue

            try:
                tag = Tag.objects.create(name=name)
                created_tags.append(TagSerializer(tag).data)
            except Exception as e:
                errors.append({'name': name, 'error': str(e)})

        return Response({
            'created': created_tags,
            'existing': existing_tags,
            'errors': errors,
            'summary': {
                'created_count': len(created_tags),
                'existing_count': len(existing_tags),
                'error_count': len(errors)
            }
        }, status=status.HTTP_201_CREATED if created_tags else status.HTTP_200_OK)