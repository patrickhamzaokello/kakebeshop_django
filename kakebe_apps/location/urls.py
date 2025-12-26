# kakebe_apps/location/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LocationViewSet, UserAddressViewSet, reverse_geocode

router = DefaultRouter()
router.register(r'addresses', UserAddressViewSet, basename='address')
router.register(r'locations', LocationViewSet, basename='location')

urlpatterns = [
    path('', include(router.urls)),
    path('reverse-geocode/', reverse_geocode, name='reverse-geocode'),
]