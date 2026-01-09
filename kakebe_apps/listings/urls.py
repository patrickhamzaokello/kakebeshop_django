# kakebe_apps/listings/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ListingViewSet

# Create router and register viewset
router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
]

# The router automatically generates the following URLs:
#
# Public endpoints:
# GET    /listings/                              - List all active, verified listings
# GET    /listings/{id}/                         - Retrieve single listing detail
# GET    /listings/featured/                     - Get featured listings
# POST   /listings/{id}/increment_views/         - Increment view count
# POST   /listings/{id}/increment_contacts/      - Increment contact count
#
# Authenticated merchant endpoints:
# POST   /listings/                              - Create new listing
# PATCH  /listings/{id}/                         - Update own listing
# DELETE /listings/{id}/                         - Soft delete own listing
# GET    /listings/my_listings/                  - Get merchant's own listings
# POST   /listings/{id}/add_images/              - Attach images to listing
# POST   /listings/{id}/reorder_images/          - Reorder listing images
# GET    /listings/{id}/get_uploadable_images/   - Get draft images available to attach
# DELETE /listings/{id}/remove_image_group/{image_group_id}/ - Remove image group
# POST   /listings/{id}/add_business_hour/       - Add business hours
# GET    /listings/{id}/stats/                   - Get listing statistics
# POST   /listings/bulk_update_status/           - Bulk update listing statuses
# POST   /listings/bulk_delete/                  - Bulk soft delete listings
# GET    /listings/analytics/                    - Get merchant analytics
# GET    /listings/export_csv/                   - Export listings to CSV