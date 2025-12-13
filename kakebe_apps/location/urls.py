# kakebe_apps/location/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LocationViewSet, UserAddressViewSet

router = DefaultRouter()
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'user-addresses', UserAddressViewSet, basename='useraddress')

urlpatterns = [
    path('', include(router.urls)),
]