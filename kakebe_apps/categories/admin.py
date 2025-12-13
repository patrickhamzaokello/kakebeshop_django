from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Tag


# ========== Inline for Category Children ==========
class CategoryChildrenInline(admin.TabularInline):
    model = Category
    fk_name = 'parent'
    extra = 0
    fields = ('name', 'slug', 'sort_order', 'is_active')
    readonly_fields = ('name', 'slug', 'sort_order', 'is_active')
    can_delete = False
    show_change_link = True
    verbose_name_plural = "Subcategories"

    def has_add_permission(self, request, obj=None):
        return False


# ========== Category Admin ==========
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'parent_link',
        'slug',
        'is_active',
        'sort_order',
        'flags_display',
        'created_at'
    )
    list_filter = (
        'is_active',
        'parent',
        'allows_order_intent',
        'allows_cart',
        'is_contact_only',
        'created_at'
    )
    search_fields = ('name', 'slug', 'icon')
    list_editable = ('sort_order', 'is_active')
    list_per_page = 25
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('id', 'created_at', 'children_count')
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'slug', 'icon', 'parent', 'sort_order')
        }),
        ('Flags', {
            'fields': (
                'allows_order_intent',
                'allows_cart',
                'is_contact_only',
                'is_active'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('children_count', 'created_at'),
            'classes': ('collapse',)
        })
    )
    inlines = [CategoryChildrenInline]

    def parent_link(self, obj):
        if obj.parent:
            url = f"/admin/categories/category/{obj.parent.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.parent.name)
        return "—"

    parent_link.short_description = "Parent"
    parent_link.admin_order_field = 'parent__name'

    def children_count(self, obj):
        return obj.children.count()

    children_count.short_description = "Subcategories"

    def flags_display(self, obj):
        flags = []
        if obj.allows_order_intent:
            flags.append('📋')
        if obj.allows_cart:
            flags.append('🛒')
        if obj.is_contact_only:
            flags.append('📞')
        return format_html('<span style="font-size: 1.2em;">{}</span>', ' '.join(flags)) if flags else "—"

    flags_display.short_description = "Flags"
    flags_display.short_description = "Flags"


# ========== Tag Admin ==========
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at', 'item_count')
    list_filter = ('created_at',)
    search_fields = ('name', 'slug')
    list_per_page = 25
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'slug')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset

    def item_count(self, obj):
        # Assuming you'll have a model that uses tags (like Product or Item)
        # Replace 'item_set' with the actual related name if different
        try:
            return obj.item_set.count()
        except AttributeError:
            return 0

    item_count.short_description = "Used in"