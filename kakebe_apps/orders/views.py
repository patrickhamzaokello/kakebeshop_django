# kakebe_apps/orders/views.py (add these to your existing views)
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import OrderIntent, OrderGroup
from .serializers import OrderIntentSerializer, OrderGroupSerializer
from kakebe_apps.notifications.services import NotificationService
from kakebe_apps.notifications.models import NotificationType


class OrderStatusUpdateMixin:
    """Mixin for handling order status updates with notifications"""

    def send_status_notification(self, order, old_status, new_status):
        """Send notification when order status changes"""

        # Map status to notification type
        notification_map = {
            'CONTACTED': NotificationType.ORDER_CONTACTED,
            'CONFIRMED': NotificationType.ORDER_CONFIRMED,
            'COMPLETED': NotificationType.ORDER_COMPLETED,
            'CANCELLED': NotificationType.ORDER_CANCELLED,
        }

        notification_type = notification_map.get(new_status)

        if notification_type:
            # Notify the buyer
            NotificationService.create_order_notification(
                user=order.buyer,
                order=order,
                notification_type=notification_type,
            )


class OrderIntentViewSet(OrderStatusUpdateMixin, viewsets.ModelViewSet):
    """
    ViewSet for OrderIntent

    Endpoints:
    - list: Get all orders for current user
    - retrieve: Get single order
    - create: Create new order (handled by cart checkout)
    - update_status: Update order status (merchant only)
    - cancel: Cancel order (buyer only)
    """
    serializer_class = OrderIntentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # If user is a merchant, show their orders
        if hasattr(user, 'merchant_profile'):
            return OrderIntent.objects.filter(
                merchant=user.merchant_profile
            ).select_related('buyer', 'merchant', 'group').prefetch_related('items')

        # Otherwise show user's orders as buyer
        return OrderIntent.objects.filter(
            buyer=user
        ).select_related('buyer', 'merchant', 'group').prefetch_related('items')

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Update order status (merchant only)

        POST /api/v1/orders/orders/{id}/update_status/
        {
          "status": "CONTACTED",
          "notes": "Called customer to confirm delivery address"
        }

        Valid statuses: NEW, CONTACTED, CONFIRMED, COMPLETED, CANCELLED
        """
        order = self.get_object()

        # Check if user is the merchant for this order
        if not hasattr(request.user, 'merchant_profile') or order.merchant != request.user.merchant_profile:
            return Response(
                {
                    'success': False,
                    'error': 'Only the merchant can update order status'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        # Validate status
        valid_statuses = ['NEW', 'CONTACTED', 'CONFIRMED', 'COMPLETED', 'CANCELLED']
        if new_status not in valid_statuses:
            return Response(
                {
                    'success': False,
                    'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Store old status for notification
        old_status = order.status

        # Update order
        order.status = new_status
        if notes:
            order.notes = notes
        order.save()

        # Send notification if status changed
        if old_status != new_status:
            self.send_status_notification(order, old_status, new_status)

        # Serialize and return
        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'message': f'Order status updated to {new_status}',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel order (buyer only, before CONFIRMED)

        POST /api/v1/orders/orders/{id}/cancel/
        {
          "reason": "Changed my mind"
        }
        """
        order = self.get_object()

        # Check if user is the buyer
        if order.buyer != request.user:
            return Response(
                {
                    'success': False,
                    'error': 'Only the buyer can cancel their order'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if order can be cancelled
        if order.status in ['COMPLETED', 'CANCELLED']:
            return Response(
                {
                    'success': False,
                    'error': f'Cannot cancel order with status {order.status}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        old_status = order.status
        order.status = 'CANCELLED'

        # Add cancellation reason to notes
        reason = request.data.get('reason', 'No reason provided')
        order.notes = f"Cancelled by buyer. Reason: {reason}"
        order.save()

        # Send notification
        self.send_status_notification(order, old_status, 'CANCELLED')

        # Serialize and return
        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'message': 'Order cancelled successfully',
            'data': serializer.data
        })

    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        """
        Get orders with filtering options

        GET /api/v1/orders/orders/my_orders/?status=CONFIRMED&role=buyer

        Query params:
        - status: Filter by status (NEW, CONTACTED, CONFIRMED, COMPLETED, CANCELLED)
        - role: 'buyer' or 'merchant'
        """
        queryset = self.get_queryset()

        # Filter by status
        order_status = request.query_params.get('status')
        if order_status:
            queryset = queryset.filter(status=order_status.upper())

        # Filter by role
        role = request.query_params.get('role')
        if role == 'merchant' and hasattr(request.user, 'merchant_profile'):
            queryset = OrderIntent.objects.filter(merchant=request.user.merchant_profile)
        elif role == 'buyer':
            queryset = OrderIntent.objects.filter(buyer=request.user)

        # Serialize
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class OrderGroupViewSet(OrderStatusUpdateMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for OrderGroup

    Endpoints:
    - list: Get all order groups for current user
    - retrieve: Get single order group with all orders
    - update_status: Update status of all orders in group
    """
    serializer_class = OrderGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderGroup.objects.filter(
            buyer=self.request.user
        ).prefetch_related('orders__items', 'orders__merchant')

    @action(detail=True, methods=['post'])
    def update_all_statuses(self, request, pk=None):
        """
        Update status of all orders in the group

        POST /api/v1/orders/order-groups/{id}/update_all_statuses/
        {
          "status": "CANCELLED",
          "notes": "Customer requested cancellation of entire order"
        }

        This updates all orders in the group to the same status
        """
        order_group = self.get_object()

        # Only buyer can update group status
        if order_group.buyer != request.user:
            return Response(
                {
                    'success': False,
                    'error': 'Only the buyer can update order group status'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        # Validate status
        valid_statuses = ['CANCELLED']  # Only cancellation for groups
        if new_status not in valid_statuses:
            return Response(
                {
                    'success': False,
                    'error': 'Only CANCELLED status is allowed for order groups'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update all orders in the group
        updated_count = 0
        for order in order_group.orders.all():
            if order.status not in ['COMPLETED', 'CANCELLED']:
                old_status = order.status
                order.status = new_status
                if notes:
                    order.notes = notes
                order.save()

                # Send notification for each order
                self.send_status_notification(order, old_status, new_status)
                updated_count += 1

        # Serialize and return
        serializer = self.get_serializer(order_group)
        return Response({
            'success': True,
            'message': f'Updated {updated_count} orders to {new_status}',
            'data': serializer.data
        })

    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        """
        Get all orders in this group

        GET /api/v1/orders/order-groups/{id}/orders/
        """
        order_group = self.get_object()
        orders = order_group.orders.all()

        serializer = OrderIntentSerializer(orders, many=True)
        return Response({
            'success': True,
            'count': orders.count(),
            'data': serializer.data
        })