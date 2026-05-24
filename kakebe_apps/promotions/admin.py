from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import BannerAgentCredential, BannerImageImport, PromotionalBanner, BannerListing


class BannerListingInline(admin.TabularInline):
    model = BannerListing
    extra = 1
    autocomplete_fields = ['listing']
    fields = ['listing', 'sort_order']


@admin.register(PromotionalBanner)
class PromotionalBannerAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'display_type', 'placement', 'status_badge',
        'image_preview', 'active_period', 'stats', 'sort_order', 'created_at'
    ]
    list_filter = [
        'display_type', 'placement', 'platform', 'is_verified',
        'is_active', 'start_date', 'end_date'
    ]
    search_fields = ['title', 'description', 'cta_text']
    readonly_fields = [
        'id', 'impressions', 'clicks', 'ctr_display',
        'verified_at', 'created_at', 'updated_at', 'status_indicator', 'image_preview'
    ]
    autocomplete_fields = ['link_category', 'link_merchant']
    inlines = [BannerListingInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'display_type', 'placement', 'platform')
        }),
        ('Media', {
            'fields': ('image_preview', 'image', 'mobile_image', 'image_asset', 'mobile_image_asset')
        }),
        ('Link Configuration', {
            'fields': ('link_type', 'link_url', 'link_category', 'link_merchant', 'cta_text')
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
        elif not obj.start_date or not obj.end_date:
            return format_html('<span style="color: gray;">● No Schedule</span>')
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
        if not obj.start_date or not obj.end_date:
            return '—'
        return f"{obj.start_date.strftime('%Y-%m-%d')} to {obj.end_date.strftime('%Y-%m-%d')}"

    active_period.short_description = 'Active Period'

    def stats(self, obj):
        ctr = obj.get_click_through_rate()
        return format_html(
            '<strong>👁 {}</strong> | <strong>🖱 {}</strong> | <strong>📊 {}%</strong>',
            obj.impressions, obj.clicks, f'{ctr:.1f}'
        )

    stats.short_description = 'Impressions | Clicks | CTR'

    def ctr_display(self, obj):
        return f"{obj.get_click_through_rate():.2f}%"

    ctr_display.short_description = 'Click-Through Rate'

    def image_preview(self, obj):
        if not obj or not obj.image:
            return 'No image'
        return format_html(
            '<img src="{}" style="max-width: 360px; max-height: 120px; object-fit: contain;" />',
            obj.image,
        )

    image_preview.short_description = 'Preview'

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


@admin.register(BannerImageImport)
class BannerImageImportAdmin(admin.ModelAdmin):
    list_display = ['source_path', 'banner', 'uploaded_by_agent', 'target_field', 'status', 'import_preview', 'processed_at', 'created_at']
    list_filter = ['status', 'target_field', 'created_at', 'processed_at']
    search_fields = ['source_path', 'banner__title', 'error_message']
    autocomplete_fields = ['banner', 'image_asset', 'uploaded_by_agent']
    readonly_fields = [
        'id', 'error_message', 'metadata', 'import_preview',
        'processed_at', 'created_at', 'updated_at'
    ]

    def import_preview(self, obj):
        if obj.image_asset:
            return format_html(
                '<img src="{}" style="max-width: 360px; max-height: 120px; object-fit: contain;" />',
                obj.image_asset.cdn_url(),
            )
        return 'Preview available after upload processing'

    import_preview.short_description = 'Preview'


@admin.register(BannerAgentCredential)
class BannerAgentCredentialAdmin(admin.ModelAdmin):
    list_display = ['name', 'token_prefix', 'is_active', 'last_used_at', 'created_at']
    list_filter = ['is_active', 'created_at', 'last_used_at']
    search_fields = ['name', 'token_prefix']
    readonly_fields = ['id', 'token_prefix', 'last_used_at', 'created_at', 'updated_at']
    fields = ['name', 'is_active', 'token_prefix', 'last_used_at', 'id', 'created_at', 'updated_at']
    actions = ['reset_credentials', 'activate_credentials', 'deactivate_credentials']

    def save_model(self, request, obj, form, change):
        if not change and not obj.token_hash:
            secret = obj.issue_secret()
            super().save_model(request, obj, form, change)
            self.message_user(
                request,
                f'Banner agent secret for {obj.name}: {secret}. Store it now; it will not be shown again.',
            )
            return
        super().save_model(request, obj, form, change)

    def reset_credentials(self, request, queryset):
        for credential in queryset:
            secret = credential.issue_secret()
            credential.save(update_fields=['token_prefix', 'token_hash', 'updated_at'])
            self.message_user(
                request,
                f'New banner agent secret for {credential.name}: {secret}. Store it now; it will not be shown again.',
            )

    reset_credentials.short_description = 'Reset selected agent credentials'

    def activate_credentials(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} credential(s) activated.')

    activate_credentials.short_description = 'Activate selected credentials'

    def deactivate_credentials(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} credential(s) deactivated.')

    deactivate_credentials.short_description = 'Deactivate selected credentials'
