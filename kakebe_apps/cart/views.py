from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404

from .models import Cart, CartItem, Wishlist, WishlistItem
from .serializers import (
    CartSerializer, CartItemSerializer, AddToCartSerializer,
    UpdateCartItemSerializer, WishlistSerializer, WishlistItemSerializer,
    AddToWishlistSerializer
)
from kakebe_apps.listings.models import Listing


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_or_create_cart(self, user):
        cart, created = Cart.objects.get_or_create(user=user)
        return cart

    def list(self, request):
        """Get user's cart with all items"""
        cart = self.get_or_create_cart(request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def items(self, request):
        """Get paginated cart items"""
        cart = self.get_or_create_cart(request.user)
        items = cart.items.select_related('listing').order_by('-created_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(items, request)

        if page is not None:
            serializer = CartItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = CartItemSerializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def count(self, request):
        """Get total number of items in cart"""
        cart = self.get_or_create_cart(request.user)
        return Response({
            'count': cart.total_items,
            'items_count': cart.items.count()
        })

    @action(detail=False, methods=['post'])
    def add(self, request):
        """Add item to cart or update quantity if exists"""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self.get_or_create_cart(request.user)
        listing = get_object_or_404(Listing, id=serializer.validated_data['listing_id'])
        quantity = serializer.validated_data['quantity']

        # Check if item already exists in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            listing=listing,
            defaults={'quantity': quantity}
        )

        if not created:
            # Update quantity if item already exists
            cart_item.quantity += quantity
            cart_item.save()
            message = "Cart item quantity updated"
        else:
            message = "Item added to cart"

        return Response({
            'message': message,
            'cart_item': CartItemSerializer(cart_item).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path='update/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """Update cart item quantity"""
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self.get_or_create_cart(request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        cart_item.quantity = serializer.validated_data['quantity']
        cart_item.save()

        return Response({
            'message': 'Cart item updated',
            'cart_item': CartItemSerializer(cart_item).data
        })

    @action(detail=False, methods=['delete'], url_path='remove/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """Remove item from cart"""
        cart = self.get_or_create_cart(request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        cart_item.delete()

        return Response({
            'message': 'Item removed from cart'
        }, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """Clear all items from cart"""
        cart = self.get_or_create_cart(request.user)
        cart.items.all().delete()

        return Response({
            'message': 'Cart cleared'
        }, status=status.HTTP_204_NO_CONTENT)


class WishlistViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_or_create_wishlist(self, user):
        wishlist, created = Wishlist.objects.get_or_create(user=user)
        return wishlist

    def list(self, request):
        """Get user's wishlist with all items"""
        wishlist = self.get_or_create_wishlist(request.user)
        serializer = WishlistSerializer(wishlist)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def items(self, request):
        """Get paginated wishlist items"""
        wishlist = self.get_or_create_wishlist(request.user)
        items = wishlist.items.select_related('listing').order_by('-created_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(items, request)

        if page is not None:
            serializer = WishlistItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = WishlistItemSerializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def count(self, request):
        """Get total number of items in wishlist"""
        wishlist = self.get_or_create_wishlist(request.user)
        return Response({
            'count': wishlist.total_items
        })

    @action(detail=False, methods=['post'])
    def add(self, request):
        """Add item to wishlist"""
        serializer = AddToWishlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wishlist = self.get_or_create_wishlist(request.user)
        listing = get_object_or_404(Listing, id=serializer.validated_data['listing_id'])

        # Check if item already exists in wishlist
        wishlist_item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            listing=listing
        )

        if not created:
            return Response({
                'message': 'Item already in wishlist',
                'wishlist_item': WishlistItemSerializer(wishlist_item).data
            }, status=status.HTTP_200_OK)

        return Response({
            'message': 'Item added to wishlist',
            'wishlist_item': WishlistItemSerializer(wishlist_item).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'], url_path='remove/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """Remove item from wishlist"""
        wishlist = self.get_or_create_wishlist(request.user)
        wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist=wishlist)

        wishlist_item.delete()

        return Response({
            'message': 'Item removed from wishlist'
        }, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete'], url_path='remove-by-listing/(?P<listing_id>[^/.]+)')
    def remove_by_listing(self, request, listing_id=None):
        """Remove item from wishlist by listing ID"""
        wishlist = self.get_or_create_wishlist(request.user)
        wishlist_item = get_object_or_404(WishlistItem, wishlist=wishlist, listing_id=listing_id)

        wishlist_item.delete()

        return Response({
            'message': 'Item removed from wishlist'
        }, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='check/(?P<listing_id>[^/.]+)')
    def check_item(self, request, listing_id=None):
        """Check if item is in wishlist"""
        wishlist = self.get_or_create_wishlist(request.user)
        exists = WishlistItem.objects.filter(wishlist=wishlist, listing_id=listing_id).exists()

        return Response({
            'in_wishlist': exists
        })

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """Clear all items from wishlist"""
        wishlist = self.get_or_create_wishlist(request.user)
        wishlist.items.all().delete()

        return Response({
            'message': 'Wishlist cleared'
        }, status=status.HTTP_204_NO_CONTENT)