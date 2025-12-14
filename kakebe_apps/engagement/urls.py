# kakebe_apps/interactions/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from .views import (
    FavoriteViewSet, SavedSearchViewSet, ConversationViewSet,
    MessageViewSet, NotificationViewSet, ListingReviewViewSet,
    MerchantReviewViewSet, ReportViewSet, MerchantScoreViewSet,
    ActivityLogViewSet, AuditLogViewSet, ApiUsageViewSet, UserIntentViewSet, OnboardingStatusViewSet
)

router = DefaultRouter()
router.register(r'favorites', FavoriteViewSet, basename='favorite')
router.register(r'saved-searches', SavedSearchViewSet, basename='saved-search')
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'listing-reviews', ListingReviewViewSet, basename='listing-review')
router.register(r'merchant-reviews', MerchantReviewViewSet, basename='merchant-review')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'merchant-scores', MerchantScoreViewSet,basename='merchant-score')
router.register(r'activity-logs', ActivityLogViewSet,basename='activity-log')
router.register(r'audit-logs', AuditLogViewSet,basename='audit-log')
router.register(r'api-usage', ApiUsageViewSet,basename='api-usage')

router.register(r'user-intent', UserIntentViewSet, basename='user-intent')
router.register(r'onboarding-status', OnboardingStatusViewSet, basename='onboarding-status')


# Nested messages under conversations
conversations_router = NestedDefaultRouter(router, r'conversations', lookup='conversation')
conversations_router.register(r'messages', MessageViewSet, basename='conversation-messages')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(conversations_router.urls)),
]