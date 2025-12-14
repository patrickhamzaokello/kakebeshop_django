from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Avg, F
import json
from .models import (
    Favorite, SavedSearch, Conversation, Message, Notification,
    ListingReview, MerchantReview, MerchantScore, Report,
    FollowUpRule, FollowUpLog, AdminUser, AuditLog,
    ApiUsage, ActivityLog, OnboardingStatus, UserIntent, PushToken
)


# ========== Inlines ==========
class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender_link', 'message_preview', 'sent_at', 'is_read')
    fields = ('sender_link', 'message_preview', 'sent_at', 'is_read')
    can_delete = False
    show_change_link = True
    verbose_name_plural = "Messages"

    def has_add_permission(self, request, obj=None):
        return False

    def sender_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.sender.id])
        return format_html('<a href="{}">{}</a>', url, obj.sender.name)

    sender_link.short_description = "Sender"

    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message

    message_preview.short_description = "Message"


class FollowUpLogInline(admin.TabularInline):
    model = FollowUpLog
    extra = 0
    readonly_fields = ('user_link', 'rule_name', 'status', 'sent_at')
    fields = ('user_link', 'rule_name', 'status', 'sent_at')
    can_delete = False
    show_change_link = True
    verbose_name_plural = "Follow-up Logs"

    def has_add_permission(self, request, obj=None):
        return False

    def user_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = "User"

    def rule_name(self, obj):
        return obj.rule.name

    rule_name.short_description = "Rule"


# ========== Favorite Admin ==========
@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'listing_link', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__name', 'user__email', 'listing__title')
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'user_link', 'listing_link')

    def user_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = "User"
    user_link.admin_order_field = 'user__name'

    def listing_link(self, obj):
        url = reverse('admin:listings_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title[:50])

    listing_link.short_description = "Listing"
    listing_link.admin_order_field = 'listing__title'


# ========== SavedSearch Admin ==========
@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'name', 'notification_badge', 'created_at', 'last_notified_at')
    list_filter = ('notification_enabled', 'created_at')
    search_fields = ('user__name', 'user__email', 'name', 'search_query')
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'user_link', 'formatted_filters')
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user_link', 'name')
        }),
        ('Search Details', {
            'fields': ('search_query', 'formatted_filters')
        }),
        ('Notifications', {
            'fields': ('notification_enabled', 'last_notified_at')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def user_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = "User"

    def notification_badge(self, obj):
        if obj.notification_enabled:
            return format_html(
                '<span style="background: #4CAF50; color: white; padding: 2px 6px; border-radius: 3px;">✓</span>'
            )
        return "—"

    notification_badge.short_description = "Notifications"

    def formatted_filters(self, obj):
        try:
            filters = json.dumps(obj.filters, indent=2, cls=DjangoJSONEncoder)
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>', filters)
        except:
            return str(obj.filters)

    formatted_filters.short_description = "Filters (Formatted)"


# ========== Conversation Admin ==========
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('buyer_link', 'seller_link', 'listing_preview', 'status_badge', 'last_message', 'created_at')
    list_filter = ('status', 'created_at', 'last_message_at')
    search_fields = ('buyer__name', 'seller__name', 'listing__title')
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'updated_at', 'buyer_link', 'seller_link', 'listing_link', 'message_count')
    fieldsets = (
        ('Participants', {
            'fields': ('buyer_link', 'seller_link')
        }),
        ('Context', {
            'fields': ('listing_link', 'order_intent_link')
        }),
        ('Status', {
            'fields': ('status', 'last_message_at', 'message_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    inlines = [MessageInline]

    def buyer_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.buyer.id])
        return format_html('<a href="{}">{}</a>', url, obj.buyer.name)

    buyer_link.short_description = "Buyer"

    def seller_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.seller.id])
        return format_html('<a href="{}">{}</a>', url, obj.seller.name)

    seller_link.short_description = "Seller"

    def listing_link(self, obj):
        if obj.listing:
            url = reverse('admin:listings_listing_change', args=[obj.listing.id])
            return format_html('<a href="{}">{}</a>', url, obj.listing.title)
        return "—"

    listing_link.short_description = "Listing"

    def listing_preview(self, obj):
        if obj.listing:
            return obj.listing.title[:30] + "..." if len(obj.listing.title) > 30 else obj.listing.title
        return "—"

    listing_preview.short_description = "Listing"

    def order_intent_link(self, obj):
        if obj.order_intent:
            url = reverse('admin:orders_orderintent_change', args=[obj.order_intent.id])
            return format_html('<a href="{}">Order #{}</a>', url, str(obj.order_intent.id)[:8])
        return "—"

    order_intent_link.short_description = "Order Intent"

    def status_badge(self, obj):
        color_map = {
            'ACTIVE': 'green',
            'ARCHIVED': 'gray',
            'BLOCKED': 'red'
        }
        color = color_map.get(obj.status, 'blue')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )

    status_badge.short_description = "Status"

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = "Total Messages"

    def last_message(self, obj):
        last_msg = obj.messages.order_by('-sent_at').first()
        if last_msg:
            time_diff = timezone.now() - last_msg.sent_at
            if time_diff.days > 0:
                return f"{time_diff.days}d ago"
            elif time_diff.seconds > 3600:
                return f"{time_diff.seconds // 3600}h ago"
            elif time_diff.seconds > 60:
                return f"{time_diff.seconds // 60}m ago"
            else:
                return "Just now"
        return "No messages"

    last_message.short_description = "Last Activity"


# ========== Message Admin ==========
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender_link', 'conversation_link', 'message_preview', 'read_status', 'sent_at')
    list_filter = ('is_read', 'sent_at')
    search_fields = ('sender__name', 'conversation__buyer__name', 'conversation__seller__name', 'message')
    list_per_page = 25
    readonly_fields = ('id', 'sent_at', 'read_at', 'sender_link', 'conversation_link')
    fieldsets = (
        ('Message Details', {
            'fields': ('sender_link', 'conversation_link', 'message', 'attachment')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Timestamps', {
            'fields': ('sent_at',),
            'classes': ('collapse',)
        })
    )

    def sender_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.sender.id])
        return format_html('<a href="{}">{}</a>', url, obj.sender.name)

    sender_link.short_description = "Sender"

    def conversation_link(self, obj):
        url = reverse('admin:communications_conversation_change', args=[obj.conversation.id])
        participants = f"{obj.conversation.buyer.name} ↔ {obj.conversation.seller.name}"
        return format_html('<a href="{}">{}</a>', url, participants[:50])

    conversation_link.short_description = "Conversation"

    def message_preview(self, obj):
        return obj.message[:60] + "..." if len(obj.message) > 60 else obj.message

    message_preview.short_description = "Message"

    def read_status(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: orange;">● Unread</span>')

    read_status.short_description = "Status"


# ========== Notification Admin ==========
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'type_badge', 'title_preview', 'read_status', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__name', 'title', 'body')
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'user_link', 'formatted_data')
    fieldsets = (
        ('Recipient', {
            'fields': ('user_link',)
        }),
        ('Notification Content', {
            'fields': ('type', 'title', 'body')
        }),
        ('Additional Data', {
            'fields': ('formatted_data', 'action_url'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def user_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = "User"

    def type_badge(self, obj):
        colors = {
            'NEW_MESSAGE': '#2196F3',
            'ORDER_UPDATE': '#4CAF50',
            'LISTING_APPROVED': '#8BC34A',
            'LISTING_REJECTED': '#F44336',
            'NEW_REVIEW': '#FF9800',
            'FOLLOW_UP': '#9C27B0',
            'SYSTEM': '#607D8B',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            colors.get(obj.type, '#999'), obj.get_type_display()
        )

    type_badge.short_description = "Type"

    def title_preview(self, obj):
        return obj.title[:40] + "..." if len(obj.title) > 40 else obj.title

    title_preview.short_description = "Title"

    def read_status(self, obj):
        if obj.is_read:
            return format_html('<span style="color: #999;">✓</span>')
        return format_html('<span style="color: #2196F3; font-weight: bold;">●</span>')

    read_status.short_description = "Read"

    def formatted_data(self, obj):
        if obj.data:
            try:
                formatted = json.dumps(obj.data, indent=2, cls=DjangoJSONEncoder)
                return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>',
                                   formatted)
            except:
                return str(obj.data)
        return "No additional data"

    formatted_data.short_description = "Data (JSON)"


# ========== ListingReview Admin ==========
@admin.register(ListingReview)
class ListingReviewAdmin(admin.ModelAdmin):
    list_display = ('listing_link', 'rating_stars', 'user_link', 'comment_preview', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('listing__title', 'user__name', 'comment')
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'updated_at', 'listing_link', 'user_link', 'order_intent_link')
    fieldsets = (
        ('Review Details', {
            'fields': ('listing_link', 'user_link', 'rating', 'comment')
        }),
        ('Context', {
            'fields': ('order_intent_link',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def listing_link(self, obj):
        url = reverse('admin:listings_listing_change', args=[obj.listing.id])
        return format_html('<a href="{}">{}</a>', url, obj.listing.title)

    listing_link.short_description = "Listing"

    def user_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = "User"

    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: #FFD700; font-size: 1.2em;">{}</span>', stars)

    rating_stars.short_description = "Rating"
    rating_stars.admin_order_field = 'rating'

    def comment_preview(self, obj):
        if obj.comment:
            return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
        return "—"

    comment_preview.short_description = "Comment"

    def order_intent_link(self, obj):
        if obj.order_intent:
            url = reverse('admin:orders_orderintent_change', args=[obj.order_intent.id])
            return format_html('<a href="{}">Order #{}</a>', url, str(obj.order_intent.id)[:8])
        return "—"

    order_intent_link.short_description = "Order Intent"


# ========== MerchantReview Admin ==========
@admin.register(MerchantReview)
class MerchantReviewAdmin(admin.ModelAdmin):
    list_display = ('merchant_link', 'rating_stars', 'user_link', 'comment_preview', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('merchant__display_name', 'user__name', 'comment')
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'updated_at', 'merchant_link', 'user_link', 'order_intent_link')
    fieldsets = (
        ('Review Details', {
            'fields': ('merchant_link', 'user_link', 'rating', 'comment')
        }),
        ('Context', {
            'fields': ('order_intent_link',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def merchant_link(self, obj):
        url = reverse('admin:merchants_merchant_change', args=[obj.merchant.id])
        return format_html('<a href="{}">{}</a>', url, obj.merchant.display_name)

    merchant_link.short_description = "Merchant"
    merchant_link.admin_order_field = 'merchant__display_name'

    def user_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = "User"
    user_link.admin_order_field = 'user__name'

    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: #FFD700; font-size: 1.2em;">{}</span>', stars)

    rating_stars.short_description = "Rating"
    rating_stars.admin_order_field = 'rating'

    def comment_preview(self, obj):
        if obj.comment:
            return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
        return "—"

    comment_preview.short_description = "Comment"

    def order_intent_link(self, obj):
        if obj.order_intent:
            url = reverse('admin:orders_orderintent_change', args=[obj.order_intent.id])
            return format_html('<a href="{}">Order #{}</a>', url, str(obj.order_intent.id)[:8])
        return "—"

    order_intent_link.short_description = "Order Intent"


# ========== MerchantScore Admin ==========
@admin.register(MerchantScore)
class MerchantScoreAdmin(admin.ModelAdmin):
    list_display = ('merchant_link', 'score_badge', 'response_rate', 'completed_orders', 'last_calculated')
    list_filter = ('score',)
    search_fields = ('merchant__display_name',)
    list_per_page = 25
    readonly_fields = ('merchant_link', 'last_calculated', 'score_breakdown')
    fieldsets = (
        ('Merchant', {
            'fields': ('merchant_link',)
        }),
        ('Performance Metrics', {
            'fields': (
                'active_listing_count',
                'total_listing_count',
                'response_rate',
                'average_response_time_minutes'
            )
        }),
        ('Order Metrics', {
            'fields': ('completed_orders', 'cancelled_orders', 'report_count')
        }),
        ('Score Summary', {
            'fields': ('score', 'score_breakdown', 'last_calculated'),
            'classes': ('wide',)
        })
    )

    def merchant_link(self, obj):
        url = reverse('admin:merchants_merchant_change', args=[obj.merchant.id])
        return format_html('<a href="{}">{}</a>', url, obj.merchant.display_name)

    merchant_link.short_description = "Merchant"

    def score_badge(self, obj):
        color = '#4CAF50' if obj.score >= 4.0 else '#FF9800' if obj.score >= 3.0 else '#F44336'
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 4px; font-weight: bold;">{:.1f}</span>',
            color, obj.score
        )

    score_badge.short_description = "Score"
    score_badge.admin_order_field = 'score'

    def response_rate(self, obj):
        return f"{obj.response_rate:.1%}"

    response_rate.short_description = "Response Rate"

    def score_breakdown(self, obj):
        breakdown = [
            f"Active Listings: {obj.active_listing_count}",
            f"Total Listings: {obj.total_listing_count}",
            f"Response Rate: {obj.response_rate:.1%}",
            f"Avg Response Time: {obj.average_response_time_minutes} mins",
            f"Completed Orders: {obj.completed_orders}",
            f"Cancelled Orders: {obj.cancelled_orders}",
            f"Reports: {obj.report_count}"
        ]
        return format_html('<br>'.join(breakdown))

    score_breakdown.short_description = "Score Breakdown"


# ========== Report Admin ==========
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter_link', 'report_target', 'reason_badge', 'status_badge', 'created_at', 'reviewed_by_link')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('reporter__name', 'listing__title', 'merchant__display_name', 'description')
    list_per_page = 25
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'reporter_link',
        'listing_link', 'merchant_link', 'reported_user_link'
    )
    fieldsets = (
        ('Report Details', {
            'fields': ('reporter_link', 'reason', 'description')
        }),
        ('Report Target', {
            'fields': ('listing_link', 'merchant_link', 'reported_user_link')
        }),
        ('Review Status', {
            'fields': ('status', 'reviewed_by_link', 'review_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def reporter_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.reporter.id])
        return format_html('<a href="{}">{}</a>', url, obj.reporter.name)

    reporter_link.short_description = "Reporter"

    def report_target(self, obj):
        if obj.listing:
            return f"Listing: {obj.listing.title[:30]}"
        elif obj.merchant:
            return f"Merchant: {obj.merchant.display_name}"
        elif obj.reported_user:
            return f"User: {obj.reported_user.name}"
        return "Unknown"

    report_target.short_description = "Target"

    def listing_link(self, obj):
        if obj.listing:
            url = reverse('admin:listings_listing_change', args=[obj.listing.id])
            return format_html('<a href="{}">{}</a>', url, obj.listing.title)
        return "—"

    listing_link.short_description = "Listing"

    def merchant_link(self, obj):
        if obj.merchant:
            url = reverse('admin:merchants_merchant_change', args=[obj.merchant.id])
            return format_html('<a href="{}">{}</a>', url, obj.merchant.display_name)
        return "—"

    merchant_link.short_description = "Merchant"

    def reported_user_link(self, obj):
        if obj.reported_user:
            url = reverse('admin:authentication_user_change', args=[obj.reported_user.id])
            return format_html('<a href="{}">{}</a>', url, obj.reported_user.name)
        return "—"

    reported_user_link.short_description = "Reported User"

    def reason_badge(self, obj):
        colors = {
            'SPAM': '#FF9800',
            'INAPPROPRIATE': '#F44336',
            'SCAM': '#9C27B0',
            'FAKE': '#607D8B',
            'OFFENSIVE': '#795548',
            'OTHER': '#9E9E9E',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            colors.get(obj.reason, '#999'), obj.get_reason_display()
        )

    reason_badge.short_description = "Reason"

    def status_badge(self, obj):
        colors = {
            'PENDING': '#FF9800',
            'UNDER_REVIEW': '#2196F3',
            'RESOLVED': '#4CAF50',
            'DISMISSED': '#9E9E9E',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#999'), obj.get_status_display()
        )

    status_badge.short_description = "Status"

    def reviewed_by_link(self, obj):
        if obj.reviewed_by:
            url = reverse('admin:communications_adminuser_change', args=[obj.reviewed_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.reviewed_by.user.name)
        return "—"

    reviewed_by_link.short_description = "Reviewed By"


# ========== FollowUpRule Admin ==========
@admin.register(FollowUpRule)
class FollowUpRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'trigger_type', 'notification_type', 'delay_minutes', 'active_badge', 'created_at')
    list_filter = ('trigger_type', 'notification_type', 'is_active')
    search_fields = ('name', 'message_template')
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Rule Details', {
            'fields': ('name', 'is_active')
        }),
        ('Trigger Configuration', {
            'fields': ('trigger_type', 'trigger_status', 'delay_minutes')
        }),
        ('Notification Content', {
            'fields': ('notification_type', 'message_template')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background: #4CAF50; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">Active</span>'
            )
        return format_html(
            '<span style="background: #9E9E9E; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">Inactive</span>'
        )

    active_badge.short_description = "Status"


# ========== FollowUpLog Admin ==========
@admin.register(FollowUpLog)
class FollowUpLogAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'rule_type', 'status_badge', 'sent_at')
    list_filter = ('status', 'sent_at', 'rule__trigger_type')
    search_fields = ('user__name', 'rule__name', 'error_message')
    list_per_page = 25
    readonly_fields = ('id', 'sent_at', 'user_link', 'rule_link', 'order_intent_link', 'listing_link')
    inlines = []

    def user_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = "User"

    def rule_type(self, obj):
        return obj.rule.trigger_type

    rule_type.short_description = "Trigger Type"

    def rule_link(self, obj):
        url = reverse('admin:communications_followuprule_change', args=[obj.rule.id])
        return format_html('<a href="{}">{}</a>', url, obj.rule.name)

    rule_link.short_description = "Rule"

    def status_badge(self, obj):
        colors = {
            'SENT': '#4CAF50',
            'FAILED': '#F44336',
            'SKIPPED': '#FF9800',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#999'), obj.get_status_display()
        )

    status_badge.short_description = "Status"

    def order_intent_link(self, obj):
        if obj.order_intent:
            url = reverse('admin:orders_orderintent_change', args=[obj.order_intent.id])
            return format_html('<a href="{}">Order #{}</a>', url, str(obj.order_intent.id)[:8])
        return "—"

    order_intent_link.short_description = "Order Intent"

    def listing_link(self, obj):
        if obj.listing:
            url = reverse('admin:listings_listing_change', args=[obj.listing.id])
            return format_html('<a href="{}">{}</a>', url, obj.listing.title)
        return "—"

    listing_link.short_description = "Listing"


# ========== AdminUser Admin ==========
@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'role_badge', 'active_badge', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('user__name', 'user__email')
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'updated_at', 'user_link', 'formatted_permissions')
    fieldsets = (
        ('Admin Profile', {
            'fields': ('user_link', 'role', 'is_active')
        }),
        ('Permissions', {
            'fields': ('formatted_permissions',),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def user_link(self, obj):
        url = reverse('admin:authentication_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.name)

    user_link.short_description = "User"

    def role_badge(self, obj):
        colors = {
            'SUPER_ADMIN': '#F44336',
            'MODERATOR': '#2196F3',
            'SUPPORT': '#4CAF50',
            'FINANCE': '#9C27B0',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            colors.get(obj.role, '#999'), obj.get_role_display()
        )

    role_badge.short_description = "Role"

    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background: #4CAF50; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">Active</span>'
            )
        return format_html(
            '<span style="background: #9E9E9E; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">Inactive</span>'
        )

    active_badge.short_description = "Status"

    def formatted_permissions(self, obj):
        if obj.permissions:
            try:
                formatted = json.dumps(obj.permissions, indent=2, cls=DjangoJSONEncoder)
                return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>',
                                   formatted)
            except:
                return str(obj.permissions)
        return "No specific permissions"

    formatted_permissions.short_description = "Permissions (JSON)"


# ========== AuditLog Admin ==========
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('admin_link', 'action', 'entity_link', 'created_at', 'ip_preview')
    list_filter = ('entity_type', 'created_at')
    search_fields = ('admin__user__name', 'action', 'entity_type', 'entity_id')
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'admin_link', 'formatted_changes', 'formatted_old_values',
                       'formatted_new_values')
    fieldsets = (
        ('Audit Details', {
            'fields': ('admin_link', 'action', 'entity_type', 'entity_id')
        }),
        ('Change Data', {
            'fields': ('formatted_old_values', 'formatted_new_values'),
            'classes': ('wide',)
        }),
        ('Technical Info', {
            'fields': ('formatted_changes', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def admin_link(self, obj):
        if obj.admin:
            url = reverse('admin:communications_adminuser_change', args=[obj.admin.id])
            return format_html('<a href="{}">{}</a>', url, obj.admin.user.name)
        return "System"

    admin_link.short_description = "Admin"

    def entity_link(self, obj):
        # This would need to be customized based on your entity types
        return f"{obj.entity_type} #{str(obj.entity_id)[:8]}"

    entity_link.short_description = "Entity"

    def ip_preview(self, obj):
        return obj.ip_address or "—"

    ip_preview.short_description = "IP"

    def formatted_changes(self, obj):
        changes = []
        if obj.old_values and obj.new_values:
            for key in set(obj.old_values.keys()) | set(obj.new_values.keys()):
                old_val = obj.old_values.get(key, '')
                new_val = obj.new_values.get(key, '')
                if old_val != new_val:
                    changes.append(f"{key}: {old_val} → {new_val}")
        if changes:
            return format_html('<br>'.join(changes))
        return "No changes detected"

    formatted_changes.short_description = "Changes"

    def formatted_old_values(self, obj):
        if obj.old_values:
            try:
                formatted = json.dumps(obj.old_values, indent=2, cls=DjangoJSONEncoder)
                return format_html('<pre style="background: #ffebee; padding: 10px; border-radius: 5px;">{}</pre>',
                                   formatted)
            except:
                return str(obj.old_values)
        return "No old values"

    formatted_old_values.short_description = "Old Values (JSON)"

    def formatted_new_values(self, obj):
        if obj.new_values:
            try:
                formatted = json.dumps(obj.new_values, indent=2, cls=DjangoJSONEncoder)
                return format_html('<pre style="background: #e8f5e8; padding: 10px; border-radius: 5px;">{}</pre>',
                                   formatted)
            except:
                return str(obj.new_values)
        return "No new values"

    formatted_new_values.short_description = "New Values (JSON)"


# ========== ApiUsage Admin ==========
@admin.register(ApiUsage)
class ApiUsageAdmin(admin.ModelAdmin):
    list_display = ('endpoint', 'method', 'request_count', 'user_link', 'date')
    list_filter = ('method', 'date', 'endpoint')
    search_fields = ('endpoint', 'user__name', 'merchant__display_name')
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'user_link', 'merchant_link')

    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:authentication_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.name)
        return "—"

    user_link.short_description = "User"

    def merchant_link(self, obj):
        if obj.merchant:
            url = reverse('admin:merchants_merchant_change', args=[obj.merchant.id])
            return format_html('<a href="{}">{}</a>', url, obj.merchant.display_name)
        return "—"

    merchant_link.short_description = "Merchant"


# ========== ActivityLog Admin ==========
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'activity_type_badge', 'listing_preview', 'created_at', 'ip_preview')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('user__name', 'listing__title')
    list_per_page = 25
    readonly_fields = ('id', 'created_at', 'user_link', 'listing_link', 'formatted_metadata')
    fieldsets = (
        ('Activity Details', {
            'fields': ('user_link', 'activity_type', 'listing_link')
        }),
        ('Additional Data', {
            'fields': ('formatted_metadata',),
            'classes': ('collapse',)
        }),
        ('Technical Info', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:authentication_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.name)
        return "Anonymous"

    user_link.short_description = "User"

    def activity_type_badge(self, obj):
        colors = {
            'VIEW_LISTING': '#2196F3',
            'SEARCH': '#4CAF50',
            'ADD_TO_CART': '#FF9800',
            'CREATE_ORDER': '#9C27B0',
            'CONTACT_SELLER': '#795548',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            colors.get(obj.activity_type, '#999'), obj.get_activity_type_display()
        )

    activity_type_badge.short_description = "Activity Type"

    def listing_preview(self, obj):
        if obj.listing:
            return obj.listing.title[:30] + "..." if len(obj.listing.title) > 30 else obj.listing.title
        return "—"

    listing_preview.short_description = "Listing"

    def listing_link(self, obj):
        if obj.listing:
            url = reverse('admin:listings_listing_change', args=[obj.listing.id])
            return format_html('<a href="{}">{}</a>', url, obj.listing.title)
        return "—"

    listing_link.short_description = "Listing"

    def ip_preview(self, obj):
        return obj.ip_address or "—"

    ip_preview.short_description = "IP"

    def formatted_metadata(self, obj):
        if obj.metadata:
            try:
                formatted = json.dumps(obj.metadata, indent=2, cls=DjangoJSONEncoder)
                return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>',
                                   formatted)
            except:
                return str(obj.metadata)
        return "No metadata"

    formatted_metadata.short_description = "Metadata (JSON)"


@admin.register(UserIntent)
class UserIntentAdmin(admin.ModelAdmin):
    """Admin interface for UserIntent model"""

    list_display = [
        'user_email',
        'user_name',
        'intent_badge',
        'created_at',
        'updated_at'
    ]
    list_filter = ['intent', 'created_at', 'updated_at']
    search_fields = [
        'user__email',
        'user__name',
        'user__username'
    ]
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'user_details'
    ]
    ordering = ['-updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_details')
        }),
        ('Intent Details', {
            'fields': ('intent',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_email(self, obj):
        """Display user email"""
        return obj.user.email

    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    def user_name(self, obj):
        """Display user name"""
        return obj.user.name

    user_name.short_description = 'Name'
    user_name.admin_order_field = 'user__name'

    def intent_badge(self, obj):
        """Display intent as a colored badge"""
        colors = {
            'buy': '#3B82F6',  # Blue
            'sell': '#10B981',  # Green
            'both': '#8B5CF6',  # Purple
        }
        color = colors.get(obj.intent, '#6B7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.get_intent_display().upper()
        )

    intent_badge.short_description = 'Intent'
    intent_badge.admin_order_field = 'intent'

    def user_details(self, obj):
        """Display detailed user information"""
        return format_html(
            '<strong>Email:</strong> {}<br>'
            '<strong>Name:</strong> {}<br>'
            '<strong>Username:</strong> {}<br>'
            '<strong>Phone:</strong> {}<br>'
            '<strong>Verified:</strong> {}',
            obj.user.email,
            obj.user.name,
            obj.user.username,
            obj.user.phone or 'N/A',
            '✅ Yes' if obj.user.is_verified else '❌ No'
        )

    user_details.short_description = 'User Details'

    def has_add_permission(self, request):
        """Prevent manual addition through admin (should be done through API)"""
        return True

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(OnboardingStatus)
class OnboardingStatusAdmin(admin.ModelAdmin):
    """Admin interface for OnboardingStatus model"""

    list_display = [
        'user_email',
        'user_name',
        'progress_bar',
        'intent_status',
        'categories_status',
        'profile_status',
        'completion_status',
        'updated_at'
    ]
    list_filter = [
        'intent_completed',
        'categories_completed',
        'profile_completed',
        'is_onboarding_complete',
        'created_at',
        'updated_at'
    ]
    search_fields = [
        'user__email',
        'user__name',
        'user__username'
    ]
    readonly_fields = [
        'id',
        'is_onboarding_complete',
        'completed_at',
        'created_at',
        'updated_at',
        'user_details',
        'progress_details'
    ]
    ordering = ['-updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_details')
        }),
        ('Onboarding Steps', {
            'fields': (
                'intent_completed',
                'categories_completed',
                'profile_completed',
            )
        }),
        ('Progress', {
            'fields': ('progress_details',)
        }),
        ('Completion Status', {
            'fields': (
                'is_onboarding_complete',
                'completed_at'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_email(self, obj):
        """Display user email"""
        return obj.user.email

    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    def user_name(self, obj):
        """Display user name"""
        return obj.user.name

    user_name.short_description = 'Name'
    user_name.admin_order_field = 'user__name'

    def intent_status(self, obj):
        """Display intent completion status"""
        return self._status_icon(obj.intent_completed)

    intent_status.short_description = 'Intent'

    def categories_status(self, obj):
        """Display categories completion status"""
        return self._status_icon(obj.categories_completed)

    categories_status.short_description = 'Categories'

    def profile_status(self, obj):
        """Display profile completion status"""
        return self._status_icon(obj.profile_completed)

    profile_status.short_description = 'Profile'

    def completion_status(self, obj):
        """Display overall completion status"""
        if obj.is_onboarding_complete:
            return format_html(
                '<span style="color: #10B981; font-weight: bold;">✅ Complete</span>'
            )
        return format_html(
            '<span style="color: #EF4444; font-weight: bold;">⏳ In Progress</span>'
        )

    completion_status.short_description = 'Status'
    completion_status.admin_order_field = 'is_onboarding_complete'

    def progress_bar(self, obj):
        """Display visual progress bar"""
        completed = sum([
            obj.intent_completed,
            obj.categories_completed,
            obj.profile_completed,
        ])
        total = 3
        percentage = (completed / total) * 100

        color = '#10B981' if percentage == 100 else '#3B82F6'

        return format_html(
            '<div style="width: 100px; background-color: #E5E7EB; '
            'border-radius: 10px; overflow: hidden;">'
            '<div style="width: {}%; background-color: {}; height: 20px; '
            'text-align: center; color: white; font-size: 11px; font-weight: bold; '
            'line-height: 20px;">{:.0f}%</div>'
            '</div>',
            percentage,
            color,
            percentage
        )

    progress_bar.short_description = 'Progress'

    def progress_details(self, obj):
        """Display detailed progress information"""
        completed = sum([
            obj.intent_completed,
            obj.categories_completed,
            obj.profile_completed,
        ])
        total = 3
        percentage = (completed / total) * 100

        return format_html(
            '<div style="background: #F3F4F6; padding: 15px; border-radius: 8px;">'
            '<h3 style="margin-top: 0;">Onboarding Progress</h3>'
            '<p><strong>Completed Steps:</strong> {} / {}</p>'
            '<p><strong>Progress:</strong> {:.1f}%</p>'
            '<hr>'
            '<p>{} Intent Selection</p>'
            '<p>{} Category Selection</p>'
            '<p>{} Profile Completion</p>'
            '</div>',
            completed,
            total,
            percentage,
            '✅' if obj.intent_completed else '⏳',
            '✅' if obj.categories_completed else '⏳',
            '✅' if obj.profile_completed else '⏳',
        )

    progress_details.short_description = 'Progress Details'

    def user_details(self, obj):
        """Display detailed user information"""
        return format_html(
            '<strong>Email:</strong> {}<br>'
            '<strong>Name:</strong> {}<br>'
            '<strong>Username:</strong> {}<br>'
            '<strong>Verified:</strong> {}',
            obj.user.email,
            obj.user.name,
            obj.user.username,
            '✅ Yes' if obj.user.is_verified else '❌ No'
        )

    user_details.short_description = 'User Details'

    @staticmethod
    def _status_icon(completed):
        """Helper method to display status icon"""
        if completed:
            return format_html(
                '<span style="color: #10B981; font-size: 16px;">✅</span>'
            )
        return format_html(
            '<span style="color: #6B7280; font-size: 16px;">⏳</span>'
        )

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')

    actions = ['mark_intent_complete', 'mark_categories_complete', 'mark_profile_complete']

    def mark_intent_complete(self, request, queryset):
        """Bulk action to mark intent as complete"""
        for obj in queryset:
            obj.intent_completed = True
            obj.check_completion()
        self.message_user(request, f"{queryset.count()} intent(s) marked as complete")

    mark_intent_complete.short_description = "Mark intent as complete"

    def mark_categories_complete(self, request, queryset):
        """Bulk action to mark categories as complete"""
        for obj in queryset:
            obj.categories_completed = True
            obj.check_completion()
        self.message_user(request, f"{queryset.count()} categories marked as complete")

    mark_categories_complete.short_description = "Mark categories as complete"

    def mark_profile_complete(self, request, queryset):
        """Bulk action to mark profile as complete"""
        for obj in queryset:
            obj.profile_completed = True
            obj.check_completion()
        self.message_user(request, f"{queryset.count()} profiles marked as complete")

    mark_profile_complete.short_description = "Mark profile as complete"


@admin.register(PushToken)
class PushTokenAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'token_short', 'platform', 'is_active',
        'last_used', 'created_at', 'notification_count'
    ]
    list_filter = ['platform', 'is_active', 'created_at', 'last_used']
    search_fields = ['user__username', 'token', 'device_id']
    readonly_fields = ['created_at', 'updated_at', 'last_used']
    actions = ['mark_inactive', 'mark_active', 'test_token']

    fieldsets = (
        ('Token Information', {
            'fields': ('user', 'token', 'device_id', 'platform', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_used')
        }),
    )

    def token_short(self, obj):
        return obj.token[:20] + "..." if len(obj.token) > 20 else obj.token

    token_short.short_description = 'Token'

    def notification_count(self, obj):
        """Count notifications sent to this user"""
        return obj.user.notifications.count()

    notification_count.short_description = 'Notifs Sent'

    def mark_inactive(self, request, queryset):
        """Mark selected tokens as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Marked {updated} token(s) as inactive")

    mark_inactive.short_description = "Mark as inactive"

    def mark_active(self, request, queryset):
        """Mark selected tokens as active"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Marked {updated} token(s) as active")

    mark_active.short_description = "Mark as active"

    def test_token(self, request, queryset):
        """Send a test notification to selected tokens"""
        import requests
        from django.contrib import messages

        api_url = 'http://notification-service:4000/api/push-notification'
        success_count = 0
        error_count = 0

        for token_obj in queryset:
            if not token_obj.is_active:
                messages.warning(request, f"Skipped inactive token for {token_obj.user.username}")
                continue

            try:
                message = {
                    'token': token_obj.token,
                    'title': '🔔 Test Notification',
                    'body': f'This is a test notification for {token_obj.user.username}',
                    'metadata': {
                        'userId': str(token_obj.user.id),
                        'notificationType': 'test',
                        'source': 'admin_panel'
                    }
                }

                response = requests.post(
                    api_url,
                    json={'messages': [message]},
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )

                if response.status_code == 200:
                    success_count += 1
                else:
                    error_count += 1
                    messages.error(
                        request,
                        f"Failed to send to {token_obj.user.username}: {response.status_code}"
                    )
            except Exception as e:
                error_count += 1
                messages.error(request, f"Error sending to {token_obj.user.username}: {str(e)}")

        if success_count > 0:
            messages.success(request, f"Successfully sent {success_count} test notification(s)")
        if error_count > 0:
            messages.error(request, f"Failed to send {error_count} test notification(s)")

    test_token.short_description = "Send test notification"