# kakebe_apps/merchants/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MerchantViewSet

router = DefaultRouter()
router.register(r'merchants', MerchantViewSet, basename='merchant')

urlpatterns = [
    path('', include(router.urls)),
]

# This creates the following routes:
#
# PUBLIC ENDPOINTS (Verified merchants only):
# GET    /merchants/                   - List verified merchants (paginated)
#                                        Query params: search, min_rating, sort_by, page, page_size
# GET    /merchants/featured/          - Get featured merchants (shuffled, random order)
#                                        Query params: limit (default: 10, max: 50)
# GET    /merchants/{id}/              - Retrieve merchant detail (must be verified)
#
# AUTHENTICATED ENDPOINTS:
# GET    /merchants/me/                - Get own profile (works even if unverified)
# PATCH  /merchants/me/                - Update own profile
# POST   /merchants/create_profile/    - Create merchant profile (starts unverified)
# DELETE /merchants/delete_me/         - Soft delete own profile
#
# Example API calls:
# GET /merchants/?page=1&page_size=20&search=coffee&min_rating=4.0&sort_by=-rating
# GET /merchants/featured/?limit=5
# GET /merchants/me/
# PATCH /merchants/me/ with JSON body
# POST /merchants/create_profile/ with JSON body