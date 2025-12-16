# kakebe_apps/merchants/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Merchant


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'user', 'rating_display',
        'verified_display', 'status', 'created_at'
    ]
    list_filter = ['verified', 'status', 'created_at']
    search_fields = ['display_name', 'business_name', 'user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'display_name', 'business_name', 'description')
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
                '<span style="color: green;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: gray;">Not Verified</span>'
        )

    verified_display.short_description = 'Verification'

    actions = ['verify_merchants', 'unverify_merchants', 'activate_merchants']

    def verify_merchants(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(verified=True, verification_date=timezone.now())
        self.message_user(request, f'{updated} merchant(s) verified successfully.')

    verify_merchants.short_description = 'Verify selected merchants'

    def unverify_merchants(self, request, queryset):
        updated = queryset.update(verified=False, verification_date=None)
        self.message_user(request, f'{updated} merchant(s) unverified.')

    unverify_merchants.short_description = 'Unverify selected merchants'

    def activate_merchants(self, request, queryset):
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f'{updated} merchant(s) activated.')

    activate_merchants.short_description = 'Activate selected merchants'