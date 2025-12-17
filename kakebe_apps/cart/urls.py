from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartViewSet, WishlistViewSet

router = DefaultRouter()
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'wishlist', WishlistViewSet, basename='wishlist')

urlpatterns = [
    path('', include(router.urls)),
]

"""
Available endpoints:

CART:
- GET    /cart/                          - Get cart with all items
- GET    /cart/items/                    - Get paginated cart items
- GET    /cart/count/                    - Get cart count
- POST   /cart/add/                      - Add item to cart (body: {listing_id, quantity})
- PATCH  /cart/update/{item_id}/         - Update cart item quantity (body: {quantity})
- DELETE /cart/remove/{item_id}/         - Remove item from cart
- DELETE /cart/clear/                    - Clear entire cart

WISHLIST:
- GET    /wishlist/                      - Get wishlist with all items
- GET    /wishlist/items/                - Get paginated wishlist items
- GET    /wishlist/count/                - Get wishlist count
- POST   /wishlist/add/                  - Add item to wishlist (body: {listing_id})
- DELETE /wishlist/remove/{item_id}/     - Remove item by wishlist item ID
- DELETE /wishlist/remove-by-listing/{listing_id}/ - Remove item by listing ID
- GET    /wishlist/check/{listing_id}/   - Check if item is in wishlist
- DELETE /wishlist/clear/                - Clear entire wishlist
"""