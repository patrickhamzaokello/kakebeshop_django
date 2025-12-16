# kakebe_apps/listings/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ListingViewSet

router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')

urlpatterns = [
    path('', include(router.urls)),
]

# This creates the following routes:
#
# PUBLIC ENDPOINTS (Verified listings only):
# GET    /listings/                         - List verified listings (paginated)
#                                             Query params: search, listing_type, category,
#                                             location, merchant, min_price, max_price,
#                                             sort_by, page, page_size
# GET    /listings/featured/                - Get featured listings (shuffled)
#                                             Query params: limit (default: 10, max: 50)
# GET    /listings/{id}/                    - Retrieve listing detail (must be verified)
# POST   /listings/{id}/increment_views/    - Increment view count
# POST   /listings/{id}/increment_contacts/ - Increment contact count
#
# AUTHENTICATED MERCHANT ENDPOINTS:
# GET    /listings/my_listings/             - Get own listings (all statuses)
#                                             Query params: status, page, page_size
# POST   /listings/                         - Create listing (starts as PENDING)
# PATCH  /listings/{id}/                    - Update own listing
# DELETE /listings/{id}/                    - Soft delete own listing
# POST   /listings/{id}/add_image/          - Add image to listing
# DELETE /listings/{id}/remove_image/{image_id}/ - Remove image
# POST   /listings/{id}/add_business_hour/  - Add business hours
#
# Example API calls:
# GET /listings/?page=1&page_size=20&category=5&location=2&min_price=100&sort_by=-created_at
# GET /listings/featured/?limit=5
# GET /listings/my_listings/?status=PENDING
# POST /listings/ with JSON body
# PATCH /listings/{id}/ with JSON body
# POST /listings/{id}/add_image/ with {"image": "url", "is_primary": tr