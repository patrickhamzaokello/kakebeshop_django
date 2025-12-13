# kakebe_apps/categories/views.py
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions
from .models import Category, Tag
from .serializers import CategorySerializer, TagSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for categories.
    - list: returns top-level active categories with nested children
    - retrieve: detailed view of a single category
    """
    queryset = Category.objects.filter(is_active=True, parent=None).order_by('sort_order', 'name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]  # Public access
    lookup_field = 'slug'  # Allow lookup by slug instead of UUID for cleaner URLs

    def get_queryset(self):
        """
        Allow retrieving all categories (including inactive) for admin purposes
        if needed, but default is active top-level.
        """
        if self.action == 'retrieve':
            return Category.objects.filter(is_active=True)
        return super().get_queryset()

class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for tags.
    Supports search by name.
    """
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'slug']