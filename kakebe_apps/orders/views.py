from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import OrderIntent, OrderIntentItem, OrderGroup
from .serializers import (
    OrderIntentSerializer,
    CheckoutRequestSerializer, OrderGroupSerializer
)
from kakebe_apps.cart.models import Cart
from kakebe_apps.location.models import UserAddress


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderIntentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderIntent.objects.filter(
            buyer=self.request.user
        ).select_related(
            'buyer', 'merchant', 'address'
        ).prefetch_related(
            'items__listing'
        ).order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout(self, request):
        """
        Create order from cart items
        """
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        try:
            # Get user's cart
            cart = Cart.objects.prefetch_related(
                'items__listing__merchant'
            ).get(user=user)

            if not cart.items.exists():
                return Response(
                    {'error': 'Cart is empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate cart items
            validation_errors = cart.validate_items()
            if validation_errors:
                return Response(
                    {'error': 'Some items are no longer available', 'details': validation_errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get and validate address
            address = get_object_or_404(
                UserAddress,
                id=serializer.validated_data['address_id'],
                user=user
            )

            # Group items by merchant
            grouped_items = cart.group_items_by_merchant()

            # Create orders (one per merchant)
            orders = []
            order_group = None
            total_group_amount = 0

            with transaction.atomic():
                # Create OrderGroup if multiple merchants
                if len(grouped_items) > 1:
                    order_group = OrderGroup.objects.create(
                        group_number=OrderGroup.generate_group_number(),
                        buyer=user,
                        total_amount=0,  # Will update after creating orders
                        total_orders=len(grouped_items)
                    )

                for merchant, items in grouped_items.items():
                    # Calculate total for this merchant's items
                    items_total = sum(
                        item.listing.price * item.quantity
                        for item in items
                    )

                    delivery_fee = serializer.validated_data.get('delivery_fee', 0)
                    total_amount = items_total + (delivery_fee or 0)
                    total_group_amount += total_amount

                    # Create order
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
                        order_group=order_group  # Link to group
                    )

                    # Create order items
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

                # Update order group total
                if order_group:
                    order_group.total_amount = total_group_amount
                    order_group.save(update_fields=['total_amount'])

                # Clear cart after successful order creation
                cart.clear_cart()

            # Serialize and return orders
            serialized_orders = OrderIntentSerializer(orders, many=True)

            return Response(
                {
                    'message': 'Order(s) placed successfully',
                    'orders': serialized_orders.data,
                    'order_group': {
                        'id': str(order_group.id) if order_group else None,
                        'group_number': order_group.group_number if order_group else None,
                        'total_orders': len(orders),
                        'total_amount': str(total_group_amount)
                    } if order_group else None
                },
                status=status.HTTP_201_CREATED
            )

        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_order(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()

        if order.status not in ['NEW', 'CONTACTED']:
            return Response(
                {'error': 'Order cannot be cancelled at this stage'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = 'CANCELLED'
        order.cancelled_by = 'BUYER'
        order.cancellation_reason = request.data.get('reason', '')
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)


class OrderGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing order groups
    """
    serializer_class = OrderGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderGroup.objects.filter(
            buyer=self.request.user
        ).prefetch_related(
            'orders__merchant',
            'orders__items__listing'
        ).order_by('-created_at')