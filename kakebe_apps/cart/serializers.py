# kakebe_apps/cart/serializers.py

from rest_framework import serializers
from kakebe_apps.listings.serializers import ListingSerializer  # Minimal listing info in cart
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    listing = ListingSerializer(read_only=True)
    listing_id = serializers.UUIDField(write_only=True)  # For adding/updating

    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id', 'listing', 'listing_id', 'quantity',
            'total_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_price']

    def get_total_price(self, obj):
        # Assumes fixed price; adjust if using price ranges or negotiable
        if obj.listing.price:
            return obj.quantity * obj.listing.price
        return None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(source='items.count', read_only=True)
    total_items_quantity = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'items_count', 'total_items_quantity', 'subtotal', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_items_quantity(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_subtotal(self, obj):
        total = sum(
            (item.quantity * item.listing.price)
            for item in obj.items.all()
            if item.listing.price
        )
        return total