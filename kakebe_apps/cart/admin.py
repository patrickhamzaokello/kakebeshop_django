from django.contrib import admin
from .models import Cart, CartItem, Wishlist, WishlistItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('created_at', 'updated_at', 'subtotal')
    fields = ('listing', 'quantity', 'subtotal', 'created_at', 'updated_at')
    raw_id_fields = ('listing',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_items', 'total_price', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'user__name', 'id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'total_items', 'total_price')
    inlines = [CartItemInline]
    raw_id_fields = ('user',)

    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Total Items'

    def total_price(self, obj):
        return f"${obj.total_price:.2f}"
    total_price.short_description = 'Total Price'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart_user', 'listing', 'quantity', 'subtotal', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('cart__user__email', 'listing__title', 'id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'subtotal')
    raw_id_fields = ('cart', 'listing')

    def cart_user(self, obj):
        return obj.cart.user.email
    cart_user.short_description = 'User'

    def subtotal(self, obj):
        return f"${obj.subtotal:.2f}"
    subtotal.short_description = 'Subtotal'


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('listing', 'created_at')
    raw_id_fields = ('listing',)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_items', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'user__name', 'id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'total_items')
    inlines = [WishlistItemInline]
    raw_id_fields = ('user',)

    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Total Items'


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'wishlist_user', 'listing', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('wishlist__user__email', 'listing__title', 'id')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('wishlist', 'listing')

    def wishlist_user(self, obj):
        return obj.wishlist.user.email
    wishlist_user.short_description = 'User'