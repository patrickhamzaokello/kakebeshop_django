from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum, F, Q
from .models import PromotionalBanner, BannerListing


class BannerListingInline(admin.TabularInline):
    model = BannerListing
    extra = 1
    autocomplete_fields = ['listing']
    fields = ['listing', 'sort_order']


@admin.register(PromotionalBanner)
class PromotionalBannerAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'display_type', 'placement', 'status_badge',
        'active_period', 'stats', 'sort_order', 'created_at'
    ]
    list_filter = [
        'display_type', 'placement', 'platform', 'is_verified',
        'is_active', 'start_date', 'end_date'
    ]
    search_fields = ['title', 'description', 'cta_text']
    readonly_fields = [
        'id', 'impressions', 'clicks', 'ctr_display',
        'verified_at', 'created_at', 'updated_at', 'status_indicator'
    ]
    autocomplete_fields = ['link_category']
    inlines = [BannerListingInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'display_type', 'placement', 'platform')
        }),
        ('Media', {
            'fields': ('image', 'mobile_image')
        }),
        ('Link Configuration', {
            'fields': ('link_type', 'link_url', 'link_category', 'cta_text')
        }),
        ('Scheduling', {
            'fields': ('start_date', 'end_date', 'sort_order')
        }),
        ('Status & Verification', {
            'fields': ('is_active', 'is_verified', 'verified_at', 'status_indicator')
        }),
        ('Analytics', {
            'fields': ('impressions', 'clicks', 'ctr_display'),
            'classes': ('collapse',)
        }),
        ('System Info', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['verify_banners', 'unverify_banners', 'activate_banners', 'deactivate_banners']

    def status_badge(self, obj):
        if obj.is_currently_active():
            return format_html('<span style="color: green;">● Active</span>')
        elif not obj.is_verified:
            return format_html('<span style="color: orange;">● Pending Verification</span>')
        elif not obj.is_active:
            return format_html('<span style="color: gray;">● Disabled</span>')
        else:
            now = timezone.now()
            if now < obj.start_date:
                return format_html('<span style="color: blue;">● Scheduled</span>')
            else:
                return format_html('<span style="color: red;">● Expired</span>')

    status_badge.short_description = 'Status'

    def status_indicator(self, obj):
        return self.status_badge(obj)

    status_indicator.short_description = 'Current Status'

    def active_period(self, obj):
        return f"{obj.start_date.strftime('%Y-%m-%d')} to {obj.end_date.strftime('%Y-%m-%d')}"

    active_period.short_description = 'Active Period'

    def stats(self, obj):
        ctr = obj.get_click_through_rate()
        return format_html(
            '<strong>👁 {}</strong> | <strong>🖱 {}</strong> | <strong>📊 {:.1f}%</strong>',
            obj.impressions, obj.clicks, ctr
        )

    stats.short_description = 'Impressions | Clicks | CTR'

    def ctr_display(self, obj):
        return f"{obj.get_click_through_rate():.2f}%"

    ctr_display.short_description = 'Click-Through Rate'

    def verify_banners(self, request, queryset):
        updated = queryset.update(is_verified=True, verified_at=timezone.now())
        self.message_user(request, f'{updated} banner(s) verified successfully.')

    verify_banners.short_description = 'Verify selected banners'

    def unverify_banners(self, request, queryset):
        updated = queryset.update(is_verified=False, verified_at=None)
        self.message_user(request, f'{updated} banner(s) unverified.')

    unverify_banners.short_description = 'Unverify selected banners'

    def activate_banners(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} banner(s) activated.')

    activate_banners.short_description = 'Activate selected banners'

    def deactivate_banners(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} banner(s) deactivated.')

    deactivate_banners.short_description = 'Deactivate selected banners'


@admin.register(BannerListing)
class BannerListingAdmin(admin.ModelAdmin):
    list_display = ['banner', 'listing', 'sort_order', 'created_at']
    list_filter = ['created_at']
    search_fields = ['banner__title', 'listing__title']
    autocomplete_fields = ['banner', 'listing']
    ordering = ['banner', 'sort_order']