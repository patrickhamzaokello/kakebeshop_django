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
        'quality_status', 'is_home_feed_eligible', 'feed_rank_boost',
        'is_home_feed_pinned', 'price_display', 'views_count', 'created_at'
    ]
    list_filter = [
        ('merchant', admin.RelatedOnlyFieldListFilter),
        'listing_type', 'status', 'is_verified', 'is_featured',
        'quality_status', 'is_home_feed_eligible', 'is_home_feed_pinned',
        'merchant__verified', 'category', 'price_type',
        'available_from', 'available_until', 'created_at'
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
        ('Home Feed Quality', {
            'fields': (
                'is_home_feed_eligible', 'quality_status',
                'quality_score', 'quality_rejection_reason'
            )
        }),
        ('Home Feed Ranking', {
            'fields': (
                'feed_rank_boost', 'feed_boost_until', 'feed_boost_reason',
                'is_home_feed_pinned', 'home_feed_pin_position',
                'home_feed_pin_until'
            )
        }),
        ('Engagement Metrics', {
            'fields': ('views_count', 'contact_count')
        }),
        ('Additional Info', {
            'fields': ('metadata', 'available_from', 'available_until', 'expires_at'),
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
        'approve_quality',
        'reject_quality',
        'clear_home_feed_pins',
        'close_listings'
    ]

    def verify_listings(self, request, queryset):
        """Verify selected listings and notify merchants."""
        updated = 0
        for listing in queryset.select_related('merchant__user'):
            if not listing.is_verified:
                listing.is_verified = True
                listing.verified_at = timezone.now()
                listing.save(update_fields=['is_verified', 'verified_at', 'updated_at'])
                updated += 1
        self.message_user(
            request,
            f'{updated} listing(s) verified. Notifications sent to merchants.',
            level='SUCCESS',
        )

    verify_listings.short_description = 'Verify selected listings (sends notification)'

    def unverify_listings(self, request, queryset):
        """Remove verification from selected listings."""
        updated = 0
        for listing in queryset.select_related('merchant__user'):
            if listing.is_verified:
                listing.is_verified = False
                listing.verified_at = None
                listing.save(update_fields=['is_verified', 'verified_at', 'updated_at'])
                updated += 1
        self.message_user(
            request,
            f'{updated} listing(s) unverified.',
            level='WARNING',
        )

    unverify_listings.short_description = 'Unverify selected listings'

    def approve_listings(self, request, queryset):
        """Approve and activate listings, then notify their merchants."""
        updated = 0
        for listing in queryset.filter(
            status__in=['PENDING', 'DRAFT']
        ).select_related('merchant__user'):
            listing.status = 'ACTIVE'
            listing.is_verified = True
            listing.verified_at = timezone.now()
            listing.save(update_fields=['status', 'is_verified', 'verified_at', 'updated_at'])
            updated += 1
        self.message_user(
            request,
            f'{updated} listing(s) approved and activated. Notifications sent to merchants.',
            level='SUCCESS',
        )

    approve_listings.short_description = 'Approve and activate listings (sends notification)'

    def reject_listings(self, request, queryset):
        """Reject selected listings and notify their merchants."""
        updated = 0
        for listing in queryset.select_related('merchant__user'):
            if listing.status != 'REJECTED':
                listing.status = 'REJECTED'
                listing.is_verified = False
                listing.save(update_fields=['status', 'is_verified', 'updated_at'])
                updated += 1
        self.message_user(
            request,
            f'{updated} listing(s) rejected. Notifications sent. Add rejection reasons via the listing detail page.',
            level='WARNING',
        )

    reject_listings.short_description = 'Reject selected listings (sends notification)'

    def feature_listings(self, request, queryset):
        """Mark selected listings as featured."""
        updated = 0
        for listing in queryset.filter(is_verified=True, status='ACTIVE'):
            if not listing.is_featured:
                listing.is_featured = True
                listing.save(update_fields=['is_featured', 'updated_at'])
                updated += 1
        self.message_user(
            request,
            f'{updated} listing(s) marked as featured.',
            level='SUCCESS',
        )

    feature_listings.short_description = 'Mark as featured'

    def unfeature_listings(self, request, queryset):
        """Remove featured status from selected listings."""
        updated = queryset.filter(is_featured=True).update(
            is_featured=False,
            featured_order=0,
        )
        self.message_user(
            request,
            f'{updated} listing(s) removed from featured.',
            level='INFO',
        )

    unfeature_listings.short_description = 'Remove from featured'

    def approve_quality(self, request, queryset):
        """Approve selected listings for the home feed."""
        updated = queryset.filter(status='ACTIVE', is_verified=True).update(
            quality_status='APPROVED',
            is_home_feed_eligible=True,
            quality_rejection_reason=None,
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f'{updated} listing(s) approved for the home feed.',
            level='SUCCESS',
        )

    approve_quality.short_description = 'Approve quality for home feed'

    def reject_quality(self, request, queryset):
        """Remove selected listings from the home feed."""
        updated = queryset.update(
            quality_status='REJECTED',
            is_home_feed_eligible=False,
            is_home_feed_pinned=False,
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f'{updated} listing(s) removed from the home feed.',
            level='WARNING',
        )

    reject_quality.short_description = 'Reject quality / remove from home feed'

    def clear_home_feed_pins(self, request, queryset):
        """Clear home feed pin settings."""
        updated = queryset.update(
            is_home_feed_pinned=False,
            home_feed_pin_position=None,
            home_feed_pin_until=None,
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f'{updated} listing pin(s) cleared.',
            level='INFO',
        )

    clear_home_feed_pins.short_description = 'Clear home feed pins'

    def close_listings(self, request, queryset):
        """Close selected listings."""
        updated = 0
        for listing in queryset.select_related('merchant__user'):
            if listing.status != 'CLOSED':
                listing.status = 'CLOSED'
                listing.save(update_fields=['status', 'updated_at'])
                updated += 1
        self.message_user(
            request,
            f'{updated} listing(s) closed.',
            level='INFO',
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
