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
        'suspend_merchants',
        'ban_merchants',
        'feature_merchants',
        'unfeature_merchants',
    ]

    def verify_merchants(self, request, queryset):
        """Verify selected merchants and notify them via push/email."""
        from django.utils import timezone
        updated = 0
        for merchant in queryset.select_related('user'):
            if not merchant.verified:
                merchant.verified = True
                merchant.verification_date = timezone.now()
                # Save individual instance so pre_save/post_save signals fire
                merchant.save(update_fields=['verified', 'verification_date', 'updated_at'])
                updated += 1
        self.message_user(
            request,
            f'{updated} merchant(s) verified. Approval notifications sent.',
            level='SUCCESS',
        )

    verify_merchants.short_description = 'Verify selected merchants (sends notification)'

    def unverify_merchants(self, request, queryset):
        """Remove verification from selected merchants."""
        updated = 0
        for merchant in queryset.select_related('user'):
            if merchant.verified:
                merchant.verified = False
                merchant.verification_date = None
                merchant.save(update_fields=['verified', 'verification_date', 'updated_at'])
                updated += 1
        self.message_user(
            request,
            f'{updated} merchant(s) unverified. They will no longer appear in the app.',
            level='WARNING',
        )

    unverify_merchants.short_description = 'Unverify selected merchants'

    def activate_merchants(self, request, queryset):
        """Reactivate suspended or banned merchants and notify them."""
        updated = 0
        for merchant in queryset.select_related('user'):
            if merchant.status != 'ACTIVE':
                merchant.status = 'ACTIVE'
                # Save individual instance so signals fire and notification is sent
                merchant.save(update_fields=['status', 'updated_at'])
                updated += 1
        self.message_user(
            request,
            f'{updated} merchant(s) activated. Reactivation notifications sent.',
        )

    activate_merchants.short_description = 'Activate selected merchants (sends notification)'

    def suspend_merchants(self, request, queryset):
        """Suspend selected merchants and notify them."""
        updated = 0
        for merchant in queryset.select_related('user'):
            if merchant.status != 'SUSPENDED':
                merchant.status = 'SUSPENDED'
                merchant.save(update_fields=['status', 'updated_at'])
                updated += 1
        self.message_user(
            request,
            f'{updated} merchant(s) suspended. Suspension notifications sent.',
            level='WARNING',
        )

    suspend_merchants.short_description = 'Suspend selected merchants (sends notification)'

    def ban_merchants(self, request, queryset):
        """Permanently ban selected merchants and notify them."""
        updated = 0
        for merchant in queryset.select_related('user'):
            if merchant.status != 'BANNED':
                merchant.status = 'BANNED'
                merchant.save(update_fields=['status', 'updated_at'])
                updated += 1
        self.message_user(
            request,
            f'{updated} merchant(s) banned. Ban notifications sent.',
            level='ERROR',
        )

    ban_merchants.short_description = 'Ban selected merchants (sends notification)'

    def feature_merchants(self, request, queryset):
        """Mark selected merchants as featured."""
        updated = 0
        for merchant in queryset:
            if not merchant.featured:
                merchant.featured = True
                merchant.save(update_fields=['featured', 'updated_at'])
                updated += 1
        self.message_user(
            request,
            f'{updated} merchant(s) marked as featured. They will appear on the homepage.',
            level='SUCCESS',
        )

    feature_merchants.short_description = 'Mark as featured'

    def unfeature_merchants(self, request, queryset):
        """Remove featured status from selected merchants."""
        updated = queryset.filter(featured=True).update(featured=False, featured_order=0)
        self.message_user(
            request,
            f'{updated} merchant(s) removed from featured list.',
            level='INFO',
        )

    unfeature_merchants.short_description = 'Remove from featured'