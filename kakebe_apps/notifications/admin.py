# kakebe_apps/notifications/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
from .models import (
    Notification,
    NotificationDelivery,
    NotificationChannel,
    NotificationStatus,
    UserNotificationPreference,
)


# ── Inline ────────────────────────────────────────────────────────────────────

class NotificationDeliveryInline(admin.TabularInline):
    model = NotificationDelivery
    extra = 0
    can_delete = False
    fields = (
        'channel', 'status_badge', 'recipient_short',
        'sent_at', 'retry_count', 'error_summary',
    )
    readonly_fields = (
        'channel', 'status_badge', 'recipient_short',
        'sent_at', 'retry_count', 'error_summary',
    )

    def status_badge(self, obj):
        colors = {
            NotificationStatus.PENDING:   ('#FF9800', '⏳ Pending'),
            NotificationStatus.SENT:      ('#2196F3', '✉ Sent'),
            NotificationStatus.DELIVERED: ('#4CAF50', '✓ Delivered'),
            NotificationStatus.FAILED:    ('#F44336', '✗ Failed'),
            NotificationStatus.READ:      ('#8BC34A', '✓ Read'),
        }
        color, label = colors.get(obj.status, ('#999', obj.status))
        return format_html(
            '<span style="color:{}; font-weight:600;">{}</span>', color, label
        )
    status_badge.short_description = 'Status'

    def recipient_short(self, obj):
        if obj.channel == NotificationChannel.PUSH:
            count = len([t for t in obj.recipient.split(',') if t])
            return f'{count} token(s)'
        return obj.recipient
    recipient_short.short_description = 'Recipient'

    def error_summary(self, obj):
        if not obj.error_message:
            return '—'
        msg = obj.error_message[:120]
        if len(obj.error_message) > 120:
            msg += '…'
        return format_html(
            '<span style="color:#F44336; font-family:monospace; font-size:11px;">{}</span>',
            msg,
        )
    error_summary.short_description = 'Last Error'


# ── Notification ──────────────────────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'notification_type',
        'user_display',
        'title_display',
        'delivery_summary',
        'is_read',
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
    readonly_fields = ('id', 'created_at', 'updated_at', 'read_at')
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

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('user')
            .prefetch_related('deliveries')
        )

    def user_display(self, obj):
        return format_html(
            '<a href="/admin/authentication/user/{}/change/">{}</a>',
            obj.user.id, obj.user.email,
        )
    user_display.short_description = 'User'

    def title_display(self, obj):
        return obj.title[:50] + ('…' if len(obj.title) > 50 else '')
    title_display.short_description = 'Title'

    def delivery_summary(self, obj):
        """Show per-channel delivery status at a glance."""
        parts = []
        for delivery in obj.deliveries.all():
            icons = {
                NotificationChannel.EMAIL: '✉',
                NotificationChannel.PUSH:  '📲',
                NotificationChannel.IN_APP: '🔔',
            }
            colors = {
                NotificationStatus.PENDING:   '#FF9800',
                NotificationStatus.SENT:      '#2196F3',
                NotificationStatus.DELIVERED: '#4CAF50',
                NotificationStatus.FAILED:    '#F44336',
            }
            icon = icons.get(delivery.channel, '?')
            color = colors.get(delivery.status, '#999')
            parts.append(
                format_html(
                    '<span style="color:{};" title="{}: {}">{}</span>',
                    color, delivery.channel, delivery.status, icon,
                )
            )
        return format_html(' '.join(str(p) for p in parts)) if parts else '—'
    delivery_summary.short_description = 'Deliveries'


# ── NotificationDelivery ──────────────────────────────────────────────────────

class FailedDeliveryFilter(admin.SimpleListFilter):
    title = 'quick filters'
    parameter_name = 'quick'

    def lookups(self, request, model_admin):
        return [
            ('failed', '✗ Failed'),
            ('pending', '⏳ Pending'),
            ('needs_retry', '🔁 Needs retry'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'failed':
            return queryset.filter(status=NotificationStatus.FAILED)
        if self.value() == 'pending':
            return queryset.filter(status=NotificationStatus.PENDING)
        if self.value() == 'needs_retry':
            return queryset.filter(
                status=NotificationStatus.FAILED,
                retry_count__lt=3,
                next_retry_at__lte=timezone.now(),
            )
        return queryset


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'notification_type_display',
        'user_display',
        'channel_badge',
        'status_badge',
        'sent_at',
        'retry_info',
        'error_summary',
    )
    list_filter = (
        FailedDeliveryFilter,
        'channel',
        'status',
        'created_at',
    )
    search_fields = (
        'notification__user__email',
        'notification__user__name',
        'recipient',
        'error_message',
        'external_id',
    )
    readonly_fields = (
        'id',
        'notification',
        'sent_at',
        'delivered_at',
        'created_at',
        'updated_at',
        'response_data',
    )
    actions = ['retry_failed']
    list_per_page = 50
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Delivery Details', {
            'fields': ('id', 'notification', 'channel', 'recipient')
        }),
        ('Status', {
            'fields': ('status', 'sent_at', 'delivered_at')
        }),
        ('Failure Reason', {
            'fields': ('error_message',),
            'classes': ('collapse',),
            'description': 'Populated when status is FAILED.',
        }),
        ('Retry', {
            'fields': ('retry_count', 'max_retries', 'next_retry_at')
        }),
        ('External Service Response', {
            'fields': ('external_id', 'response_data'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related('notification', 'notification__user')
        )

    # ── list_display helpers ──────────────────────────────────────────────────

    def notification_type_display(self, obj):
        return obj.notification.notification_type
    notification_type_display.short_description = 'Type'
    notification_type_display.admin_order_field = 'notification__notification_type'

    def user_display(self, obj):
        user = obj.notification.user
        return format_html(
            '<a href="/admin/authentication/user/{}/change/">{}</a>',
            user.id, user.email,
        )
    user_display.short_description = 'User'

    def channel_badge(self, obj):
        labels = {
            NotificationChannel.EMAIL:  ('✉', '#555'),
            NotificationChannel.PUSH:   ('📲', '#555'),
            NotificationChannel.IN_APP: ('🔔', '#555'),
        }
        icon, color = labels.get(obj.channel, ('?', '#999'))
        return format_html(
            '<span style="color:{};">{} {}</span>', color, icon, obj.channel,
        )
    channel_badge.short_description = 'Channel'

    def status_badge(self, obj):
        colors = {
            NotificationStatus.PENDING:   '#FF9800',
            NotificationStatus.SENT:      '#2196F3',
            NotificationStatus.DELIVERED: '#4CAF50',
            NotificationStatus.FAILED:    '#F44336',
            NotificationStatus.READ:      '#8BC34A',
        }
        color = colors.get(obj.status, '#999')
        return format_html(
            '<span style="color:{}; font-weight:600;">{}</span>',
            color, obj.get_status_display(),
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def retry_info(self, obj):
        if obj.retry_count == 0 and obj.status != NotificationStatus.FAILED:
            return '—'
        color = '#F44336' if obj.retry_count >= obj.max_retries else '#FF9800'
        return format_html(
            '<span style="color:{};">{}/{} retries</span>',
            color, obj.retry_count, obj.max_retries,
        )
    retry_info.short_description = 'Retries'

    def error_summary(self, obj):
        if not obj.error_message:
            return '—'
        msg = obj.error_message[:100]
        if len(obj.error_message) > 100:
            msg += '…'
        return format_html(
            '<span style="color:#F44336; font-family:monospace; font-size:11px;" '
            'title="{}">{}</span>',
            obj.error_message, msg,
        )
    error_summary.short_description = 'Failure Reason'

    # ── actions ───────────────────────────────────────────────────────────────

    @admin.action(description='🔁 Retry selected failed deliveries')
    def retry_failed(self, request, queryset):
        from .tasks import send_email_notification, send_push_notification

        eligible = queryset.filter(status=NotificationStatus.FAILED)
        count = 0
        for delivery in eligible:
            delivery.status = NotificationStatus.PENDING
            delivery.error_message = None
            delivery.next_retry_at = None
            delivery.save(update_fields=['status', 'error_message', 'next_retry_at'])

            if delivery.channel == NotificationChannel.EMAIL:
                send_email_notification.delay(str(delivery.id))
                count += 1
            elif delivery.channel == NotificationChannel.PUSH:
                send_push_notification.delay(str(delivery.id))
                count += 1

        self.message_user(request, f'Queued {count} delivery task(s) for retry.')


# ── UserNotificationPreference ────────────────────────────────────────────────

@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        'user_display',
        'email_status',
        'push_status',
        'device_count',
        'updated_at',
    )
    list_filter = ('email_enabled', 'push_enabled')
    search_fields = ('user__email', 'user__name')
    readonly_fields = ('id', 'created_at', 'updated_at')

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

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def user_display(self, obj):
        return format_html(
            '<a href="/admin/authentication/user/{}/change/">{}</a>',
            obj.user.id, obj.user.email,
        )
    user_display.short_description = 'User'

    def email_status(self, obj):
        if obj.email_enabled:
            return format_html('<span style="color:#4CAF50;">✓ Enabled</span>')
        return format_html('<span style="color:#999;">✗ Disabled</span>')
    email_status.short_description = 'Email'

    def push_status(self, obj):
        if obj.push_enabled:
            return format_html('<span style="color:#4CAF50;">✓ Enabled</span>')
        return format_html('<span style="color:#999;">✗ Disabled</span>')
    push_status.short_description = 'Push'

    def device_count(self, obj):
        count = len(obj.device_tokens)
        return format_html('<span style="font-weight:600;">{} device(s)</span>', count)
    device_count.short_description = 'Devices'
