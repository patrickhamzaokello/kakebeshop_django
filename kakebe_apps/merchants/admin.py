# kakebe_apps/merchants/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Merchant


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'user', 'rating_display',
        'verified_display', 'featured_display', 'status', 'created_at'
    ]
    list_filter = ['verified', 'featured', 'status', 'created_at']
    search_fields = ['display_name', 'business_name', 'user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    list_editable = ['status']

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'display_name', 'business_name','location', 'description')
        }),
        ('Contact Information', {
            'fields': ('business_phone', 'business_email')
        }),
        ('Media', {
            'fields': ('logo', 'cover_image')
        }),
        ('Verification & Rating', {
            'fields': ('verified', 'verification_date', 'rating', 'total_reviews')
        }),
        ('Featured Settings', {
            'fields': ('featured', 'featured_order'),
            'description': 'Featured merchants appear on the homepage. Lower order numbers appear first.'
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )

    def rating_display(self, obj):
        stars = '⭐' * int(obj.rating)
        return format_html(
            '<span title="{}">{} ({}/5)</span>',
            f'{obj.total_reviews} reviews',
            stars,
            obj.rating
        )

    rating_display.short_description = 'Rating'

    def verified_display(self, obj):
        if obj.verified:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: orange;">⏳ Pending Verification</span>'
        )

    verified_display.short_description = 'Verification'

    def featured_display(self, obj):
        if obj.featured:
            return format_html(
                '<span style="color: gold;">⭐ Featured (Order: {})</span>',
                obj.featured_order
            )
        return format_html(
            '<span style="color: gray;">Not Featured</span>'
        )

    featured_display.short_description = 'Featured Status'

    actions = [
        'verify_merchants',
        'unverify_merchants',
        'activate_merchants',
        'feature_merchants',
        'unfeature_merchants'
    ]

    def verify_merchants(self, request, queryset):
        """Verify selected merchants"""
        from django.utils import timezone
        updated = queryset.update(verified=True, verification_date=timezone.now())
        self.message_user(
            request,
            f'{updated} merchant(s) verified successfully. They can now appear in the app.',
            level='SUCCESS'
        )

    verify_merchants.short_description = 'Verify selected merchants'

    def unverify_merchants(self, request, queryset):
        """Remove verification from selected merchants"""
        updated = queryset.update(verified=False, verification_date=None)
        self.message_user(
            request,
            f'{updated} merchant(s) unverified. They will no longer appear in the app.',
            level='WARNING'
        )

    unverify_merchants.short_description = 'Unverify selected merchants'

    def activate_merchants(self, request, queryset):
        """Activate selected merchants"""
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f'{updated} merchant(s) activated.')

    activate_merchants.short_description = 'Activate selected merchants'

    def feature_merchants(self, request, queryset):
        """Mark selected merchants as featured"""
        # Set featured to True for selected merchants
        updated = 0
        for merchant in queryset:
            if not merchant.featured:
                merchant.featured = True
                merchant.save(update_fields=['featured'])
                updated += 1

        self.message_user(
            request,
            f'{updated} merchant(s) marked as featured. They will appear on the homepage.',
            level='SUCCESS'
        )

    feature_merchants.short_description = 'Mark as featured'

    def unfeature_merchants(self, request, queryset):
        """Remove featured status from selected merchants"""
        updated = queryset.filter(featured=True).update(featured=False, featured_order=0)
        self.message_user(
            request,
            f'{updated} merchant(s) removed from featured list.',
            level='INFO'
        )

    unfeature_merchants.short_description = 'Remove from featured'