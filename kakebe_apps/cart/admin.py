from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.urls import reverse
from .models import Cart, CartItem


# ========== Inline for Cart Items ==========
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('id', 'listing_link', 'quantity', 'created_at', 'updated_at')
    fields = ('listing_link', 'quantity', 'created_at')
    can_delete = False
    show_change_link = True
    verbose_name_plural = "Cart Items"

    def has_add_permission(self, request, obj=None):
        return False

    def listing_link(self, obj):
        if obj.listing:
            url = reverse('admin:listings_listing_change', args=[obj.listing.id])
            return format_html('<a href="{}">{}</a>', url, obj.listing.title)
        return "—"

    listing_link.short_description = "Listing"


# ========== Cart Item Admin ==========
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        'cart_user',
        'listing_title',
        'quantity',
        'cart_link',
        'created_at',
        'updated_at'
    )
    list_filter = (
        'created_at',
        'updated_at',
        'cart__user__name',
    )
    search_fields = (
        'listing__title',
        'cart__user__name',
        'cart__user__email'
    )
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'updated_at', 'cart_link', 'listing_link')
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'cart_link', 'listing_link', 'quantity')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def cart_user(self, obj):
        return obj.cart.user.name if obj.cart.user.name else obj.cart.user.email

    cart_user.short_description = "User"
    cart_user.admin_order_field = 'cart__user__name'

    def listing_title(self, obj):
        return obj.listing.title[:50] + "..." if len(obj.listing.title) > 50 else obj.listing.title

    listing_title.short_description = "Listing"
    listing_title.admin_order_field = 'listing__title'

    def cart_link(self, obj):
        url = reverse('admin:cart_cart_change', args=[obj.cart.id])
        return format_html('<a href="{}">Cart #{}</a>', url, str(obj.cart.id)[:8])

    cart_link.short_description = "Cart"

    def listing_link(self, obj):
        url = reverse('admin:listings_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)

    listing_link.short_description = "Listing"


# ========== Cart Admin ==========
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        'user_info',
        'items_count',
        'total_quantity',
        'created_at',
        'updated_at'
    )
    list_filter = (
        'created_at',
        'updated_at',
    )
    search_fields = (
        'user__name',
        'user__email',
        'user__phone'
    )
    list_per_page = 25
    readonly_fields = (
        'id',
        'user_link',
        'created_at',
        'updated_at',
        'items_count',
        'total_quantity',
        'items_list'
    )
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user_link')
        }),
        ('Cart Contents', {
            'fields': ('items_count', 'total_quantity', 'items_list'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    inlines = [CartItemInline]

    def user_info(self, obj):
        user = obj.user
        info = []
        if user.name:
            info.append(user.name)
        if user.email:
            info.append(f"📧 {user.email}")
        if hasattr(user, 'phone') and user.phone:
            info.append(f"📱 {user.phone}")
        return format_html('<br>'.join(info))

    user_info.short_description = "User Information"
    user_info.admin_order_field = 'user__name'

    def items_count(self, obj):
        return obj.items.count()

    items_count.short_description = "Unique Items"

    def total_quantity(self, obj):
        total = obj.items.aggregate(models.Sum('quantity'))['quantity__sum']
        return total or 0

    total_quantity.short_description = "Total Items"

    def user_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user)

    user_link.short_description = "User"

    def items_list(self, obj):
        items = []
        for item in obj.items.select_related('listing').all():
            items.append(f"• {item.listing.title} × {item.quantity}")
        return format_html('<br>'.join(items)) if items else "Empty cart"

    items_list.short_description = "Cart Items"