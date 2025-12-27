# kakebe_apps/orders/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count
from django.utils import timezone
from .models import OrderGroup, OrderIntent, OrderIntentItem


class OrderGroupFilter(admin.SimpleListFilter):
    """Custom filter for orders with/without group"""
    title = 'order group'
    parameter_name = 'has_group'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Part of Group'),
            ('no', 'Single Order'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(order_group__isnull=False)
        if self.value() == 'no':
            return queryset.filter(order_group__isnull=True)
        return queryset


class OrderIntentItemInline(admin.TabularInline):
    """Inline for OrderIntentItems in OrderIntent admin"""
    model = OrderIntentItem
    extra = 0
    fields = ('listing', 'quantity', 'unit_price', 'total_price', 'created_at')
    readonly_fields = ('created_at', 'total_price')

    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly when editing existing order"""
        if obj:  # Editing existing order
            return self.readonly_fields + ('listing', 'quantity', 'unit_price')
        return self.readonly_fields


class OrderIntentInline(admin.TabularInline):
    """Inline for OrderIntents in OrderGroup admin"""
    model = OrderIntent
    extra = 0
    fields = ('order_number_link', 'merchant', 'total_amount', 'status', 'created_at')
    readonly_fields = ('order_number_link', 'merchant', 'total_amount', 'status', 'created_at')
    can_delete = False

    def order_number_link(self, obj):
        """Link to order detail page"""
        if obj.id:
            url = reverse('admin:orders_orderintent_change', args=[obj.id])
            return format_html('<a href="{}">{}</a>', url, obj.order_number)
        return '-'

    order_number_link.short_description = 'Order Number'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OrderGroup)
class OrderGroupAdmin(admin.ModelAdmin):
    """Admin for OrderGroup model"""
    list_display = (
        'group_number_display',
        'buyer_link',
        'total_orders',
        'total_amount_display',
        'created_at_display',
        'view_orders_link'
    )
    list_filter = (
        'created_at',
        'total_orders',
    )
    search_fields = (
        'group_number',
        'buyer__email',
        'buyer__name',
    )
    readonly_fields = (
        'id',
        'group_number',
        'buyer',
        'total_amount',
        'total_orders',
        'created_at',
        'orders_summary'
    )
    inlines = [OrderIntentInline]

    fieldsets = (
        ('Group Information', {
            'fields': ('id', 'group_number', 'created_at')
        }),
        ('Buyer Details', {
            'fields': ('buyer',)
        }),
        ('Summary', {
            'fields': ('total_orders', 'total_amount', 'orders_summary')
        }),
    )

    def group_number_display(self, obj):
        """Display group number with icon"""
        return format_html(
            '<strong>📦 {}</strong>',
            obj.group_number
        )

    group_number_display.short_description = 'Group Number'
    group_number_display.admin_order_field = 'group_number'

    def buyer_link(self, obj):
        """Link to buyer admin page"""
        url = reverse('admin:authentication_user_change', args=[obj.buyer.id])
        return format_html('<a href="{}">{}</a>', url, obj.buyer.name or obj.buyer.email)

    buyer_link.short_description = 'Buyer'
    buyer_link.admin_order_field = 'buyer__name'

    def total_amount_display(self, obj):
        """Display total amount with currency"""
        amount_str = f'{int(obj.total_amount):,}'
        return format_html(
            '<strong style="color: #E60549;">UGX {}</strong>',
            amount_str
        )

    total_amount_display.short_description = 'Total Amount'
    total_amount_display.admin_order_field = 'total_amount'

    def created_at_display(self, obj):
        """Display created date in readable format"""
        return obj.created_at.strftime('%b %d, %Y at %I:%M %p')

    created_at_display.short_description = 'Created'
    created_at_display.admin_order_field = 'created_at'

    def view_orders_link(self, obj):
        """Link to view all orders in this group"""
        url = f"/admin/orders/orderintent/?order_group__id__exact={obj.id}"
        return format_html(
            '<a class="button" href="{}">View {} Orders</a>',
            url,
            obj.total_orders
        )

    view_orders_link.short_description = 'Actions'

    def orders_summary(self, obj):
        """Display summary of orders in this group"""
        orders = obj.orders.select_related('merchant').all()

        html = '<div style="margin: 10px 0;">'
        for order in orders:
            status_color = {
                'NEW': '#2196F3',
                'CONTACTED': '#FF9800',
                'CONFIRMED': '#4CAF50',
                'COMPLETED': '#8BC34A',
                'CANCELLED': '#F44336',
            }.get(order.status, '#666')

            amount_str = f'{int(order.total_amount):,}'
            html += f'''
                <div style="padding: 8px; margin: 4px 0; background: #f5f5f5; border-radius: 4px;">
                    <strong>{order.order_number}</strong> - {order.merchant.display_name}<br>
                    <span style="color: {status_color}; font-weight: bold;">{order.get_status_display()}</span> | 
                    UGX {amount_str}
                </div>
            '''
        html += '</div>'

        return format_html(html)

    orders_summary.short_description = 'Orders in Group'

    def has_add_permission(self, request):
        """Prevent manual creation of order groups"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of order groups"""
        return False


@admin.register(OrderIntent)
class OrderIntentAdmin(admin.ModelAdmin):
    """Admin for OrderIntent model"""
    list_display = (
        'order_number_display',
        'buyer_link',
        'merchant_link',
        'status_badge',
        'total_amount_display',
        'items_count',
        'group_badge',
        'created_at_display',
    )
    list_filter = (
        'status',
        'created_at',
        'merchant',
        OrderGroupFilter,
    )
    search_fields = (
        'order_number',
        'buyer__email',
        'buyer__name',
        'merchant__display_name',
        'order_group__group_number',
    )
    readonly_fields = (
        'id',
        'order_number',
        'buyer',
        'merchant',
        'order_group',
        'total_amount',
        'created_at',
        'updated_at',
        'order_summary',
    )
    inlines = [OrderIntentItemInline]

    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'order_number', 'order_group', 'created_at', 'updated_at')
        }),
        ('Parties', {
            'fields': ('buyer', 'merchant')
        }),
        ('Delivery Details', {
            'fields': ('address', 'delivery_fee', 'expected_delivery_date', 'notes')
        }),
        ('Financial', {
            'fields': ('total_amount',)
        }),
        ('Status', {
            'fields': ('status', 'cancelled_by', 'cancellation_reason')
        }),
        ('Summary', {
            'fields': ('order_summary',),
            'classes': ('collapse',)
        }),
    )

    actions = [
        'mark_as_contacted',
        'mark_as_confirmed',
        'mark_as_completed',
        'cancel_orders',
    ]

    def order_number_display(self, obj):
        """Display order number with icon"""
        icon = '📦' if obj.order_group else '🛍️'
        return format_html('<strong>{} {}</strong>', icon, obj.order_number)

    order_number_display.short_description = 'Order Number'
    order_number_display.admin_order_field = 'order_number'

    def buyer_link(self, obj):
        """Link to buyer admin page"""
        url = reverse('admin:authentication_user_change', args=[obj.buyer.id])
        return format_html('<a href="{}">{}</a>', url, obj.buyer.name or obj.buyer.email)

    buyer_link.short_description = 'Buyer'
    buyer_link.admin_order_field = 'buyer__name'

    def merchant_link(self, obj):
        """Link to merchant admin page"""
        url = reverse('admin:merchants_merchant_change', args=[obj.merchant.id])
        return format_html('<a href="{}">{}</a>', url, obj.merchant.display_name)

    merchant_link.short_description = 'Merchant'
    merchant_link.admin_order_field = 'merchant__display_name'

    def status_badge(self, obj):
        """Display status with color badge"""
        colors = {
            'NEW': '#2196F3',
            'CONTACTED': '#FF9800',
            'CONFIRMED': '#4CAF50',
            'COMPLETED': '#8BC34A',
            'CANCELLED': '#F44336',
        }
        color = colors.get(obj.status, '#666')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def total_amount_display(self, obj):
        """Display total amount with currency"""
        amount_str = f'{int(obj.total_amount):,}'
        return format_html(
            '<strong style="color: #E60549;">UGX {}</strong>',
            amount_str
        )

    total_amount_display.short_description = 'Total'
    total_amount_display.admin_order_field = 'total_amount'

    def items_count(self, obj):
        """Display number of items in order"""
        count = obj.items.count()
        return format_html('<span title="Number of items">📋 {}</span>', count)

    items_count.short_description = 'Items'

    def group_badge(self, obj):
        """Display order group badge if applicable"""
        if obj.order_group:
            url = reverse('admin:orders_ordergroup_change', args=[obj.order_group.id])
            return format_html(
                '<a href="{}" style="background: #E3F2FD; color: #1976D2; '
                'padding: 4px 8px; border-radius: 8px; text-decoration: none; '
                'font-size: 11px;">📦 {}</a>',
                url,
                obj.order_group.group_number
            )
        return format_html('<span style="color: #999;">—</span>')

    group_badge.short_description = 'Group'

    def created_at_display(self, obj):
        """Display created date in readable format"""
        return obj.created_at.strftime('%b %d, %Y')

    created_at_display.short_description = 'Date'
    created_at_display.admin_order_field = 'created_at'

    def order_summary(self, obj):
        """Display detailed order summary"""
        items = obj.items.select_related('listing').all()

        html = '<div style="margin: 10px 0;">'
        html += '<h3>Order Items:</h3>'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '''
            <thead>
                <tr style="background: #f5f5f5;">
                    <th style="padding: 8px; text-align: left;">Item</th>
                    <th style="padding: 8px; text-align: center;">Qty</th>
                    <th style="padding: 8px; text-align: right;">Unit Price</th>
                    <th style="padding: 8px; text-align: right;">Total</th>
                </tr>
            </thead>
            <tbody>
        '''

        for item in items:
            unit_price_str = f'{int(item.unit_price):,}'
            total_price_str = f'{int(item.total_price):,}'
            html += f'''
                <tr style="border-bottom: 1px solid #e0e0e0;">
                    <td style="padding: 8px;">{item.listing.title}</td>
                    <td style="padding: 8px; text-align: center;">{item.quantity}</td>
                    <td style="padding: 8px; text-align: right;">UGX {unit_price_str}</td>
                    <td style="padding: 8px; text-align: right;">UGX {total_price_str}</td>
                </tr>
            '''

        html += '</tbody></table>'

        # Summary
        delivery_fee_str = f'{int(obj.delivery_fee or 0):,}'
        total_amount_str = f'{int(obj.total_amount):,}'
        html += '<div style="margin-top: 16px; padding: 12px; background: #f9f9f9; border-radius: 4px;">'
        html += f'<strong>Delivery Fee:</strong> UGX {delivery_fee_str}<br>'
        html += f'<strong style="font-size: 16px; color: #E60549;">Total Amount:</strong> <span style="font-size: 18px; color: #E60549;">UGX {total_amount_str}</span>'
        html += '</div>'

        html += '</div>'

        return format_html(html)

    order_summary.short_description = 'Order Details'

    # Admin Actions
    def mark_as_contacted(self, request, queryset):
        """Mark selected orders as contacted"""
        updated = queryset.filter(status='NEW').update(status='CONTACTED')
        self.message_user(request, f'{updated} order(s) marked as contacted.')

    mark_as_contacted.short_description = 'Mark as Contacted'

    def mark_as_confirmed(self, request, queryset):
        """Mark selected orders as confirmed"""
        updated = queryset.filter(status__in=['NEW', 'CONTACTED']).update(status='CONFIRMED')
        self.message_user(request, f'{updated} order(s) marked as confirmed.')

    mark_as_confirmed.short_description = 'Mark as Confirmed'

    def mark_as_completed(self, request, queryset):
        """Mark selected orders as completed"""
        updated = queryset.filter(status__in=['CONFIRMED']).update(status='COMPLETED')
        self.message_user(request, f'{updated} order(s) marked as completed.')

    mark_as_completed.short_description = 'Mark as Completed'

    def cancel_orders(self, request, queryset):
        """Cancel selected orders"""
        updated = queryset.filter(status__in=['NEW', 'CONTACTED', 'CONFIRMED']).update(
            status='CANCELLED',
            cancelled_by='ADMIN'
        )
        self.message_user(request, f'{updated} order(s) cancelled.')

    cancel_orders.short_description = 'Cancel Orders'

    def has_add_permission(self, request):
        """Prevent manual creation of orders"""
        return False

    def get_queryset(self, request):
        """Optimize queryset with prefetch"""
        queryset = super().get_queryset(request)
        return queryset.select_related(
            'buyer',
            'merchant',
            'address',
            'order_group'
        ).prefetch_related('items')


@admin.register(OrderIntentItem)
class OrderIntentItemAdmin(admin.ModelAdmin):
    """Admin for OrderIntentItem model"""
    list_display = (
        'listing_link',
        'order_link',
        'quantity',
        'unit_price_display',
        'total_price_display',
        'created_at_display',
    )
    list_filter = (
        'created_at',
    )
    search_fields = (
        'listing__title',
        'order_intent__order_number',
    )
    readonly_fields = (
        'id',
        'order_intent',
        'listing',
        'quantity',
        'unit_price',
        'total_price',
        'created_at',
    )

    fieldsets = (
        ('Item Information', {
            'fields': ('id', 'order_intent', 'listing', 'created_at')
        }),
        ('Pricing', {
            'fields': ('quantity', 'unit_price', 'total_price')
        }),
    )

    def listing_link(self, obj):
        """Link to listing admin page"""
        url = reverse('admin:listings_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)

    listing_link.short_description = 'Listing'
    listing_link.admin_order_field = 'listing__title'

    def order_link(self, obj):
        """Link to order admin page"""
        url = reverse('admin:orders_orderintent_change', args=[obj.order_intent.id])
        return format_html('<a href="{}">{}</a>', url, obj.order_intent.order_number)

    order_link.short_description = 'Order'
    order_link.admin_order_field = 'order_intent__order_number'

    def unit_price_display(self, obj):
        """Display unit price with currency"""
        price_str = f'{int(obj.unit_price):,}'
        return f'UGX {price_str}'

    unit_price_display.short_description = 'Unit Price'
    unit_price_display.admin_order_field = 'unit_price'

    def total_price_display(self, obj):
        """Display total price with currency"""
        price_str = f'{int(obj.total_price):,}'
        return format_html('<strong>UGX {}</strong>', price_str)

    total_price_display.short_description = 'Total'
    total_price_display.admin_order_field = 'total_price'

    def created_at_display(self, obj):
        """Display created date in readable format"""
        return obj.created_at.strftime('%b %d, %Y')

    created_at_display.short_description = 'Date'
    created_at_display.admin_order_field = 'created_at'

    def has_add_permission(self, request):
        """Prevent manual creation of order items"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of order items"""
        return False

    def get_queryset(self, request):
        """Optimize queryset with prefetch"""
        queryset = super().get_queryset(request)
        return queryset.select_related('order_intent', 'listing')