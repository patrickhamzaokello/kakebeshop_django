from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from django.utils import timezone
from .models import OrderIntent, OrderIntentItem


# ========== Inline for Order Items ==========
class OrderIntentItemInline(admin.TabularInline):
    model = OrderIntentItem
    extra = 0
    readonly_fields = ('listing_link', 'quantity', 'unit_price', 'total_price', 'created_at')
    fields = ('listing_link', 'quantity', 'unit_price', 'total_price')
    can_delete = False
    show_change_link = True
    verbose_name_plural = "Order Items"

    def has_add_permission(self, request, obj=None):
        return False

    def listing_link(self, obj):
        url = reverse('admin:listings_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title[:50])

    listing_link.short_description = "Listing"


# ========== OrderIntentItem Admin ==========
@admin.register(OrderIntentItem)
class OrderIntentItemAdmin(admin.ModelAdmin):
    list_display = (
        'order_link',
        'listing_link',
        'quantity',
        'unit_price_display',
        'total_price_display',
        'created_at'
    )
    list_filter = ('created_at',)
    search_fields = (
        'order_intent__order_number',
        'listing__title',
        'order_intent__buyer__name',
        'order_intent__merchant__display_name'
    )
    list_per_page = 25
    readonly_fields = (
        'id',
        'created_at',
        'order_link',
        'listing_link',
        'unit_price_display',
        'total_price_display'
    )
    fieldsets = (
        ('Order Information', {
            'fields': ('order_link', 'listing_link')
        }),
        ('Item Details', {
            'fields': ('quantity', 'unit_price_display', 'total_price_display')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def order_link(self, obj):
        url = reverse('admin:orders_orderintent_change', args=[obj.order_intent.id])
        return format_html(
            '<a href="{}">Order #{}</a>',
            url,
            obj.order_intent.order_number
        )

    order_link.short_description = "Order"
    order_link.admin_order_field = 'order_intent__order_number'

    def listing_link(self, obj):
        url = reverse('admin:listings_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title[:60])

    listing_link.short_description = "Listing"
    listing_link.admin_order_field = 'listing__title'

    def unit_price_display(self, obj):
        return f"${obj.unit_price:,.2f}"

    unit_price_display.short_description = "Unit Price"

    def total_price_display(self, obj):
        return f"${obj.total_price:,.2f}"

    total_price_display.short_description = "Total Price"


# ========== OrderIntent Admin ==========
@admin.register(OrderIntent)
class OrderIntentAdmin(admin.ModelAdmin):
    list_display = (
        'order_number_link',
        'buyer_link',
        'merchant_link',
        'status_badge',
        'total_amount_display',
        'items_count',
        'created_at',
        'updated_at'
    )
    list_filter = (
        'status',
        'cancelled_by',
        'created_at',
        'updated_at',
        'merchant'
    )
    search_fields = (
        'order_number',
        'buyer__name',
        'buyer__email',
        'merchant__display_name',
        'address__street_address',
        'notes'
    )
    list_per_page = 25
    list_select_related = ('buyer', 'merchant', 'address')
    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'buyer_link',
        'merchant_link',
        'address_link',
        'items_count',
        'items_total',
        'cancellation_info',
        'order_summary'
    )
    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'order_number', 'status', 'notes')
        }),
        ('Participants', {
            'fields': ('buyer_link', 'merchant_link', 'address_link')
        }),
        ('Financial Details', {
            'fields': ('total_amount_display_field', 'delivery_fee', 'order_summary'),
            'classes': ('wide',)
        }),
        ('Delivery Information', {
            'fields': ('expected_delivery_date',),
            'classes': ('collapse',)
        }),
        ('Cancellation Details', {
            'fields': ('cancelled_by', 'cancellation_reason', 'cancellation_info'),
            'classes': ('collapse',)
        }),
        ('Order Items', {
            'fields': ('items_count', 'items_total'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    inlines = [OrderIntentItemInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('buyer', 'merchant', 'address').prefetch_related('items')

    def order_number_link(self, obj):
        url = reverse('admin:orders_orderintent_change', args=[obj.id])
        return format_html('<a href="{}">{}</a>', url, obj.order_number)

    order_number_link.short_description = "Order Number"
    order_number_link.admin_order_field = 'order_number'

    def buyer_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.buyer.id])
        return format_html('<a href="{}">{}</a>', url, obj.buyer.name)

    buyer_link.short_description = "Buyer"
    buyer_link.admin_order_field = 'buyer__name'

    def merchant_link(self, obj):
        url = reverse('admin:merchants_merchant_change', args=[obj.merchant.id])
        return format_html('<a href="{}">{}</a>', url, obj.merchant.display_name)

    merchant_link.short_description = "Merchant"
    merchant_link.admin_order_field = 'merchant__display_name'

    def address_link(self, obj):
        if obj.address:
            # Assuming UserAddress model has an admin
            try:
                url = reverse('admin:location_useraddress_change', args=[obj.address.id])
                address_text = f"{obj.address.street_address[:30]}..." if len(
                    obj.address.street_address) > 30 else obj.address.street_address
                return format_html('<a href="{}">{}</a>', url, address_text)
            except:
                return obj.address.street_address[:50]
        return "—"

    address_link.short_description = "Delivery Address"

    def status_badge(self, obj):
        status_colors = {
            'NEW': '#2196F3',  # Blue
            'CONTACTED': '#4CAF50',  # Green
            'CONFIRMED': '#8BC34A',  # Light Green
            'COMPLETED': '#009688',  # Teal
            'CANCELLED': '#F44336',  # Red
        }
        color = status_colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 4px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = 'status'

    def total_amount_display(self, obj):
        return f"${obj.total_amount:,.2f}"

    total_amount_display.short_description = "Total Amount"
    total_amount_display.admin_order_field = 'total_amount'

    def total_amount_display_field(self, obj):
        # For display in the detail view
        return f"${obj.total_amount:,.2f}"

    total_amount_display_field.short_description = "Total Amount"

    def items_count(self, obj):
        return obj.items.count()

    items_count.short_description = "Items"

    def items_total(self, obj):
        item_count = obj.items.count()
        total_quantity = obj.items.aggregate(total=models.Sum('quantity'))['total'] or 0
        return f"{item_count} items, {total_quantity} units"

    items_total.short_description = "Items Summary"

    def cancellation_info(self, obj):
        if obj.status == 'CANCELLED':
            info = []
            if obj.cancelled_by:
                info.append(f"Cancelled by: {obj.get_cancelled_by_display()}")
            if obj.cancellation_reason:
                reason = obj.cancellation_reason[:100] + "..." if len(
                    obj.cancellation_reason) > 100 else obj.cancellation_reason
                info.append(f"Reason: {reason}")
            if info:
                return format_html('<br>'.join(info))
        return "—"

    cancellation_info.short_description = "Cancellation Details"

    def order_summary(self, obj):
        summary = []
        if obj.delivery_fee:
            summary.append(f"Delivery Fee: ${obj.delivery_fee:,.2f}")

        # Calculate subtotal from items
        subtotal = sum(item.total_price for item in obj.items.all())
        summary.append(f"Subtotal: ${subtotal:,.2f}")
        summary.append(f"Total: ${obj.total_amount:,.2f}")

        return format_html('<br>'.join(summary))

    order_summary.short_description = "Financial Summary"

    def delivery_info(self, obj):
        info = []
        if obj.expected_delivery_date:
            today = timezone.now().date()
            if obj.expected_delivery_date < today:
                info.append(f"<span style='color: red;'>Overdue: {obj.expected_delivery_date}</span>")
            elif obj.expected_delivery_date == today:
                info.append(f"<span style='color: orange;'>Today: {obj.expected_delivery_date}</span>")
            else:
                days_until = (obj.expected_delivery_date - today).days
                info.append(f"Due in {days_until} days: {obj.expected_delivery_date}")

        if info:
            return format_html('<br>'.join(info))
        return "No delivery date set"

    delivery_info.short_description = "Delivery Status"

    # Actions for the admin
    actions = ['mark_as_confirmed', 'mark_as_completed', 'mark_as_cancelled']

    def mark_as_confirmed(self, request, queryset):
        updated = queryset.filter(status='CONTACTED').update(status='CONFIRMED', updated_at=timezone.now())
        self.message_user(request, f"{updated} orders marked as confirmed.")

    mark_as_confirmed.short_description = "Mark selected orders as CONFIRMED"

    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status='CONFIRMED').update(status='COMPLETED', updated_at=timezone.now())
        self.message_user(request, f"{updated} orders marked as completed.")

    mark_as_completed.short_description = "Mark selected orders as COMPLETED"

    def mark_as_cancelled(self, request, queryset):
        # You might want to add a form to collect cancellation reason
        updated = queryset.exclude(status='CANCELLED').update(
            status='CANCELLED',
            cancelled_by='ADMIN',
            updated_at=timezone.now()
        )
        self.message_user(request, f"{updated} orders marked as cancelled.")

    mark_as_cancelled.short_description = "Mark selected orders as CANCELLED"