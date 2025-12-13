# kakebe_apps/merchants/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MerchantViewSet

router = DefaultRouter(trailing_slash=False)  # Optional: cleaner URLs without trailing slash
router.register(r'merchants', MerchantViewSet, basename='merchant')

urlpatterns = [
    path('', include(router.urls)),
]