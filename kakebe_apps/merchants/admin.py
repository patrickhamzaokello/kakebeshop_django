from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Avg, Q

from .models import Merchant


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = (
        'display_name',
        'business_name',
        'user_link',
        'status_badge',
        'verified_badge',
        'rating_display',
        'listings_count',
        'business_contact',
        'created_at'
    )
    list_filter = (
        'status',
        'verified',
        'rating',
        'created_at',
        'verification_date'
    )
    search_fields = (
        'display_name',
        'business_name',
        'description',
        'user__email',
        'user__first_name',
        'user__last_name',
        'business_email',
        'business_phone'
    )
    readonly_fields = (
        'id',
        'created_at',
        'deleted_at',
        'logo_preview',
        'cover_image_preview',
        'merchant_statistics',
        'listing_summary'
    )
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id',
                'user',
                'display_name',
                'business_name',
                'description'
            )
        }),
        ('Contact Information', {
            'fields': (
                'business_phone',
                'business_email'
            )
        }),
        ('Branding', {
            'fields': (
                'logo',
                'logo_preview',
                'cover_image',
                'cover_image_preview'
            )
        }),
        ('Status & Verification', {
            'fields': (
                'status',
                'verified',
                'verification_date',
                'rating'
            )
        }),
        ('Statistics', {
            'fields': (
                'merchant_statistics',
                'listing_summary'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'deleted_at'
            ),
            'classes': ('collapse',)
        })
    )
    date_hierarchy = 'created_at'
    list_per_page = 25
    actions = [
        'verify_merchants',
        'unverify_merchants',
        'activate_merchants',
        'suspend_merchants',
        'ban_merchants'
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _listings_count=Count('listings', distinct=True),
            _active_listings_count=Count(
                'listings',
                filter=Q(listings__status='ACTIVE'),
                distinct=True
            )
        )
        return queryset

    def user_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user)

    user_link.short_description = "User Account"

    def status_badge(self, obj):
        colors = {
            'ACTIVE': '#28a745',
            'SUSPENDED': '#ffc107',
            'BANNED': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = "Status"

    def verified_badge(self, obj):
        if obj.verified:
            return format_html(
                '<span style="color: #28a745; font-size: 16px;" title="Verified on {}">✓ Verified</span>',
                obj.verification_date.strftime('%Y-%m-%d') if obj.verification_date else 'N/A'
            )
        return format_html('<span style="color: #dc3545;">✗ Not Verified</span>')

    verified_badge.short_description = "Verification"
    verified_badge.boolean = False

    def rating_display(self, obj):
        if obj.rating > 0:
            stars = '⭐' * int(obj.rating)
            return format_html(
                '<span title="{:.2f}/5.0">{} {:.1f}</span>',
                obj.rating,
                stars,
                obj.rating
            )
        return format_html('<span style="color: #999;">No ratings</span>')

    rating_display.short_description = "Rating"
    rating_display.admin_order_field = 'rating'

    def listings_count(self, obj):
        total = getattr(obj, '_listings_count', 0)
        active = getattr(obj, '_active_listings_count', 0)

        if total > 0:
            return format_html(
                '<span style="background-color: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 3px; font-weight: bold;" title="{} active out of {} total">{} / {}</span>',
                active,
                total,
                active,
                total
            )
        return format_html('<span style="color: #999;">0</span>')

    listings_count.short_description = "Listings (Active/Total)"
    listings_count.admin_order_field = '_listings_count'

    def business_contact(self, obj):
        contact_info = []
        if obj.business_email:
            contact_info.append(format_html(
                '<a href="mailto:{}">{}</a>',
                obj.business_email,
                obj.business_email
            ))
        if obj.business_phone:
            contact_info.append(obj.business_phone)

        if contact_info:
            return format_html('<br>'.join(contact_info))
        return format_html('<span style="color: #999;">No contact info</span>')

    business_contact.short_description = "Business Contact"

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 200px; border: 1px solid #ddd; border-radius: 4px;" />',
                obj.logo
            )
        return "No logo"

    logo_preview.short_description = "Logo Preview"

    def cover_image_preview(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="max-height: 150px; max-width: 400px; border: 1px solid #ddd; border-radius: 4px;" />',
                obj.cover_image
            )
        return "No cover image"

    cover_image_preview.short_description = "Cover Image Preview"

    def merchant_statistics(self, obj):
        total_listings = getattr(obj, '_listings_count', 0)
        active_listings = getattr(obj, '_active_listings_count', 0)

        # Calculate other statistics
        try:
            from kakebe_apps.listings.models import Listing
            listings = Listing.objects.filter(merchant=obj)

            total_views = sum(l.views_count for l in listings)
            total_contacts = sum(l.contact_count for l in listings)

            status_breakdown = {}
            for status_choice in Listing.STATUS_CHOICES:
                count = listings.filter(status=status_choice[0]).count()
                if count > 0:
                    status_breakdown[status_choice[1]] = count
        except:
            total_views = 0
            total_contacts = 0
            status_breakdown = {}

        stats_html = f"""
        <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
            <tr style="background-color: #f5f5f5;">
                <th colspan="2" style="padding: 10px; border: 1px solid #ddd; text-align: left; font-size: 14px;">Merchant Performance</th>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; width: 40%;">Total Listings:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{total_listings}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Active Listings:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{active_listings}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Total Views:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{total_views:,}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Total Contacts:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{total_contacts:,}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Rating:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{obj.rating:.2f} / 5.0</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Member Since:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{obj.created_at.strftime('%B %d, %Y')}</td>
            </tr>
        </table>
        """

        if status_breakdown:
            stats_html += """
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr style="background-color: #f5f5f5;">
                    <th colspan="2" style="padding: 10px; border: 1px solid #ddd; text-align: left; font-size: 14px;">Listing Status Breakdown</th>
                </tr>
            """
            for status_name, count in status_breakdown.items():
                stats_html += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; width: 40%;">{status_name}:</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{count}</td>
                </tr>
                """
            stats_html += "</table>"

        return format_html(stats_html)

    merchant_statistics.short_description = "Performance Statistics"

    def listing_summary(self, obj):
        try:
            from kakebe_apps.listings.models import Listing
            listings = Listing.objects.filter(merchant=obj).select_related('category').order_by('-created_at')[:5]

            if not listings:
                return format_html('<p style="color: #999;">No listings yet</p>')

            summary_html = """
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background-color: #f5f5f5;">
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Recent Listings</th>
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Status</th>
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Views</th>
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Created</th>
                </tr>
            """

            for listing in listings:
                listing_url = reverse('admin:listings_listing_change', args=[listing.id])
                status_colors = {
                    'ACTIVE': '#28a745',
                    'PENDING': '#ffc107',
                    'DRAFT': '#6c757d',
                    'CLOSED': '#6c757d',
                    'DEACTIVATED': '#dc3545',
                    'REJECTED': '#dc3545',
                }
                color = status_colors.get(listing.status, '#6c757d')

                summary_html += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <a href="{listing_url}">{listing.title}</a>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <span style="background-color: {color}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{listing.get_status_display()}</span>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{listing.views_count}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{listing.created_at.strftime('%Y-%m-%d')}</td>
                </tr>
                """

            summary_html += "</table>"

            total_count = Listing.objects.filter(merchant=obj).count()
            if total_count > 5:
                summary_html += f'<p style="margin-top: 10px; color: #666;"><em>Showing 5 of {total_count} total listings</em></p>'

            return format_html(summary_html)
        except:
            return format_html('<p style="color: #999;">Unable to load listings</p>')

    listing_summary.short_description = "Recent Listings"

    def verify_merchants(self, request, queryset):
        updated = queryset.update(verified=True, verification_date=timezone.now())
        self.message_user(request, f"{updated} merchant(s) verified successfully.")

    verify_merchants.short_description = "Verify selected merchants"

    def unverify_merchants(self, request, queryset):
        updated = queryset.update(verified=False, verification_date=None)
        self.message_user(request, f"{updated} merchant(s) unverified.")

    unverify_merchants.short_description = "Remove verification"

    def activate_merchants(self, request, queryset):
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f"{updated} merchant(s) activated.")

    activate_merchants.short_description = "Activate selected merchants"

    def suspend_merchants(self, request, queryset):
        updated = queryset.update(status='SUSPENDED')
        self.message_user(request, f"{updated} merchant(s) suspended.")

    suspend_merchants.short_description = "Suspend selected merchants"

    def ban_merchants(self, request, queryset):
        updated = queryset.update(status='BANNED')
        self.message_user(request, f"{updated} merchant(s) banned.")

    ban_merchants.short_description = "Ban selected merchants"