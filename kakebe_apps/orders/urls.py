# kakebe_apps/orders/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet, OrderGroupViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-groups', OrderGroupViewSet, basename='order-group')


urlpatterns = [
    path('', include(router.urls)),
]