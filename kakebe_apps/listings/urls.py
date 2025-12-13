# kakebe_apps/listings/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ListingViewSet, ListingTagViewSet,
    ListingImageViewSet, ListingBusinessHourViewSet
)

router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'listing-tags', ListingTagViewSet, basename='listingtag')
router.register(r'listing-images', ListingImageViewSet, basename='listingimage')
router.register(r'listing-business-hours', ListingBusinessHourViewSet, basename='listingbusinesshour')

urlpatterns = [
    path('', include(router.urls)),
]