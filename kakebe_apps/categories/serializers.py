# kakebe_apps/categories/serializers.py

from rest_framework import serializers
from .models import Category,Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'created_at', 'slug']

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'icon', 'parent', 'children',
            'allows_order_intent', 'allows_cart', 'is_contact_only',
            'sort_order', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'slug']  # slug can be auto-generated if you want

    def get_children(self, obj):
        # Return nested children recursively (optional depth control can be added)
        children_qs = obj.children.filter(is_active=True).order_by('sort_order', 'name')
        return CategorySerializer(children_qs, many=True, context=self.context).data

    def create(self, validated_data):
        # You might want to auto-generate slug here
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)