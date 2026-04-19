# kakebe_apps/orders/views.py - COMPLETE VERSION WITH CHECKOUT
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.conf import settings

from django.db.models import Q

from .models import OrderIntent, OrderIntentItem, OrderGroup
from kakebe_apps.analytics import events as analytics
from .serializers import (
    OrderIntentSerializer,
    OrderGroupSerializer,
    CheckoutRequestSerializer
)
from kakebe_apps.cart.models import Cart
from kakebe_apps.location.models import UserAddress


def _attach_primary_images(orders):
    """
    Bulk-load thumbnail images for all listings across a set of orders.
    Replaces 1-3 DB queries per listing with a single query for all listings.
    Sets `_cached_primary_image` on each Listing instance so that
    ListingListSerializer uses the cache instead of the N+1 property.
    """
    from kakebe_apps.imagehandler.models import ImageAsset
    from collections import defaultdict

    listings = []
    for order in orders:
        for item in order.items.all():
            listings.append(item.listing)

    if not listings:
        return

    listing_ids = list({l.id for l in listings})

    assets = list(
        ImageAsset.objects.filter(
            image_type='listing',
            object_id__in=listing_ids,
            is_confirmed=True,
        )
        .order_by('object_id', 'order', 'created_at')
        .values('id', 'object_id', 'image_group_id', 'variant', 's3_key', 'width', 'height')
    )

    # First image group per listing (ordering guarantees earliest/lowest wins)
    listing_first_group = {}
    group_variants = defaultdict(dict)
    for asset in assets:
        lid = asset['object_id']
        gid = asset['image_group_id']
        if lid not in listing_first_group:
            listing_first_group[lid] = gid
        group_variants[gid].setdefault(asset['variant'], asset)

    def _best(variants):
        for v in ('thumb', 'medium', 'large'):
            if v in variants:
                return variants[v]
        return next(iter(variants.values()), None)

    cdn = getattr(settings, 'AWS_CLOUDFRONT_DOMAIN', '')
    for listing in listings:
        first_group = listing_first_group.get(listing.id)
        asset = _best(group_variants.get(first_group, {})) if first_group else None
        listing._cached_primary_image = {
            'id': str(asset['id']),
            'image': f"{cdn}/{asset['s3_key']}",
            'width': asset['width'],
            'height': asset['height'],
            'variant': asset['variant'],
            'image_group_id': str(asset['image_group_id']),
        } if asset else None


class OrderIntentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for OrderIntent with automatic notification via signals

    All status changes trigger notifications automatically via
    signals in kakebe_apps/notifications/signals.py
    """
    serializer_class = OrderIntentSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        orders = list(queryset)
        _attach_primary_images(orders)
        serializer = self.get_serializer(orders, many=True)
        return Response({'success': True, 'count': len(orders), 'data': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        _attach_primary_images([instance])
        serializer = self.get_serializer(instance)
        return Response({'success': True, 'data': serializer.data})

    def get_queryset(self):
        user = self.request.user
        qs_base = OrderIntent.objects.select_related(
            'buyer', 'merchant', 'address', 'order_group'
        ).prefetch_related(
            'items__listing__merchant',
            'items__listing__category',
        ).order_by('-created_at')

        if hasattr(user, 'merchant_profile'):
            # Return orders where user is buyer OR merchant
            return qs_base.filter(
                Q(buyer=user) | Q(merchant=user.merchant_profile)
            )

        return qs_base.filter(buyer=user)

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
        analytics.checkout_started(user.id)

        try:
            cart = Cart.objects.prefetch_related(
                'items__listing__merchant'
            ).get(user=user)

            if not cart.items.exists():
                analytics.checkout_failed(user.id, reason='empty_cart')
                return Response({
                    'success': False,
                    'error': 'Cart is empty'
                }, status=status.HTTP_400_BAD_REQUEST)

            validation_errors = cart.validate_items()
            if validation_errors:
                analytics.checkout_failed(user.id, reason='items_unavailable')
                return Response({
                    'success': False,
                    'error': 'Some items are no longer available',
                    'details': validation_errors
                }, status=status.HTTP_400_BAD_REQUEST)

            price_errors = [
                {
                    'item_id': str(item.id),
                    'error': f'"{item.listing.title}" has no fixed price and cannot be checked out. '
                             f'Please remove it from your cart.'
                }
                for item in cart.items.select_related('listing').all()
                if item.listing.price is None
            ]
            if price_errors:
                analytics.checkout_failed(user.id, reason='price_missing')
                return Response({
                    'success': False,
                    'error': 'Some items do not have a fixed price and cannot be checked out.',
                    'details': price_errors
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

            analytics.order_placed(user.id, orders, total_group_amount, order_group)

            order_ids = [o.id for o in orders]
            orders_with_items = list(
                OrderIntent.objects.filter(
                    id__in=order_ids
                ).select_related(
                    'buyer', 'merchant', 'address', 'order_group'
                ).prefetch_related('items__listing__merchant', 'items__listing__category')
            )
            _attach_primary_images(orders_with_items)
            serialized_orders = OrderIntentSerializer(orders_with_items, many=True)

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

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        """
        Merchant confirms an order.
        POST /api/v1/orders/orders/{id}/confirm/
        """
        order = self.get_object()

        if not hasattr(request.user, 'merchant_profile') or order.merchant != request.user.merchant_profile:
            return Response({
                'success': False,
                'error': 'Only the merchant can confirm this order'
            }, status=status.HTTP_403_FORBIDDEN)

        if order.status not in ['NEW', 'CONTACTED']:
            return Response({
                'success': False,
                'error': f'Cannot confirm an order with status {order.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'CONFIRMED'
        order.save()

        analytics.order_status_changed(request.user.id, order, 'NEW', 'CONFIRMED')

        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'message': 'Order confirmed successfully',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """
        Merchant marks an order as completed.
        POST /api/v1/orders/orders/{id}/complete/
        """
        order = self.get_object()

        if not hasattr(request.user, 'merchant_profile') or order.merchant != request.user.merchant_profile:
            return Response({
                'success': False,
                'error': 'Only the merchant can complete this order'
            }, status=status.HTTP_403_FORBIDDEN)

        if order.status not in ['CONFIRMED']:
            return Response({
                'success': False,
                'error': f'Cannot complete an order with status {order.status}. Order must be CONFIRMED first.'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'COMPLETED'
        order.save()

        analytics.order_completed(request.user.id, order)

        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'message': 'Order completed successfully',
            'data': serializer.data
        })

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

        old_status = order.status
        order.status = new_status
        if notes:
            order.notes = notes
        order.save()  # Signal handles notification

        analytics.order_status_changed(request.user.id, order, old_status, new_status)

        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'message': f'Order status updated to {new_status}',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        Cancel order (buyer only).
        POST /api/v1/orders/{id}/cancel/
        Body: { "reason": "optional reason" }
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
                'error': f'Cannot cancel an order with status {order.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get('reason', '').strip() or 'No reason provided'
        order.status = 'CANCELLED'
        order.cancelled_by = 'BUYER'
        order.cancellation_reason = reason
        order.notes = f"Cancelled by buyer. Reason: {reason}"
        order.save()  # signal handles notification

        analytics.order_cancelled(request.user.id, order, cancelled_by='buyer', reason=reason)

        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'message': 'Order cancelled successfully',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='merchant-cancel')
    def merchant_cancel(self, request, pk=None):
        """
        Merchant cancels a received order.
        POST /api/v1/orders/{id}/merchant-cancel/
        Body: { "reason": "required reason" }

        Allowed from: NEW, CONTACTED, CONFIRMED.
        Not allowed once the order is COMPLETED or already CANCELLED.
        """
        order = self.get_object()

        if not hasattr(request.user, 'merchant_profile') or order.merchant != request.user.merchant_profile:
            return Response({
                'success': False,
                'error': 'Only the merchant who received this order can cancel it'
            }, status=status.HTTP_403_FORBIDDEN)

        if order.status in ['COMPLETED', 'CANCELLED']:
            return Response({
                'success': False,
                'error': f'Cannot cancel an order with status {order.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get('reason', '').strip()
        if not reason:
            return Response({
                'success': False,
                'error': 'A cancellation reason is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.status = 'CANCELLED'
        order.cancelled_by = 'MERCHANT'
        order.cancellation_reason = reason
        order.notes = f"Cancelled by merchant. Reason: {reason}"
        order.save()  # signal handles notification

        analytics.order_cancelled(request.user.id, order, cancelled_by='merchant', reason=reason)

        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'message': 'Order cancelled successfully',
            'data': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='buyer-search')
    def buyer_search(self, request):
        """
        Buyer searches their own placed orders.

        GET /api/v1/orders/orders/buyer-search/
        Query params:
          q          - search order_number or merchant name (optional)
          status     - NEW | CONTACTED | CONFIRMED | COMPLETED | CANCELLED (optional)
          date_from  - ISO date YYYY-MM-DD (optional)
          date_to    - ISO date YYYY-MM-DD (optional)
          min_amount - minimum total_amount (optional)
          max_amount - maximum total_amount (optional)
        """
        qs = OrderIntent.objects.select_related(
            'buyer', 'merchant', 'address', 'order_group'
        ).prefetch_related(
            'items__listing__merchant',
            'items__listing__category',
        ).filter(buyer=request.user).order_by('-created_at')

        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(order_number__icontains=q) |
                Q(merchant__display_name__icontains=q)
            )

        order_status = request.query_params.get('status', '').strip().upper()
        if order_status:
            qs = qs.filter(status=order_status)

        date_from = request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        min_amount = request.query_params.get('min_amount')
        if min_amount:
            qs = qs.filter(total_amount__gte=min_amount)

        max_amount = request.query_params.get('max_amount')
        if max_amount:
            qs = qs.filter(total_amount__lte=max_amount)

        orders = list(qs)
        _attach_primary_images(orders)
        serializer = self.get_serializer(orders, many=True)
        return Response({
            'success': True,
            'count': len(orders),
            'data': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='merchant-search')
    def merchant_search(self, request):
        """
        Merchant searches orders they have received.

        GET /api/v1/orders/orders/merchant-search/
        Query params:
          q          - search order_number, buyer name, or buyer phone (optional)
          status     - NEW | CONTACTED | CONFIRMED | COMPLETED | CANCELLED (optional)
          date_from  - ISO date YYYY-MM-DD (optional)
          date_to    - ISO date YYYY-MM-DD (optional)
          min_amount - minimum total_amount (optional)
          max_amount - maximum total_amount (optional)
        """
        if not hasattr(request.user, 'merchant_profile'):
            return Response({
                'success': False,
                'error': 'Only merchants can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)

        qs = OrderIntent.objects.select_related(
            'buyer', 'merchant', 'address', 'order_group'
        ).prefetch_related(
            'items__listing__merchant',
            'items__listing__category',
        ).filter(merchant=request.user.merchant_profile).order_by('-created_at')

        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(order_number__icontains=q) |
                Q(buyer__name__icontains=q) |
                Q(buyer__phone__icontains=q)
            )

        order_status = request.query_params.get('status', '').strip().upper()
        if order_status:
            qs = qs.filter(status=order_status)

        date_from = request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        min_amount = request.query_params.get('min_amount')
        if min_amount:
            qs = qs.filter(total_amount__gte=min_amount)

        max_amount = request.query_params.get('max_amount')
        if max_amount:
            qs = qs.filter(total_amount__lte=max_amount)

        orders = list(qs)
        _attach_primary_images(orders)
        serializer = self.get_serializer(orders, many=True)
        return Response({
            'success': True,
            'count': len(orders),
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
        _base = OrderIntent.objects.select_related(
            'buyer', 'merchant', 'address', 'order_group'
        ).prefetch_related('items__listing__merchant', 'items__listing__category')
        if role == 'merchant' and hasattr(request.user, 'merchant_profile'):
            queryset = _base.filter(merchant=request.user.merchant_profile)
        elif role == 'buyer':
            queryset = _base.filter(buyer=request.user)

        orders = list(queryset)
        _attach_primary_images(orders)
        serializer = self.get_serializer(orders, many=True)
        return Response({
            'success': True,
            'count': len(orders),
            'data': serializer.data
        })


class OrderGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for OrderGroup"""
    serializer_class = OrderGroupSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        groups = list(self.filter_queryset(self.get_queryset()))
        orders = [o for g in groups for o in g.orders.all()]
        _attach_primary_images(orders)
        serializer = self.get_serializer(groups, many=True)
        return Response({'success': True, 'count': len(groups), 'data': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        group = self.get_object()
        _attach_primary_images(list(group.orders.all()))
        serializer = self.get_serializer(group)
        return Response({'success': True, 'data': serializer.data})

    def get_queryset(self):
        return OrderGroup.objects.filter(
            buyer=self.request.user
        ).prefetch_related(
            'orders__items__listing__merchant',
            'orders__items__listing__category',
            'orders__merchant',
            'orders__buyer',
            'orders__address',
        ).order_by('-created_at')

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
        orders = list(
            OrderIntent.objects.filter(
                order_group=order_group
            ).select_related(
                'buyer', 'merchant', 'address', 'order_group'
            ).prefetch_related('items__listing__merchant', 'items__listing__category')
        )
        _attach_primary_images(orders)
        serializer = OrderIntentSerializer(orders, many=True)
        return Response({
            'success': True,
            'count': len(orders),
            'data': serializer.data
        })