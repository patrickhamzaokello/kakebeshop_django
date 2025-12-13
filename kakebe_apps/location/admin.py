from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count

from .models import UserAddress, Location


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = (
        'label_badge',
        'user_link',
        'full_address',
        'is_default',
        'has_coordinates',
        'created_at'
    )
    list_filter = (
        'label',
        'is_default',
        'region',
        'district',
        'created_at'
    )
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'region',
        'district',
        'area',
        'landmark'
    )
    readonly_fields = ('id', 'created_at', 'map_link')
    fieldsets = (
        ('User Information', {
            'fields': ('id', 'user', 'label', 'is_default')
        }),
        ('Location Details', {
            'fields': (
                'region',
                'district',
                'area',
                'landmark'
            )
        }),
        ('Coordinates', {
            'fields': (
                'latitude',
                'longitude',
                'map_link'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    date_hierarchy = 'created_at'
    list_per_page = 25
    actions = ['make_default', 'unmake_default']

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user)

    user_link.short_description = "User"

    def label_badge(self, obj):
        colors = {
            'HOME': '#28a745',
            'WORK': '#007bff',
            'OTHER': '#6c757d',
        }
        color = colors.get(obj.label, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_label_display()
        )

    label_badge.short_description = "Label"

    def full_address(self, obj):
        return f"{obj.area}, {obj.district}, {obj.region}"

    full_address.short_description = "Address"

    def has_coordinates(self, obj):
        if obj.latitude and obj.longitude:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')

    has_coordinates.short_description = "Coordinates"
    has_coordinates.boolean = True

    def map_link(self, obj):
        if obj.latitude and obj.longitude:
            google_maps_url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            return format_html(
                '<a href="{}" target="_blank">View on Google Maps</a>',
                google_maps_url
            )
        return "No coordinates available"

    map_link.short_description = "Map"

    def make_default(self, request, queryset):
        for address in queryset:
            # Unset all other default addresses for this user
            UserAddress.objects.filter(user=address.user, is_default=True).update(is_default=False)
            # Set this one as default
            address.is_default = True
            address.save()
        self.message_user(request, f"{queryset.count()} address(es) set as default.")

    make_default.short_description = "Set as default address"

    def unmake_default(self, request, queryset):
        updated = queryset.update(is_default=False)
        self.message_user(request, f"{updated} address(es) unmarked as default.")

    unmake_default.short_description = "Remove default status"


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        'location_name',
        'region',
        'district',
        'area',
        'coordinates_display',
        'is_active',
        'usage_count',
        'created_at'
    )
    list_filter = (
        'is_active',
        'region',
        'district',
        'created_at'
    )
    search_fields = (
        'region',
        'district',
        'area',
        'address'
    )
    readonly_fields = ('id', 'created_at', 'map_link', 'usage_statistics')
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'is_active')
        }),
        ('Location Details', {
            'fields': (
                'region',
                'district',
                'area',
                'address'
            )
        }),
        ('Coordinates', {
            'fields': (
                'latitude',
                'longitude',
                'map_link'
            )
        }),
        ('Statistics', {
            'fields': ('usage_statistics',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    date_hierarchy = 'created_at'
    list_per_page = 25
    actions = ['activate_locations', 'deactivate_locations']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _listing_count=Count('listings', distinct=True)
        )
        return queryset

    def location_name(self, obj):
        return str(obj)

    location_name.short_description = "Location"
    location_name.admin_order_field = 'area'

    def coordinates_display(self, obj):
        return f"{obj.latitude}, {obj.longitude}"

    coordinates_display.short_description = "Coordinates"

    def usage_count(self, obj):
        count = getattr(obj, '_listing_count', 0)
        if count > 0:
            return format_html(
                '<span style="background-color: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
                count
            )
        return format_html('<span style="color: #999;">0</span>')

    usage_count.short_description = "Listings"
    usage_count.admin_order_field = '_listing_count'

    def map_link(self, obj):
        if obj.latitude and obj.longitude:
            google_maps_url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            return format_html(
                '<a href="{}" target="_blank" style="padding: 5px 10px; background-color: #4285f4; color: white; text-decoration: none; border-radius: 3px;">View on Google Maps</a>',
                google_maps_url
            )
        return "No coordinates available"

    map_link.short_description = "Map"

    def usage_statistics(self, obj):
        listing_count = getattr(obj, '_listing_count', 0)

        stats_html = f"""
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; background-color: #f5f5f5; font-weight: bold;">Listings using this location:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{listing_count}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; background-color: #f5f5f5; font-weight: bold;">Full Address:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{obj.address}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; background-color: #f5f5f5; font-weight: bold;">Geographic Area:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{obj.area}, {obj.district}, {obj.region}</td>
            </tr>
        </table>
        """

        return format_html(stats_html)

    usage_statistics.short_description = "Usage Statistics"

    def activate_locations(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} location(s) activated.")

    activate_locations.short_description = "Activate selected locations"

    def deactivate_locations(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} location(s) deactivated.")

    deactivate_locations.short_description = "Deactivate selected locations"