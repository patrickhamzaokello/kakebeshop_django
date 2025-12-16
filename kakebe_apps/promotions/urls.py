# kakebe_apps/promotions/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PromotionalBannerViewSet, BannerListingViewSet

router = DefaultRouter()
router.register(r'banners', PromotionalBannerViewSet, basename='promotional-banner')
router.register(r'banner-listings', BannerListingViewSet, basename='banner-listing')

urlpatterns = [
    path('', include(router.urls)),
]