# kakebe_apps/orders/views.py - COMPLETE VERSION WITH CHECKOUT
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import OrderIntent, OrderIntentItem, OrderGroup
from .serializers import (
    OrderIntentSerializer,
    OrderGroupSerializer,
    CheckoutRequestSerializer
)
from kakebe_apps.cart.models import Cart
from kakebe_apps.location.models import UserAddress


class OrderIntentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for OrderIntent with automatic notification via signals

    All status changes trigger notifications automatically via
    signals in kakebe_apps/notifications/signals.py
    """
    serializer_class = OrderIntentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # If user is a merchant, show their orders
        if hasattr(user, 'merchant_profile'):
            return OrderIntent.objects.filter(
                merchant=user.merchant_profile
            ).select_related('buyer', 'merchant', 'address', 'group').prefetch_related('items__listing')

        # Otherwise show user's orders as buyer
        return OrderIntent.objects.filter(
            buyer=user
        ).select_related('buyer', 'merchant', 'address', 'group').prefetch_related('items__listing').order_by(
            '-created_at')

    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout(self, request):
        """
        ✅ CHECKOUT ENDPOINT - RESTORED

        POST /api/v1/orders/orders/checkout/
        {
          "address_id": "uuid",
          "notes": "optional",
          "delivery_fee": 5000
        }
        """
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        try:
            cart = Cart.objects.prefetch_related(
                'items__listing__merchant'
            ).get(user=user)

            if not cart.items.exists():
                return Response({
                    'success': False,
                    'error': 'Cart is empty'
                }, status=status.HTTP_400_BAD_REQUEST)

            validation_errors = cart.validate_items()
            if validation_errors:
                return Response({
                    'success': False,
                    'error': 'Some items are no longer available',
                    'details': validation_errors
                }, status=status.HTTP_400_BAD_REQUEST)

            address = get_object_or_404(
                UserAddress,
                id=serializer.validated_data['address_id'],
                user=user
            )

            grouped_items = cart.group_items_by_merchant()
            orders = []
            order_group = None
            total_group_amount = 0

            with transaction.atomic():
                if len(grouped_items) > 1:
                    order_group = OrderGroup.objects.create(
                        group_number=OrderGroup.generate_group_number(),
                        buyer=user,
                        total_amount=0,
                        total_orders=len(grouped_items)
                    )

                for merchant, items in grouped_items.items():
                    items_total = sum(
                        item.listing.price * item.quantity
                        for item in items
                    )

                    delivery_fee = serializer.validated_data.get('delivery_fee', 0)
                    total_amount = items_total + (delivery_fee or 0)
                    total_group_amount += total_amount

                    # Create order - signals automatically send notifications
                    order = OrderIntent.objects.create(
                        order_number=OrderIntent.generate_order_number(),
                        buyer=user,
                        merchant=merchant,
                        address=address,
                        notes=serializer.validated_data.get('notes', ''),
                        total_amount=total_amount,
                        delivery_fee=delivery_fee,
                        expected_delivery_date=serializer.validated_data.get('expected_delivery_date'),
                        status='NEW',
                        order_group=order_group
                    )

                    order_items = []
                    for cart_item in items:
                        order_items.append(
                            OrderIntentItem(
                                order_intent=order,
                                listing=cart_item.listing,
                                quantity=cart_item.quantity,
                                unit_price=cart_item.listing.price,
                                total_price=cart_item.listing.price * cart_item.quantity
                            )
                        )

                    OrderIntentItem.objects.bulk_create(order_items)
                    orders.append(order)

                if order_group:
                    order_group.total_amount = total_group_amount
                    order_group.save(update_fields=['total_amount'])

                cart.clear_cart()

            serialized_orders = OrderIntentSerializer(orders, many=True)

            return Response({
                'success': True,
                'message': 'Order(s) placed successfully',
                'data': {
                    'orders': serialized_orders.data,
                    'order_group': {
                        'id': str(order_group.id) if order_group else None,
                        'group_number': order_group.group_number if order_group else None,
                        'total_orders': len(orders),
                        'total_amount': str(total_group_amount)
                    } if order_group else None
                }
            }, status=status.HTTP_201_CREATED)

        except Cart.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Cart not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Update order status (merchant only)
        Notification sent automatically via signal
        """
        order = self.get_object()

        if not hasattr(request.user, 'merchant_profile') or order.merchant != request.user.merchant_profile:
            return Response({
                'success': False,
                'error': 'Only the merchant can update order status'
            }, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        valid_statuses = ['NEW', 'CONTACTED', 'CONFIRMED', 'COMPLETED', 'CANCELLED']
        if new_status not in valid_statuses:
            return Response({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = new_status
        if notes:
            order.notes = notes
        order.save()  # Signal handles notification

        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'message': f'Order status updated to {new_status}',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        Cancel order (buyer only)
        Notification sent automatically via signal
        """
        order = self.get_object()

        if order.buyer != request.user:
            return Response({
                'success': False,
                'error': 'Only the buyer can cancel their order'
            }, status=status.HTTP_403_FORBIDDEN)

        if order.status in ['COMPLETED', 'CANCELLED']:
            return Response({
                'success': False,
                'error': f'Cannot cancel order with status {order.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'CANCELLED'
        reason = request.data.get('reason', 'No reason provided')
        order.cancelled_by = 'BUYER'
        order.cancellation_reason = reason
        order.notes = f"Cancelled by buyer. Reason: {reason}"
        order.save()  # Signal handles notification

        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'message': 'Order cancelled successfully',
            'data': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='my-orders')
    def my_orders(self, request):
        """Get filtered orders"""
        queryset = self.get_queryset()

        order_status = request.query_params.get('status')
        if order_status:
            queryset = queryset.filter(status=order_status.upper())

        role = request.query_params.get('role')
        if role == 'merchant' and hasattr(request.user, 'merchant_profile'):
            queryset = OrderIntent.objects.filter(merchant=request.user.merchant_profile)
        elif role == 'buyer':
            queryset = OrderIntent.objects.filter(buyer=request.user)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class OrderGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for OrderGroup"""
    serializer_class = OrderGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderGroup.objects.filter(
            buyer=self.request.user
        ).prefetch_related('orders__items', 'orders__merchant').order_by('-created_at')

    @action(detail=True, methods=['post'], url_path='update-all-statuses')
    def update_all_statuses(self, request, pk=None):
        """
        Cancel all orders in group
        Notifications sent automatically via signals
        """
        order_group = self.get_object()

        if order_group.buyer != request.user:
            return Response({
                'success': False,
                'error': 'Only the buyer can update order group status'
            }, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        if new_status not in ['CANCELLED']:
            return Response({
                'success': False,
                'error': 'Only CANCELLED status is allowed for order groups'
            }, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0
        for order in order_group.orders.all():
            if order.status not in ['COMPLETED', 'CANCELLED']:
                order.status = new_status
                if notes:
                    order.notes = notes
                order.save()  # Signal handles notification
                updated_count += 1

        serializer = self.get_serializer(order_group)
        return Response({
            'success': True,
            'message': f'Updated {updated_count} orders to {new_status}',
            'data': serializer.data
        })

    @action(detail=True, methods=['get'], url_path='orders')
    def orders(self, request, pk=None):
        """Get all orders in group"""
        order_group = self.get_object()
        orders = order_group.orders.all()

        serializer = OrderIntentSerializer(orders, many=True)
        return Response({
            'success': True,
            'count': orders.count(),
            'data': serializer.data
        })