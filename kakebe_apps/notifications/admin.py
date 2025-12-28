# kakebe_apps/notifications/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import (
    Notification,
    NotificationDelivery,
    UserNotificationPreference,
)


class NotificationDeliveryInline(admin.TabularInline):
    model = NotificationDelivery
    extra = 0
    fields = ('channel', 'status', 'recipient', 'sent_at', 'error_message')
    readonly_fields = ('sent_at',)
    can_delete = False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'notification_type',
        'user_display',
        'title_display',
        'status_display',
        'created_at',
    )
    list_filter = (
        'notification_type',
        'is_read',
        'created_at',
    )
    search_fields = (
        'user__email',
        'user__name',
        'title',
        'message',
    )
    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'read_at',
    )
    inlines = [NotificationDeliveryInline]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Notification Details', {
            'fields': ('id', 'user', 'notification_type', 'title', 'message')
        }),
        ('Related Objects', {
            'fields': ('order_id', 'merchant_id', 'listing_id')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def user_display(self, obj):
        return format_html(
            '<a href="/admin/auth/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.email
        )

    user_display.short_description = 'User'

    def title_display(self, obj):
        max_length = 50
        if len(obj.title) > max_length:
            return f"{obj.title[:max_length]}..."
        return obj.title

    title_display.short_description = 'Title'

    def status_display(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="color: #4CAF50;">✓ Read</span>'
            )
        return format_html(
            '<span style="color: #FF9800;">⊙ Unread</span>'
        )

    status_display.short_description = 'Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').prefetch_related('deliveries')


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        'notification_type_display',
        'channel',
        'status_display',
        'recipient_display',
        'retry_count',
        'created_at',
    )
    list_filter = (
        'channel',
        'status',
        'created_at',
    )
    search_fields = (
        'notification__user__email',
        'recipient',
        'external_id',
    )
    readonly_fields = (
        'id',
        'notification',
        'sent_at',
        'delivered_at',
        'created_at',
        'updated_at',
    )

    fieldsets = (
        ('Delivery Details', {
            'fields': ('id', 'notification', 'channel', 'recipient')
        }),
        ('Status', {
            'fields': ('status', 'sent_at', 'delivered_at', 'error_message')
        }),
        ('Retry Information', {
            'fields': ('retry_count', 'max_retries', 'next_retry_at')
        }),
        ('External Service', {
            'fields': ('external_id', 'response_data')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def notification_type_display(self, obj):
        return obj.notification.notification_type

    notification_type_display.short_description = 'Type'

    def status_display(self, obj):
        colors = {
            'PENDING': '#FF9800',
            'SENT': '#2196F3',
            'DELIVERED': '#4CAF50',
            'FAILED': '#F44336',
            'READ': '#8BC34A',
        }
        color = colors.get(obj.status, '#999')
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_display.short_description = 'Status'

    def recipient_display(self, obj):
        if obj.channel == 'EMAIL':
            return obj.recipient
        elif obj.channel == 'PUSH':
            tokens = obj.recipient.split(',')
            return f"{len(tokens)} device(s)"
        return obj.recipient

    recipient_display.short_description = 'Recipient'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('notification', 'notification__user')


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        'user_display',
        'email_status',
        'push_status',
        'device_count',
        'updated_at',
    )
    list_filter = (
        'email_enabled',
        'push_enabled',
    )
    search_fields = (
        'user__email',
        'user__name',
    )
    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
    )

    fieldsets = (
        ('User', {
            'fields': ('id', 'user')
        }),
        ('Email Preferences', {
            'fields': (
                'email_enabled',
                'email_order_updates',
                'email_merchant_updates',
                'email_marketing',
            )
        }),
        ('Push Notification Preferences', {
            'fields': (
                'push_enabled',
                'push_order_updates',
                'push_merchant_updates',
                'device_tokens',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def user_display(self, obj):
        return format_html(
            '<a href="/admin/auth/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.email
        )

    user_display.short_description = 'User'

    def email_status(self, obj):
        if obj.email_enabled:
            return format_html('<span style="color: #4CAF50;">✓ Enabled</span>')
        return format_html('<span style="color: #999;">✗ Disabled</span>')

    email_status.short_description = 'Email'

    def push_status(self, obj):
        if obj.push_enabled:
            return format_html('<span style="color: #4CAF50;">✓ Enabled</span>')
        return format_html('<span style="color: #999;">✗ Disabled</span>')

    push_status.short_description = 'Push'

    def device_count(self, obj):
        count = len(obj.device_tokens)
        return format_html(
            '<span style="font-weight: 600;">{} device(s)</span>',
            count
        )

    device_count.short_description = 'Devices'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')