# kakebe_apps/imagehandler/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import ImageAsset


@admin.register(ImageAsset)
class ImageAssetAdmin(admin.ModelAdmin):
    list_display = [
        'image_preview',
        'image_type',
        'variant',
        'object_id_short',
        'group_id_short',
        'owner_email',
        'dimensions',
        'file_size',
        'order',
        'is_confirmed',
        'created_at',
    ]

    list_filter = [
        'image_type',
        'variant',
        'is_confirmed',
        'created_at',
    ]

    search_fields = [
        'object_id',
        'image_group_id',
        's3_key',
        'owner__email',
        'owner__name',
    ]

    readonly_fields = [
        'id',
        'image_group_id',
        'owner',
        's3_key',
        'width',
        'height',
        'size_bytes',
        'created_at',
        'updated_at',
        'image_preview_large',
        'cdn_link',
    ]

    fieldsets = (
        ('Image Information', {
            'fields': (
                'id',
                'image_preview_large',
                'cdn_link',
            )
        }),
        ('Ownership & Type', {
            'fields': (
                'owner',
                'image_type',
                'variant',
            )
        }),
        ('Relationships', {
            'fields': (
                'object_id',
                'image_group_id',
            )
        }),
        ('Storage Details', {
            'fields': (
                's3_key',
                'width',
                'height',
                'size_bytes',
            )
        }),
        ('Status & Order', {
            'fields': (
                'order',
                'is_confirmed',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )

    list_per_page = 50
    date_hierarchy = 'created_at'

    actions = [
        'confirm_images',
        'unconfirm_images',
        'delete_unconfirmed',
    ]

    def image_preview(self, obj):
        """Display small thumbnail preview"""
        return format_html(
            '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
            obj.cdn_url()
        )

    image_preview.short_description = 'Preview'

    def image_preview_large(self, obj):
        """Display large preview in detail view"""
        return format_html(
            '<img src="{}" style="max-width: 500px; max-height: 500px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
            obj.cdn_url()
        )

    image_preview_large.short_description = 'Image Preview'

    def cdn_link(self, obj):
        """Display clickable CDN URL"""
        url = obj.cdn_url()
        return format_html(
            '<a href="{}" target="_blank" style="word-break: break-all;">{}</a>',
            url, url
        )

    cdn_link.short_description = 'CDN URL'

    def object_id_short(self, obj):
        """Display shortened object_id"""
        if obj.object_id:
            return str(obj.object_id)[:8] + '...'
        return '-'

    object_id_short.short_description = 'Object ID'

    def group_id_short(self, obj):
        """Display shortened group_id"""
        return str(obj.image_group_id)[:8] + '...'

    group_id_short.short_description = 'Group ID'

    def owner_email(self, obj):
        """Display owner email"""
        return obj.owner.email

    owner_email.short_description = 'Owner'
    owner_email.admin_order_field = 'owner__email'

    def dimensions(self, obj):
        """Display image dimensions"""
        return f'{obj.width} × {obj.height}'

    dimensions.short_description = 'Dimensions'

    def file_size(self, obj):
        """Display formatted file size"""
        size_kb = obj.size_bytes / 1024
        if size_kb < 1024:
            return f'{size_kb:.1f} KB'
        else:
            size_mb = size_kb / 1024
            return f'{size_mb:.2f} MB'

    file_size.short_description = 'Size'

    def confirm_images(self, request, queryset):
        """Bulk action to confirm images"""
        updated = queryset.update(is_confirmed=True)
        self.message_user(
            request,
            f'{updated} image(s) confirmed successfully.'
        )

    confirm_images.short_description = 'Confirm selected images'

    def unconfirm_images(self, request, queryset):
        """Bulk action to unconfirm images"""
        updated = queryset.update(is_confirmed=False)
        self.message_user(
            request,
            f'{updated} image(s) unconfirmed successfully.'
        )

    unconfirm_images.short_description = 'Unconfirm selected images'

    def delete_unconfirmed(self, request, queryset):
        """Bulk action to delete unconfirmed images"""
        unconfirmed = queryset.filter(is_confirmed=False)
        count = unconfirmed.count()
        unconfirmed.delete()
        self.message_user(
            request,
            f'{count} unconfirmed image(s) deleted successfully.'
        )

    delete_unconfirmed.short_description = 'Delete unconfirmed images'

    def get_queryset(self, request):
        """Optimize queries with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('owner')

    def changelist_view(self, request, extra_context=None):
        """Add summary statistics to changelist"""
        extra_context = extra_context or {}

        # Get statistics
        stats = ImageAsset.objects.aggregate(
            total=Count('id'),
            confirmed=Count('id', filter=models.Q(is_confirmed=True)),
            listings=Count('id', filter=models.Q(image_type='listing')),
            profiles=Count('id', filter=models.Q(image_type='profile')),
        )

        extra_context['stats'] = stats

        return super().changelist_view(request, extra_context)


# Import for aggregation
from django.db import models