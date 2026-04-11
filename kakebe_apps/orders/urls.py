# kakebe_apps/orders/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderIntentViewSet, OrderGroupViewSet

router = DefaultRouter()
router.register(r'', OrderIntentViewSet, basename='order')
router.register(r'order-groups', OrderGroupViewSet, basename='order-group')

app_name = 'orders'

urlpatterns = [
    path('', include(router.urls)),
]

# Available endpoints:
"""
Order Management:
GET    /api/v1/orders/                    - List all orders
GET    /api/v1/orders/{id}/               - Get single order
GET    /api/v1/orders/my-orders/          - Get filtered orders
GET    /api/v1/orders/buyer-search/       - Buyer searches their placed orders
GET    /api/v1/orders/merchant-search/    - Merchant searches received orders
POST   /api/v1/orders/checkout/           - Place orders from cart
POST   /api/v1/orders/{id}/confirm/       - Confirm order (merchant)
POST   /api/v1/orders/{id}/complete/      - Complete order (merchant)
POST   /api/v1/orders/{id}/update-status/ - Update order status (merchant)
POST   /api/v1/orders/{id}/cancel/         - Cancel order (buyer)
POST   /api/v1/orders/{id}/merchant-cancel/ - Cancel order (merchant)

Order Groups:
GET    /api/v1/orders/order-groups/              - List all order groups
GET    /api/v1/orders/order-groups/{id}/         - Get single order group
GET    /api/v1/orders/order-groups/{id}/orders/  - Get orders in group
POST   /api/v1/orders/order-groups/{id}/update-all-statuses/ - Update all orders in group
"""