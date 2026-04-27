from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AdminBroadcastCampaignViewSet,
    AdminCategoryViewSet,
    AdminImageViewSet,
    AdminListingViewSet,
    AdminMerchantViewSet,
    AdminOrderViewSet,
    AdminStatsView,
    AdminUserViewSet,
)

router = DefaultRouter()
router.register(r'stats', AdminStatsView, basename='admin-stats')
router.register(r'users', AdminUserViewSet, basename='admin-users')
router.register(r'merchants', AdminMerchantViewSet, basename='admin-merchants')
router.register(r'listings', AdminListingViewSet, basename='admin-listings')
router.register(r'categories', AdminCategoryViewSet, basename='admin-categories')
router.register(r'orders', AdminOrderViewSet, basename='admin-orders')
router.register(r'images', AdminImageViewSet, basename='admin-images')
router.register(r'broadcasts', AdminBroadcastCampaignViewSet, basename='admin-broadcasts')

urlpatterns = [
    path('', include(router.urls)),
]
