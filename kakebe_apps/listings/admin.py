# kakebe_apps/listings/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Listing, ListingTag, ListingBusinessHour


class ListingBusinessHourInline(admin.TabularInline):
    model = ListingBusinessHour
    extra = 0
    fields = ['day', 'opens_at', 'closes_at', 'is_closed']


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'merchant', 'listing_type', 'category','status',
        'status_display', 'verified_display', 'featured_display',
        'price_display', 'views_count', 'created_at'
    ]
    list_filter = [
        'listing_type', 'status', 'is_verified', 'is_featured',
        'category', 'created_at'
    ]
    search_fields = [
        'title', 'description', 'merchant__display_name',
        'merchant__user__username'
    ]
    readonly_fields = [
        'id', 'views_count', 'contact_count',
        'created_at', 'updated_at', 'deleted_at'
    ]
    list_editable = ['status']
    inlines = [ListingBusinessHourInline]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id', 'merchant', 'title', 'description',
                'listing_type', 'category'
            )
        }),
        ('Pricing', {
            'fields': (
                'price_type', 'price', 'price_min', 'price_max',
                'currency', 'is_price_negotiable'
            )
        }),
        ('Status & Verification', {
            'fields': (
                'status', 'rejection_reason', 'is_verified', 'verified_at'
            )
        }),
        ('Featured Settings', {
            'fields': (
                'is_featured', 'featured_until', 'featured_order'
            ),
            'description': 'Featured listings appear on the homepage. Lower order numbers appear first.'
        }),
        ('Engagement Metrics', {
            'fields': ('views_count', 'contact_count')
        }),
        ('Additional Info', {
            'fields': ('metadata', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )

    def status_display(self, obj):
        colors = {
            'DRAFT': 'gray',
            'PENDING': 'orange',
            'ACTIVE': 'green',
            'CLOSED': 'red',
            'DEACTIVATED': 'gray',
            'REJECTED': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_display.short_description = 'Status'

    def verified_display(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: orange;">⏳ Pending Verification</span>'
        )

    verified_display.short_description = 'Verification'

    def featured_display(self, obj):
        if obj.is_featured:
            if obj.featured_until and obj.featured_until < timezone.now():
                return format_html(
                    '<span style="color: gray;">⭐ Expired</span>'
                )
            return format_html(
                '<span style="color: gold;">⭐ Featured (Order: {})</span>',
                obj.featured_order
            )
        return format_html(
            '<span style="color: gray;">Not Featured</span>'
        )

    featured_display.short_description = 'Featured Status'

    def price_display(self, obj):
        if obj.price_type == 'FIXED' and obj.price:
            return f"{obj.currency} {obj.price:,.2f}"
        elif obj.price_type == 'RANGE' and obj.price_min and obj.price_max:
            return f"{obj.currency} {obj.price_min:,.2f} - {obj.price_max:,.2f}"
        elif obj.price_type == 'ON_REQUEST':
            return "On Request"
        return "N/A"

    price_display.short_description = 'Price'

    actions = [
        'verify_listings',
        'unverify_listings',
        'approve_listings',
        'reject_listings',
        'feature_listings',
        'unfeature_listings',
        'close_listings'
    ]

    def verify_listings(self, request, queryset):
        """Verify selected listings"""
        updated = queryset.update(
            is_verified=True,
            verified_at=timezone.now()
        )
        self.message_user(
            request,
            f'{updated} listing(s) verified successfully.',
            level='SUCCESS'
        )

    verify_listings.short_description = 'Verify selected listings'

    def unverify_listings(self, request, queryset):
        """Remove verification from selected listings"""
        updated = queryset.update(is_verified=False, verified_at=None)
        self.message_user(
            request,
            f'{updated} listing(s) unverified.',
            level='WARNING'
        )

    unverify_listings.short_description = 'Unverify selected listings'

    def approve_listings(self, request, queryset):
        """Approve and activate listings"""
        updated = queryset.filter(
            status__in=['PENDING', 'DRAFT']
        ).update(
            status='ACTIVE',
            is_verified=True,
            verified_at=timezone.now()
        )
        self.message_user(
            request,
            f'{updated} listing(s) approved and activated.',
            level='SUCCESS'
        )

    approve_listings.short_description = 'Approve and activate listings'

    def reject_listings(self, request, queryset):
        """Reject selected listings"""
        updated = queryset.update(
            status='REJECTED',
            is_verified=False
        )
        self.message_user(
            request,
            f'{updated} listing(s) rejected. Please add rejection reasons manually.',
            level='WARNING'
        )

    reject_listings.short_description = 'Reject selected listings'

    def feature_listings(self, request, queryset):
        """Mark selected listings as featured"""
        updated = 0
        for listing in queryset.filter(is_verified=True, status='ACTIVE'):
            if not listing.is_featured:
                listing.is_featured = True
                listing.save(update_fields=['is_featured'])
                updated += 1

        self.message_user(
            request,
            f'{updated} listing(s) marked as featured.',
            level='SUCCESS'
        )

    feature_listings.short_description = 'Mark as featured'

    def unfeature_listings(self, request, queryset):
        """Remove featured status from selected listings"""
        updated = queryset.filter(is_featured=True).update(
            is_featured=False,
            featured_order=0
        )
        self.message_user(
            request,
            f'{updated} listing(s) removed from featured.',
            level='INFO'
        )

    unfeature_listings.short_description = 'Remove from featured'

    def close_listings(self, request, queryset):
        """Close selected listings"""
        updated = queryset.update(status='CLOSED')
        self.message_user(
            request,
            f'{updated} listing(s) closed.',
            level='INFO'
        )

    close_listings.short_description = 'Close selected listings'



@admin.register(ListingBusinessHour)
class ListingBusinessHourAdmin(admin.ModelAdmin):
    list_display = ['listing', 'day', 'opens_at', 'closes_at', 'is_closed']
    list_filter = ['day', 'is_closed']
    search_fields = ['listing__title']
    readonly_fields = ['id', 'created_at']


@admin.register(ListingTag)
class ListingTagAdmin(admin.ModelAdmin):
    list_display = ['listing', 'tag', 'created_at']
    list_filter = ['created_at']
    search_fields = ['listing__title', 'tag__name']
    readonly_fields = ['created_at']