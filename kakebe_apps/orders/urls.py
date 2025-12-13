# kakebe_apps/orders/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import OrderIntentViewSet

router = DefaultRouter()
router.register(r'orders', OrderIntentViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
]