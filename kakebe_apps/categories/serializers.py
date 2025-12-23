from rest_framework import serializers
from .models import Category, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'created_at', 'slug']


class CategoryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views without nested children"""
    children_count = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True, allow_null=True)

    def get_children_count(self, obj):
        """Get children count from annotation or calculate it"""
        if hasattr(obj, 'children_count'):
            return obj.children_count
        return obj.get_children_count()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'icon', 'description', 'parent', 'parent_name',
            'children_count', 'allows_order_intent', 'allows_cart',
            'is_contact_only', 'is_featured', 'sort_order', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'slug']


class CategoryDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with nested children for detail views"""
    children = serializers.SerializerMethodField()
    parent_details = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    breadcrumbs = serializers.SerializerMethodField()

    def get_children_count(self, obj):
        """Get children count from annotation or calculate it"""
        if hasattr(obj, 'children_count'):
            return obj.children_count
        return obj.get_children_count()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'icon', 'description', 'parent',
            'parent_details', 'children', 'children_count', 'breadcrumbs',
            'allows_order_intent', 'allows_cart', 'is_contact_only',
            'is_featured', 'sort_order', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'slug']

    def get_children(self, obj):
        """Return active children without deep nesting"""
        children_qs = obj.children.filter(is_active=True).order_by('sort_order', 'name')
        return CategoryListSerializer(children_qs, many=True, context=self.context).data

    def get_parent_details(self, obj):
        """Return parent category basic info"""
        if obj.parent:
            return {
                'id': obj.parent.id,
                'name': obj.parent.name,
                'slug': obj.parent.slug,
            }
        return None

    def get_breadcrumbs(self, obj):
        """Generate breadcrumb trail for navigation"""
        breadcrumbs = []
        current = obj
        while current:
            breadcrumbs.insert(0, {
                'id': current.id,
                'name': current.name,
                'slug': current.slug
            })
            current = current.parent
        return breadcrumbs


class CategoryTreeSerializer(serializers.ModelSerializer):
    """Recursive serializer for full category tree"""
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'icon', 'children',
            'allows_order_intent', 'allows_cart', 'is_contact_only',
            'is_featured', 'sort_order'
        ]

    def get_children(self, obj):
        children_qs = obj.children.filter(is_active=True).order_by('sort_order', 'name')
        return CategoryTreeSerializer(children_qs, many=True, context=self.context).data