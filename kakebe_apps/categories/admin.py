# kakebe_apps/categories/admin.py
from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Category, Tag


class ChildCategoryInline(admin.TabularInline):
    """Inline for managing child categories"""
    model = Category
    extra = 0
    fields = ['name', 'slug', 'icon', 'is_active', 'is_featured', 'sort_order']
    prepopulated_fields = {'slug': ('name',)}
    show_change_link = True
    verbose_name = "Child Category"
    verbose_name_plural = "Child Categories"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('sort_order', 'name')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Category model"""

    # List display
    list_display = [
        'name_with_hierarchy',
        'icon_display',
        'parent_link',
        'children_count_display',
        'is_featured_display',
        'is_active_display',
        'sort_order',
        'order_settings',
        'created_at_display'
    ]

    # List filters
    list_filter = [
        'is_active',
        'is_featured',
        'allows_order_intent',
        'allows_cart',
        'is_contact_only',
        'created_at',
        'updated_at',
    ]

    # Search
    search_fields = ['name', 'slug', 'description']

    # Ordering
    ordering = ['sort_order', 'name']

    # Editable fields in list view
    list_editable = ['sort_order']

    # Fields that are editable
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'icon', 'description')
        }),
        ('Hierarchy', {
            'fields': ('parent',),
            'description': 'Set the parent category to create a hierarchical structure'
        }),
        ('Display Settings', {
            'fields': ('is_featured', 'sort_order', 'is_active'),
            'description': 'Control how this category appears in listings'
        }),
        ('Ordering Options', {
            'fields': ('allows_order_intent', 'allows_cart', 'is_contact_only'),
            'description': 'Configure how products in this category can be ordered'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'System timestamps'
        }),
    )

    # Read-only fields
    readonly_fields = ['created_at', 'updated_at']

    # Prepopulate slug from name
    prepopulated_fields = {'slug': ('name',)}

    # Pagination
    list_per_page = 50

    # Add inline for child categories
    inlines = [ChildCategoryInline]

    # Enable actions
    actions = [
        'make_featured',
        'remove_featured',
        'activate_categories',
        'deactivate_categories',
        'enable_cart',
        'disable_cart',
    ]

    def get_queryset(self, request):
        """Optimize queryset with annotations"""
        qs = super().get_queryset(request)
        return qs.annotate(
            children_count=Count('children', filter=Q(children__is_active=True))
        ).select_related('parent')

    # Custom display methods
    def name_with_hierarchy(self, obj):
        """Display name with indentation for hierarchy"""
        level = 0
        current = obj
        while current.parent:
            level += 1
            current = current.parent

        indent = '—' * level
        return format_html(
            '{} <strong>{}</strong>',
            indent,
            obj.name
        )

    name_with_hierarchy.short_description = 'Category Name'
    name_with_hierarchy.admin_order_field = 'name'

    def icon_display(self, obj):
        """Display icon with preview"""
        if obj.icon:
            if obj.icon.startswith('http'):
                # If it's a URL, show image
                return format_html(
                    '<img src="{}" width="30" height="30" style="border-radius: 4px;" /> {}',
                    obj.icon,
                    obj.icon[:20] + '...' if len(obj.icon) > 20 else obj.icon
                )
            else:
                # If it's an icon class/name
                return format_html(
                    '<span style="font-size: 20px; margin-right: 5px;">📦</span> {}',
                    obj.icon
                )
        return '-'

    icon_display.short_description = 'Icon'

    def parent_link(self, obj):
        """Display parent with clickable link"""
        if obj.parent:
            url = reverse('admin:categories_category_change', args=[obj.parent.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.parent.name
            )
        return format_html('<span style="color: #999;">Root Category</span>')

    parent_link.short_description = 'Parent'
    parent_link.admin_order_field = 'parent__name'

    def children_count_display(self, obj):
        """Display number of active children with link"""
        count = obj.children_count
        if count > 0:
            url = reverse('admin:categories_category_changelist')
            return format_html(
                '<a href="{}?parent__id__exact={}" style="color: #417690; font-weight: bold;">{} child{}</a>',
                url,
                obj.pk,
                count,
                'ren' if count != 1 else ''
            )
        return format_html('<span style="color: #999;">0</span>')

    children_count_display.short_description = 'Children'
    children_count_display.admin_order_field = 'children_count'

    def is_featured_display(self, obj):
        """Display featured status with icon"""
        if obj.is_featured:
            return format_html(
                '<span style="color: #ffc107; font-size: 18px;" title="Featured">⭐</span>'
            )
        return format_html('<span style="color: #ccc;">☆</span>')

    is_featured_display.short_description = 'Featured'
    is_featured_display.admin_order_field = 'is_featured'

    def is_active_display(self, obj):
        """Display active status with colored badge"""
        if obj.is_active:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">ACTIVE</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">INACTIVE</span>'
        )

    is_active_display.short_description = 'Status'
    is_active_display.admin_order_field = 'is_active'

    def order_settings(self, obj):
        """Display order settings as badges"""
        badges = []
        if obj.allows_order_intent:
            badges.append('<span style="background: #007bff; color: white; padding: 2px 6px; '
                          'border-radius: 3px; font-size: 10px; margin-right: 3px;">INTENT</span>')
        if obj.allows_cart:
            badges.append('<span style="background: #17a2b8; color: white; padding: 2px 6px; '
                          'border-radius: 3px; font-size: 10px; margin-right: 3px;">CART</span>')
        if obj.is_contact_only:
            badges.append('<span style="background: #6c757d; color: white; padding: 2px 6px; '
                          'border-radius: 3px; font-size: 10px;">CONTACT</span>')
        return format_html(''.join(badges)) if badges else '-'

    order_settings.short_description = 'Order Options'

    def created_at_display(self, obj):
        """Display formatted creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')

    created_at_display.short_description = 'Created'
    created_at_display.admin_order_field = 'created_at'

    # Admin actions
    @admin.action(description='Mark selected categories as featured')
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} categor{"y" if updated == 1 else "ies"} marked as featured.')

    @admin.action(description='Remove featured status from selected categories')
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} categor{"y" if updated == 1 else "ies"} removed from featured.')

    @admin.action(description='Activate selected categories')
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} categor{"y" if updated == 1 else "ies"} activated.')

    @admin.action(description='Deactivate selected categories')
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} categor{"y" if updated == 1 else "ies"} deactivated.')

    @admin.action(description='Enable cart for selected categories')
    def enable_cart(self, request, queryset):
        updated = queryset.update(allows_cart=True)
        self.message_user(request, f'Cart enabled for {updated} categor{"y" if updated == 1 else "ies"}.')

    @admin.action(description='Disable cart for selected categories')
    def disable_cart(self, request, queryset):
        updated = queryset.update(allows_cart=False)
        self.message_user(request, f'Cart disabled for {updated} categor{"y" if updated == 1 else "ies"}.')

    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        super().save_model(request, obj, form, change)

        # Log message
        if change:
            self.message_user(request, f'Category "{obj.name}" updated successfully.')
        else:
            self.message_user(request, f'Category "{obj.name}" created successfully.')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Tag model"""

    # List display
    list_display = [
        'name_display',
        'slug',
        'created_at_display',
        'usage_count'
    ]

    # Search
    search_fields = ['name', 'slug']

    # Ordering
    ordering = ['name']

    # Prepopulate slug
    prepopulated_fields = {'slug': ('name',)}

    # Fields configuration
    fields = ['name', 'slug', 'created_at']
    readonly_fields = ['created_at']

    # Pagination
    list_per_page = 50

    # Custom display methods
    def name_display(self, obj):
        """Display name with tag icon"""
        return format_html(
            '<span style="background: #e9ecef; padding: 4px 10px; border-radius: 12px; '
            'font-size: 12px; font-weight: 500;">🏷️ {}</span>',
            obj.name
        )

    name_display.short_description = 'Tag Name'
    name_display.admin_order_field = 'name'

    def created_at_display(self, obj):
        """Display formatted creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')

    created_at_display.short_description = 'Created'
    created_at_display.admin_order_field = 'created_at'

    def usage_count(self, obj):
        """Display usage count (placeholder - implement based on your product model)"""
        # TODO: Add actual count based on your product-tag relationship
        # Example: count = obj.products.count()
        return format_html('<span style="color: #999;">N/A</span>')

    usage_count.short_description = 'Usage'


# Optional: Custom admin site configuration
admin.site.site_header = "Kakebe Admin"
admin.site.site_title = "Kakebe Admin Portal"
admin.site.index_title = "Welcome to Kakebe Administration"