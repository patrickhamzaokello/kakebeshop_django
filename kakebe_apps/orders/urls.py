# kakebe_apps/orders/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderIntentViewSet, OrderGroupViewSet

router = DefaultRouter()
router.register(r'orders', OrderIntentViewSet, basename='order')
router.register(r'order-groups', OrderGroupViewSet, basename='order-group')

app_name = 'orders'

urlpatterns = [
    path('', include(router.urls)),
]

# Available endpoints:
"""
Order Management:
GET    /api/v1/orders/orders/                    - List all orders
GET    /api/v1/orders/orders/{id}/               - Get single order
GET    /api/v1/orders/orders/my_orders/          - Get filtered orders
POST   /api/v1/orders/orders/{id}/update_status/ - Update order status (merchant)
POST   /api/v1/orders/orders/{id}/cancel/        - Cancel order (buyer)

Order Groups:
GET    /api/v1/orders/order-groups/              - List all order groups
GET    /api/v1/orders/order-groups/{id}/         - Get single order group
GET    /api/v1/orders/order-groups/{id}/orders/  - Get orders in group
POST   /api/v1/orders/order-groups/{id}/update_all_statuses/ - Update all orders in group
"""