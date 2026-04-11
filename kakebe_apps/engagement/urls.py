# kakebe_apps/interactions/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from .views import (
    SavedSearchViewSet, ConversationViewSet,
    MessageViewSet, ListingReviewViewSet,
    MerchantReviewViewSet, ReportViewSet, MerchantScoreViewSet,
    ActivityLogViewSet, AuditLogViewSet, ApiUsageViewSet, UserIntentViewSet, OnboardingStatusViewSet, PushTokenViewSet,
    EnhancedSearchView, ListingCommentViewSet,
)

router = DefaultRouter()
router.register(r'saved-searches', SavedSearchViewSet, basename='saved-search')

router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'listing-reviews', ListingReviewViewSet, basename='listing-review')
router.register(r'merchant-reviews', MerchantReviewViewSet, basename='merchant-review')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'merchant-scores', MerchantScoreViewSet,basename='merchant-score')
router.register(r'activity-logs', ActivityLogViewSet,basename='activity-log')
router.register(r'audit-logs', AuditLogViewSet,basename='audit-log')
router.register(r'api-usage', ApiUsageViewSet,basename='api-usage')

router.register(r'user-intent', UserIntentViewSet, basename='user-intent')
router.register(r'onboarding-status', OnboardingStatusViewSet, basename='onboarding-status')

router.register(r'push-tokens', PushTokenViewSet, basename='push-token')

# Direct access to a specific comment (retrieve / edit / delete / replies action)
router.register(r'listing-comments', ListingCommentViewSet, basename='listing-comment')


# Nested messages under conversations
conversations_router = NestedDefaultRouter(router, r'conversations', lookup='conversation')
conversations_router.register(r'messages', MessageViewSet, basename='conversation-messages')


# Listing-scoped comment endpoints (nested under /listings/<listing_id>/comments/)
_comment_list_create = ListingCommentViewSet.as_view({'get': 'list', 'post': 'create'})
_comment_total = ListingCommentViewSet.as_view({'get': 'total'})

urlpatterns = [
    path('', include(router.urls)),
    path('', include(conversations_router.urls)),
    path('search/', EnhancedSearchView.as_view(), name='unified-search'),

    # Paginated comments for a listing + post a comment
    path(
        'listings/<uuid:listing_id>/comments/',
        _comment_list_create,
        name='listing-comments-list',
    ),
    # Total comment count for a listing
    path(
        'listings/<uuid:listing_id>/comments/total/',
        _comment_total,
        name='listing-comments-total',
    ),
]