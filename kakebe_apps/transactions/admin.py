from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db import models
from .models import Transaction


# ========== Transaction Admin ==========
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_number_link',
        'order_intent_link',
        'amount_display',
        'payment_method_badge',
        'status_badge',
        'created_at',
        'completed_at_display',
        'age_display'
    )

    list_filter = (
        'status',
        'payment_method',
        'created_at',
        'completed_at',
    )

    search_fields = (
        'transaction_number',
        'order_intent__order_number',
        'order_intent__buyer__name',
        'order_intent__merchant__display_name',
        'payment_reference',
    )

    list_per_page = 25
    list_select_related = ('order_intent',)

    readonly_fields = (
        'id',
        'transaction_number',
        'created_at',
        'completed_at',
        'order_intent_link',
        'amount_display_field',
        'payment_details',
        'transaction_age',
        'order_intent_info'
    )

    fieldsets = (
        ('Transaction Information', {
            'fields': ('id', 'transaction_number', 'status', 'created_at')
        }),

        ('Order Reference', {
            'fields': ('order_intent_link', 'order_intent_info'),
            'classes': ('wide',)
        }),

        ('Payment Details', {
            'fields': ('amount_display_field', 'currency', 'payment_method', 'payment_reference')
        }),

        ('Payment Status', {
            'fields': ('payment_details', 'completed_at', 'transaction_age'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_completed', 'mark_as_failed', 'mark_as_refunded']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related(
            'order_intent',
            'order_intent__buyer',
            'order_intent__merchant'
        )

    def transaction_number_link(self, obj):
        url = reverse('admin:payments_transaction_change', args=[obj.id])
        return format_html('<a href="{}">{}</a>', url, obj.transaction_number)

    transaction_number_link.short_description = "Transaction #"
    transaction_number_link.admin_order_field = 'transaction_number'

    def order_intent_link(self, obj):
        url = reverse('admin:orders_orderintent_change', args=[obj.order_intent.id])
        return format_html(
            '<a href="{}">Order #{}</a>',
            url,
            obj.order_intent.order_number
        )

    order_intent_link.short_description = "Order"
    order_intent_link.admin_order_field = 'order_intent__order_number'

    def order_intent_info(self, obj):
        info = []
        info.append(f"Buyer: {obj.order_intent.buyer.name}")
        info.append(f"Merchant: {obj.order_intent.merchant.display_name}")
        info.append(f"Order Total: ${obj.order_intent.total_amount:,.2f}")
        return format_html('<br>'.join(info))

    order_intent_info.short_description = "Order Details"

    def amount_display(self, obj):
        return f"{obj.currency} {obj.amount:,.2f}"

    amount_display.short_description = "Amount"
    amount_display.admin_order_field = 'amount'

    def amount_display_field(self, obj):
        # For display in the detail view
        return f"{obj.currency} {obj.amount:,.2f}"

    amount_display_field.short_description = "Amount"

    def payment_method_badge(self, obj):
        colors = {
            'CASH': '#4CAF50',  # Green
            'MOBILE_MONEY': '#2196F3',  # Blue
            'BANK_TRANSFER': '#9C27B0',  # Purple
            'CARD': '#FF9800',  # Orange
        }
        color = colors.get(obj.payment_method, '#9E9E9E')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color, obj.get_payment_method_display()
        )

    payment_method_badge.short_description = "Payment Method"
    payment_method_badge.admin_order_field = 'payment_method'

    def status_badge(self, obj):
        status_colors = {
            'PENDING': '#FF9800',  # Orange
            'COMPLETED': '#4CAF50',  # Green
            'FAILED': '#F44336',  # Red
            'REFUNDED': '#2196F3',  # Blue
        }
        color = status_colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 4px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = 'status'

    def completed_at_display(self, obj):
        if obj.completed_at:
            return obj.completed_at.strftime("%Y-%m-%d %H:%M")
        return "—"

    completed_at_display.short_description = "Completed At"
    completed_at_display.admin_order_field = 'completed_at'

    def age_display(self, obj):
        if obj.status == 'PENDING':
            time_diff = timezone.now() - obj.created_at
            if time_diff.days > 0:
                return f"{time_diff.days}d pending"
            elif time_diff.seconds > 3600:
                return f"{time_diff.seconds // 3600}h pending"
            elif time_diff.seconds > 60:
                return f"{time_diff.seconds // 60}m pending"
            else:
                return "Just created"
        elif obj.completed_at:
            time_diff = timezone.now() - obj.completed_at
            if time_diff.days > 30:
                return f"{time_diff.days // 30}mo ago"
            elif time_diff.days > 0:
                return f"{time_diff.days}d ago"
            elif time_diff.seconds > 3600:
                return f"{time_diff.seconds // 3600}h ago"
            else:
                return f"{time_diff.seconds // 60}m ago"
        return "—"

    age_display.short_description = "Age/Status"

    def payment_details(self, obj):
        details = []

        # Payment reference
        if obj.payment_reference:
            details.append(f"Reference: {obj.payment_reference}")

        # Status timeline
        if obj.completed_at:
            processing_time = obj.completed_at - obj.created_at
            if processing_time.days > 0:
                details.append(f"Processed in: {processing_time.days}d {processing_time.seconds // 3600}h")
            elif processing_time.seconds > 3600:
                details.append(f"Processed in: {processing_time.seconds // 3600}h")
            elif processing_time.seconds > 60:
                details.append(f"Processed in: {processing_time.seconds // 60}m")
            else:
                details.append("Processed instantly")

        if details:
            return format_html('<br>'.join(details))
        return "No additional details"

    payment_details.short_description = "Payment Information"

    def transaction_age(self, obj):
        if obj.status == 'PENDING':
            time_diff = timezone.now() - obj.created_at
            if time_diff.days > 1:
                return format_html(
                    '<span style="color: orange; font-weight: bold;">Pending for {} days</span>',
                    time_diff.days
                )
            elif time_diff.days == 1:
                return format_html(
                    '<span style="color: orange;">Pending for 1 day</span>'
                )
            elif time_diff.seconds > 3600:
                return f"Pending for {time_diff.seconds // 3600} hours"
            else:
                return f"Pending for {time_diff.seconds // 60} minutes"
        elif obj.completed_at:
            time_diff = timezone.now() - obj.completed_at
            if time_diff.days > 30:
                return f"Completed {time_diff.days // 30} months ago"
            elif time_diff.days > 0:
                return f"Completed {time_diff.days} days ago"
            elif time_diff.seconds > 3600:
                return f"Completed {time_diff.seconds // 3600} hours ago"
            else:
                return f"Completed {time_diff.seconds // 60} minutes ago"
        return "—"

    transaction_age.short_description = "Transaction Timeline"

    # Admin actions
    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status='PENDING').update(
            status='COMPLETED',
            completed_at=timezone.now()
        )
        self.message_user(request, f"{updated} transactions marked as completed.")

    mark_as_completed.short_description = "Mark selected as COMPLETED"

    def mark_as_failed(self, request, queryset):
        updated = queryset.filter(status='PENDING').update(status='FAILED')
        self.message_user(request, f"{updated} transactions marked as failed.")

    mark_as_failed.short_description = "Mark selected as FAILED"

    def mark_as_refunded(self, request, queryset):
        updated = queryset.filter(status='COMPLETED').update(status='REFUNDED')
        self.message_user(request, f"{updated} transactions marked as refunded.")

    mark_as_refunded.short_description = "Mark selected as REFUNDED"