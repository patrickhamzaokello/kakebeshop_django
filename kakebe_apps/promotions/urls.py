# kakebe_apps/promotions/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PromotionalCampaignViewSet, CampaignCreativeViewSet,
    CampaignListingViewSet, ActiveCreativeViewSet
)

router = DefaultRouter()
router.register(r'campaigns', PromotionalCampaignViewSet, basename='campaign')
router.register(r'creatives', CampaignCreativeViewSet, basename='creative')
router.register(r'campaign-listings', CampaignListingViewSet, basename='campaign-listing')
router.register(r'active-creatives', ActiveCreativeViewSet, basename='active-creative')

urlpatterns = [
    path('', include(router.urls)),
]