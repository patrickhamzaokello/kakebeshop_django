from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum, F, Q

from .models import (
    PromotionalCampaign,
    CampaignListing,
    CampaignCreative,
    CampaignPlacement
)


class CampaignListingInline(admin.TabularInline):
    model = CampaignListing
    extra = 1
    fields = ('listing', 'impressions', 'clicks', 'conversions', 'ctr_display', 'conversion_rate_display')
    readonly_fields = ('ctr_display', 'conversion_rate_display', 'impressions', 'clicks', 'conversions')
    autocomplete_fields = ('listing',)

    def ctr_display(self, obj):
        if obj.impressions > 0:
            ctr = (obj.clicks / obj.impressions) * 100
            return f"{ctr:.2f}%"
        return "0%"

    ctr_display.short_description = "CTR"

    def conversion_rate_display(self, obj):
        if obj.clicks > 0:
            rate = (obj.conversions / obj.clicks) * 100
            return f"{rate:.2f}%"
        return "0%"

    conversion_rate_display.short_description = "Conv. Rate"


class CampaignCreativeInline(admin.StackedInline):
    model = CampaignCreative
    extra = 0
    fields = (
        'creative_type',
        'title',
        'subtitle',
        'image',
        'thumbnail',
        'image_preview',
        'platform',
        'cta_text',
        'sort_order',
        'is_active',
        'start_date',
        'end_date'
    )
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 200px; border: 1px solid #ddd; border-radius: 4px;" />',
                obj.thumbnail
            )
        elif obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 200px; border: 1px solid #ddd; border-radius: 4px;" />',
                obj.image
            )
        return "No image"

    image_preview.short_description = "Preview"


@admin.register(PromotionalCampaign)
class PromotionalCampaignAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'campaign_type_badge',
        'status_badge',
        'date_range_display',
        'budget_display',
        'performance_summary',
        'listings_count',
        'created_at'
    )
    list_filter = (
        'status',
        'campaign_type',
        'start_date',
        'end_date',
        'created_at'
    )
    search_fields = (
        'name',
        'description'
    )
    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'campaign_performance',
        'duration_info'
    )
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id',
                'name',
                'description',
                'campaign_type'
            )
        }),
        ('Schedule & Budget', {
            'fields': (
                'start_date',
                'end_date',
                'duration_info',
                'budget',
                'status'
            )
        }),
        ('Performance', {
            'fields': ('campaign_performance',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    inlines = [CampaignCreativeInline, CampaignListingInline]
    date_hierarchy = 'start_date'
    list_per_page = 25
    actions = [
        'activate_campaigns',
        'pause_campaigns',
        'mark_as_completed',
        'duplicate_campaign'
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _listings_count=Sum('listings__id'),
            _total_impressions=Sum('listings__impressions'),
            _total_clicks=Sum('listings__clicks'),
            _total_conversions=Sum('listings__conversions')
        )
        return queryset

    def campaign_type_badge(self, obj):
        colors = {
            'FEATURED_LISTING': '#007bff',
            'BANNER': '#28a745',
            'PUSH_NOTIFICATION': '#ffc107',
            'EMAIL': '#6f42c1',
        }
        color = colors.get(obj.campaign_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.get_campaign_type_display()
        )

    campaign_type_badge.short_description = "Type"

    def status_badge(self, obj):
        colors = {
            'DRAFT': '#6c757d',
            'ACTIVE': '#28a745',
            'PAUSED': '#ffc107',
            'COMPLETED': '#17a2b8',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = "Status"

    def date_range_display(self, obj):
        now = timezone.now()
        start_str = obj.start_date.strftime('%Y-%m-%d')
        end_str = obj.end_date.strftime('%Y-%m-%d')

        if obj.end_date < now:
            status_icon = '🔴'
            status_text = 'Ended'
        elif obj.start_date > now:
            status_icon = '🟡'
            status_text = 'Upcoming'
        else:
            status_icon = '🟢'
            status_text = 'Running'

        return format_html(
            '{} {}<br><small>{} → {}</small>',
            status_icon,
            status_text,
            start_str,
            end_str
        )

    date_range_display.short_description = "Schedule"

    def budget_display(self, obj):
        if obj.budget:
            return format_html(
                '<span style="font-weight: bold; color: #28a745;">${:,.2f}</span>',
                obj.budget
            )
        return format_html('<span style="color: #999;">No budget set</span>')

    budget_display.short_description = "Budget"
    budget_display.admin_order_field = 'budget'

    def performance_summary(self, obj):
        impressions = getattr(obj, '_total_impressions', 0) or 0
        clicks = getattr(obj, '_total_clicks', 0) or 0
        conversions = getattr(obj, '_total_conversions', 0) or 0

        ctr = (clicks / impressions * 100) if impressions > 0 else 0

        return format_html(
            '<div style="font-size: 11px;">'
            '<div>👁️ {impressions:,}</div>'
            '<div>👆 {clicks:,} <span style="color: #666;">({ctr:.1f}%)</span></div>'
            '<div>✅ {conversions:,}</div>'
            '</div>',
            impressions=impressions,
            clicks=clicks,
            ctr=ctr,
            conversions=conversions
        )

    performance_summary.short_description = "Performance"

    def listings_count(self, obj):
        count = CampaignListing.objects.filter(campaign=obj).count()
        if count > 0:
            return format_html(
                '<span style="background-color: #e3f2fd; color: #1976d2; padding: 2px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
                count
            )
        return format_html('<span style="color: #999;">0</span>')

    listings_count.short_description = "Listings"

    def duration_info(self, obj):
        duration = obj.end_date - obj.start_date
        days = duration.days

        now = timezone.now()
        if obj.start_date > now:
            starts_in = (obj.start_date - now).days
            time_info = f"Starts in {starts_in} days"
        elif obj.end_date < now:
            ended_ago = (now - obj.end_date).days
            time_info = f"Ended {ended_ago} days ago"
        else:
            remaining = (obj.end_date - now).days
            time_info = f"{remaining} days remaining"

        info_html = f"""
        <div style="padding: 10px; background-color: #f5f5f5; border-radius: 4px;">
            <p><strong>Duration:</strong> {days} days</p>
            <p><strong>Status:</strong> {time_info}</p>
            <p><strong>Start:</strong> {obj.start_date.strftime('%B %d, %Y %I:%M %p')}</p>
            <p><strong>End:</strong> {obj.end_date.strftime('%B %d, %Y %I:%M %p')}</p>
        </div>
        """
        return format_html(info_html)

    duration_info.short_description = "Duration Information"

    def campaign_performance(self, obj):
        listings = CampaignListing.objects.filter(campaign=obj)

        total_impressions = sum(l.impressions for l in listings)
        total_clicks = sum(l.clicks for l in listings)
        total_conversions = sum(l.conversions for l in listings)

        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0

        cost_per_click = (obj.budget / total_clicks) if obj.budget and total_clicks > 0 else 0
        cost_per_conversion = (obj.budget / total_conversions) if obj.budget and total_conversions > 0 else 0

        performance_html = f"""
        <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
            <tr style="background-color: #f5f5f5;">
                <th colspan="2" style="padding: 10px; border: 1px solid #ddd; text-align: left; font-size: 14px;">Campaign Performance Metrics</th>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; width: 40%;">Total Impressions:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{total_impressions:,}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Total Clicks:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{total_clicks:,}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Total Conversions:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{total_conversions:,}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Click-Through Rate (CTR):</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{ctr:.2f}%</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Conversion Rate:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{conversion_rate:.2f}%</td>
            </tr>
        """

        if obj.budget:
            performance_html += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Budget:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${obj.budget:,.2f}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Cost Per Click (CPC):</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${cost_per_click:.2f}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Cost Per Conversion:</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${cost_per_conversion:.2f}</td>
            </tr>
            """

        performance_html += "</table>"

        # Top performing listings
        if listings:
            top_listings = sorted(listings, key=lambda x: x.clicks, reverse=True)[:5]
            performance_html += """
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr style="background-color: #f5f5f5;">
                    <th colspan="4" style="padding: 10px; border: 1px solid #ddd; text-align: left; font-size: 14px;">Top Performing Listings</th>
                </tr>
                <tr style="background-color: #fafafa;">
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Listing</th>
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Impressions</th>
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Clicks</th>
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">CTR</th>
                </tr>
            """

            for listing in top_listings:
                listing_url = reverse('admin:listings_listing_change', args=[listing.listing.id])
                listing_ctr = (listing.clicks / listing.impressions * 100) if listing.impressions > 0 else 0
                performance_html += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">
                        <a href="{listing_url}">{listing.listing.title}</a>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{listing.impressions:,}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{listing.clicks:,}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{listing_ctr:.2f}%</td>
                </tr>
                """

            performance_html += "</table>"

        return format_html(performance_html)

    campaign_performance.short_description = "Detailed Performance"

    def activate_campaigns(self, request, queryset):
        updated = queryset.update(status='ACTIVE')
        self.message_user(request, f"{updated} campaign(s) activated.")

    activate_campaigns.short_description = "Activate selected campaigns"

    def pause_campaigns(self, request, queryset):
        updated = queryset.update(status='PAUSED')
        self.message_user(request, f"{updated} campaign(s) paused.")

    pause_campaigns.short_description = "Pause selected campaigns"

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='COMPLETED')
        self.message_user(request, f"{updated} campaign(s) marked as completed.")

    mark_as_completed.short_description = "Mark as completed"


@admin.register(CampaignListing)
class CampaignListingAdmin(admin.ModelAdmin):
    list_display = (
        'campaign_link',
        'listing_link',
        'performance_metrics',
        'ctr_display',
        'conversion_rate_display',
        'created_at'
    )
    list_filter = (
        'campaign__status',
        'campaign__campaign_type',
        'created_at'
    )
    search_fields = (
        'campaign__name',
        'listing__title'
    )
    readonly_fields = (
        'id',
        'impressions',
        'clicks',
        'conversions',
        'created_at',
        'performance_chart'
    )
    fieldsets = (
        ('Campaign & Listing', {
            'fields': ('id', 'campaign', 'listing')
        }),
        ('Performance Metrics', {
            'fields': (
                'impressions',
                'clicks',
                'conversions',
                'performance_chart'
            )
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    autocomplete_fields = ('campaign', 'listing')
    date_hierarchy = 'created_at'

    def campaign_link(self, obj):
        url = reverse('admin:promotions_promotionalcampaign_change', args=[obj.campaign.id])
        return format_html('<a href="{}">{}</a>', url, obj.campaign.name)

    campaign_link.short_description = "Campaign"

    def listing_link(self, obj):
        url = reverse('admin:listings_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)

    listing_link.short_description = "Listing"

    def performance_metrics(self, obj):
        return format_html(
            '<div style="font-size: 11px;">'
            '<div>👁️ {}</div>'
            '<div>👆 {}</div>'
            '<div>✅ {}</div>'
            '</div>',
            f"{obj.impressions:,}",
            f"{obj.clicks:,}",
            f"{obj.conversions:,}"
        )

    performance_metrics.short_description = "Metrics"

    def ctr_display(self, obj):
        if obj.impressions > 0:
            ctr = (obj.clicks / obj.impressions) * 100
            color = '#28a745' if ctr > 2 else '#ffc107' if ctr > 1 else '#dc3545'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.2f}%</span>',
                color,
                ctr
            )
        return "0%"

    ctr_display.short_description = "CTR"

    def conversion_rate_display(self, obj):
        if obj.clicks > 0:
            rate = (obj.conversions / obj.clicks) * 100
            color = '#28a745' if rate > 5 else '#ffc107' if rate > 2 else '#dc3545'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.2f}%</span>',
                color,
                rate
            )
        return "0%"

    conversion_rate_display.short_description = "Conv. Rate"

    def performance_chart(self, obj):
        ctr = (obj.clicks / obj.impressions * 100) if obj.impressions > 0 else 0
        conv_rate = (obj.conversions / obj.clicks * 100) if obj.clicks > 0 else 0

        chart_html = f"""
        <div style="padding: 15px; background-color: #f5f5f5; border-radius: 4px;">
            <h3 style="margin-top: 0;">Performance Overview</h3>
            <div style="margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span><strong>Impressions:</strong></span>
                    <span>{obj.impressions:,}</span>
                </div>
                <div style="background-color: #e0e0e0; height: 20px; border-radius: 3px; overflow: hidden;">
                    <div style="background-color: #2196f3; height: 100%; width: 100%;"></div>
                </div>
            </div>
            <div style="margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span><strong>Clicks:</strong></span>
                    <span>{obj.clicks:,} ({ctr:.2f}% CTR)</span>
                </div>
                <div style="background-color: #e0e0e0; height: 20px; border-radius: 3px; overflow: hidden;">
                    <div style="background-color: #4caf50; height: 100%; width: {min(ctr * 10, 100)}%;"></div>
                </div>
            </div>
            <div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span><strong>Conversions:</strong></span>
                    <span>{obj.conversions:,} ({conv_rate:.2f}% rate)</span>
                </div>
                <div style="background-color: #e0e0e0; height: 20px; border-radius: 3px; overflow: hidden;">
                    <div style="background-color: #ff9800; height: 100%; width: {min(conv_rate * 5, 100)}%;"></div>
                </div>
            </div>
        </div>
        """
        return format_html(chart_html)

    performance_chart.short_description = "Performance Visualization"


class CampaignPlacementInline(admin.TabularInline):
    model = CampaignPlacement
    extra = 1
    fields = ('placement', 'target_type', 'target_id', 'target_url')


@admin.register(CampaignCreative)
class CampaignCreativeAdmin(admin.ModelAdmin):
    list_display = (
        'campaign_link',
        'creative_type_badge',
        'title',
        'platform_badge',
        'image_preview_small',
        'is_active',
        'sort_order',
        'date_range_display'
    )
    list_filter = (
        'creative_type',
        'platform',
        'is_active',
        'created_at'
    )
    search_fields = (
        'campaign__name',
        'title',
        'subtitle',
        'cta_text'
    )
    readonly_fields = (
        'id',
        'created_at',
        'image_preview_large'
    )
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id',
                'campaign',
                'creative_type',
                'platform',
                'is_active'
            )
        }),
        ('Content', {
            'fields': (
                'title',
                'subtitle',
                'cta_text'
            )
        }),
        ('Media', {
            'fields': (
                'image',
                'thumbnail',
                'image_preview_large'
            )
        }),
        ('Settings', {
            'fields': (
                'sort_order',
                'start_date',
                'end_date'
            )
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    inlines = [CampaignPlacementInline]
    list_editable = ('sort_order', 'is_active')
    date_hierarchy = 'created_at'
    actions = ['activate_creatives', 'deactivate_creatives']

    def campaign_link(self, obj):
        url = reverse('admin:promotions_promotionalcampaign_change', args=[obj.campaign.id])
        return format_html('<a href="{}">{}</a>', url, obj.campaign.name)

    campaign_link.short_description = "Campaign"

    def creative_type_badge(self, obj):
        colors = {
            'SLIDER': '#007bff',
            'BANNER': '#28a745',
            'POPUP': '#ffc107',
        }
        color = colors.get(obj.creative_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.get_creative_type_display()
        )

    creative_type_badge.short_description = "Type"

    def platform_badge(self, obj):
        icons = {
            'ANDROID': '🤖',
            'IOS': '🍎',
            'WEB': '🌐',
            'ALL': '📱',
        }
        icon = icons.get(obj.platform, '📱')
        return format_html(
            '<span title="{}">{} {}</span>',
            obj.get_platform_display(),
            icon,
            obj.get_platform_display()
        )

    platform_badge.short_description = "Platform"

    def image_preview_small(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 80px; border-radius: 3px;" />',
                obj.thumbnail
            )
        elif obj.image:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 80px; border-radius: 3px;" />',
                obj.image
            )
        return "No image"

    image_preview_small.short_description = "Preview"

    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 600px; border: 1px solid #ddd; border-radius: 4px;" />',
                obj.image
            )
        return "No image"

    image_preview_large.short_description = "Image Preview"

    def date_range_display(self, obj):
        if obj.start_date and obj.end_date:
            return format_html(
                '<small>{}<br>to<br>{}</small>',
                obj.start_date.strftime('%Y-%m-%d'),
                obj.end_date.strftime('%Y-%m-%d')
            )
        elif obj.start_date:
            return format_html('<small>From {}</small>', obj.start_date.strftime('%Y-%m-%d'))
        elif obj.end_date:
            return format_html('<small>Until {}</small>', obj.end_date.strftime('%Y-%m-%d'))
        return format_html('<span style="color: #999;">No schedule</span>')

    date_range_display.short_description = "Schedule"

    def activate_creatives(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} creative(s) activated.")

    activate_creatives.short_description = "Activate selected creatives"

    def deactivate_creatives(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} creative(s) deactivated.")

    deactivate_creatives.short_description = "Deactivate selected creatives"


@admin.register(CampaignPlacement)
class CampaignPlacementAdmin(admin.ModelAdmin):
    list_display = (
        'creative_link',
        'placement_badge',
        'target_display',
        'created_at'
    )
    list_filter = (
        'placement',
        'target_type',
        'created_at'
    )
    search_fields = (
        'creative__campaign__name',
        'creative__title',
        'target_url'
    )
    readonly_fields = (
        'id',
        'created_at'
    )
    fieldsets = (
        ('Creative & Placement', {
            'fields': (
                'id',
                'creative',
                'placement'
            )
        }),
        ('Target Configuration', {
            'fields': (
                'target_type',
                'target_id',
                'target_url'
            )
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    date_hierarchy = 'created_at'

    def creative_link(self, obj):
        url = reverse('admin:promotions_campaigncreative_change', args=[obj.creative.id])
        return format_html('<a href="{}">{}</a>', url, str(obj.creative))

    creative_link.short_description = "Creative"

    def placement_badge(self, obj):
        return format_html(
            '<span style="background-color: #17a2b8; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            obj.get_placement_display()
        )

    placement_badge.short_description = "Placement"

    def target_display(self, obj):
        if obj.target_type == 'URL' and obj.target_url:
            return format_html(
                '🔗 <a href="{}" target="_blank">{}</a>',
                obj.target_url,
                obj.target_url[:50] + '...' if len(obj.target_url) > 50 else obj.target_url
            )
        elif obj.target_type == 'NONE':
            return format_html('<span style="color: #999;">No action</span>')
        elif obj.target_id:
            return format_html(
                '{} <code>{}</code>',
                obj.get_target_type_display)