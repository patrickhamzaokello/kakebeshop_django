from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from .models import Listing, ListingTag, ListingImage, ListingBusinessHour


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1
    fields = ('image', 'thumbnail', 'is_primary', 'sort_order', 'image_preview')
    readonly_fields = ('image_preview',)
    ordering = ('sort_order',)

    def image_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.thumbnail)
        elif obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.image)
        return "No image"
    image_preview.short_description = "Preview"


class ListingBusinessHourInline(admin.TabularInline):
    model = ListingBusinessHour
    extra = 0
    fields = ('day', 'opens_at', 'closes_at', 'is_closed')
    ordering = ('day',)


class ListingTagInline(admin.TabularInline):
    model = ListingTag
    extra = 1
    autocomplete_fields = ('tag',)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'merchant_link',
        'listing_type',
        'status_badge',
        'price_display',
        'is_featured',
        'is_verified',
        'views_count',
        'contact_count',
        'created_at'
    )
    list_filter = (
        'status',
        'listing_type',
        'is_featured',
        'is_verified',
        'price_type',
        'category',
        'created_at',
        'updated_at'
    )
    search_fields = (
        'title',
        'description',
        'merchant__business_name',
        'merchant__email'
    )
    autocomplete_fields = ('merchant', 'category', 'location')
    readonly_fields = (
        'id',
        'views_count',
        'contact_count',
        'created_at',
        'updated_at',
        'deleted_at'
    )
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id',
                'merchant',
                'title',
                'description',
                'listing_type',
                'category',
                'location'
            )
        }),
        ('Pricing', {
            'fields': (
                'price_type',
                'price',
                'price_min',
                'price_max',
                'currency',
                'is_price_negotiable'
            )
        }),
        ('Status & Verification', {
            'fields': (
                'status',
                'rejection_reason',
                'is_verified',
                'is_featured',
                'featured_until',
                'expires_at'
            )
        }),
        ('Metrics', {
            'fields': (
                'views_count',
                'contact_count'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
                'deleted_at'
            ),
            'classes': ('collapse',)
        })
    )
    inlines = [ListingImageInline, ListingBusinessHourInline, ListingTagInline]
    date_hierarchy = 'created_at'
    list_per_page = 25
    actions = [
        'make_active',
        'make_pending',
        'make_closed',
        'mark_as_featured',
        'unmark_as_featured',
        'mark_as_verified',
        'unmark_as_verified'
    ]

    def merchant_link(self, obj):
        url = reverse('admin:merchants_merchant_change', args=[obj.merchant.id])
        return format_html('<a href="{}">{}</a>', url, obj.merchant)
    merchant_link.short_description = "Merchant"

    def status_badge(self, obj):
        colors = {
            'DRAFT': '#6c757d',
            'PENDING': '#ffc107',
            'ACTIVE': '#28a745',
            'CLOSED': '#6c757d',
            'DEACTIVATED': '#dc3545',
            'REJECTED': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def price_display(self, obj):
        if obj.price_type == 'FIXED' and obj.price:
            return f"{obj.currency} {obj.price:,.2f}"
        elif obj.price_type == 'RANGE' and obj.price_min and obj.price_max:
            return f"{obj.currency} {obj.price_min:,.2f} - {obj.price_max:,.2f}"
        elif obj.price_type == 'ON_REQUEST':
            return "On Request"
        return "-"
    price_display.short_description = "Price"

    def make_active(self, request, queryset):
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f"{updated} listing(s) marked as active.")
    make_active.short_description = "Mark selected as Active"

    def make_pending(self, request, queryset):
        updated = queryset.update(status='PENDING')
        self.message_user(request, f"{updated} listing(s) marked as pending.")
    make_pending.short_description = "Mark selected as Pending"

    def make_closed(self, request, queryset):
        updated = queryset.update(status='CLOSED')
        self.message_user(request, f"{updated} listing(s) marked as closed.")
    make_closed.short_description = "Mark selected as Closed"

    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} listing(s) marked as featured.")
    mark_as_featured.short_description = "Mark as Featured"

    def unmark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=False, featured_until=None)
        self.message_user(request, f"{updated} listing(s) unmarked as featured.")
    unmark_as_featured.short_description = "Unmark as Featured"

    def mark_as_verified(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f"{updated} listing(s) marked as verified.")
    mark_as_verified.short_description = "Mark as Verified"

    def unmark_as_verified(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f"{updated} listing(s) unmarked as verified.")
    unmark_as_verified.short_description = "Unmark as Verified"


@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ('listing_link', 'image_preview', 'is_primary', 'sort_order', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('listing__title',)
    readonly_fields = ('id', 'created_at', 'image_preview_large')
    fields = ('id', 'listing', 'image', 'thumbnail', 'image_preview_large', 'is_primary', 'sort_order', 'created_at')
    list_per_page = 50

    def listing_link(self, obj):
        url = reverse('admin:listings_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)
    listing_link.short_description = "Listing"

    def image_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.thumbnail)
        elif obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.image)
        return "No image"
    image_preview.short_description = "Preview"

    def image_preview_large(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 300px; max-width: 500px;" />', obj.image)
        return "No image"
    image_preview_large.short_description = "Image Preview"


@admin.register(ListingBusinessHour)
class ListingBusinessHourAdmin(admin.ModelAdmin):
    list_display = ('listing_link', 'day', 'opens_at', 'closes_at', 'is_closed')
    list_filter = ('day', 'is_closed')
    search_fields = ('listing__title',)
    readonly_fields = ('id', 'created_at')
    fields = ('id', 'listing', 'day', 'opens_at', 'closes_at', 'is_closed', 'created_at')

    def listing_link(self, obj):
        url = reverse('admin:listings_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)
    listing_link.short_description = "Listing"


@admin.register(ListingTag)
class ListingTagAdmin(admin.ModelAdmin):
    list_display = ('listing_link', 'tag', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('listing__title', 'tag__name')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('listing', 'tag')
    date_hierarchy = 'created_at'

    def listing_link(self, obj):
        url = reverse('admin:listings_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)
    listing_link.short_description = "Listing"