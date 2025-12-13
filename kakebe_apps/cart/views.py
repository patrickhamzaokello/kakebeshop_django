# kakebe_apps/cart/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from kakebe_apps.listings.models import Listing
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer


class CartViewSet(viewsets.ViewSet):
    """
    Endpoints:
    - GET    /cart/           → View current user's cart
    - POST   /cart/add/       → Add/update item in cart
    - POST   /cart/remove/    → Remove item from cart
    - POST   /cart/clear/     → Clear entire cart
    """
    permission_classes = [IsAuthenticated]

    def _get_cart(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    # GET: Retrieve current cart
    def list(self, request):
        cart = self._get_cart(request)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    # POST: Add or update item in cart
    @action(detail=False, methods=['post'])
    def add(self, request):
        cart = self._get_cart(request)
        listing_id = request.data.get('listing_id')
        quantity = int(request.data.get('quantity', 1))

        if quantity < 1:
            return Response({"quantity": ["Must be at least 1."]}, status=status.HTTP_400_BAD_REQUEST)

        listing = get_object_or_404(
            Listing,
            id=listing_id,
            status='ACTIVE',
            category__allows_cart=True  # Only listings from categories that allow cart
        )

        cart_item, created = CartItem.objects.update_or_create(
            cart=cart,
            listing=listing,
            defaults={'quantity': quantity}
        )

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

    # POST: Remove specific item
    @action(detail=False, methods=['post'])
    def remove(self, request):
        cart = self._get_cart(request)
        listing_id = request.data.get('listing_id')

        if not listing_id:
            return Response({"listing_id": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        cart_item = get_object_or_404(CartItem, cart=cart, listing_id=listing_id)
        cart_item.delete()

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    # POST: Clear entire cart
    @action(detail=False, methods=['post'])
    def clear(self, request):
        cart = self._get_cart(request)
        cart.items.all().delete()
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)