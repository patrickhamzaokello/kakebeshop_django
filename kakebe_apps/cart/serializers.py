from rest_framework import serializers
from .models import Cart, CartItem, Wishlist, WishlistItem
from kakebe_apps.listings.models import Listing


class ListingBasicSerializer(serializers.ModelSerializer):
    """Basic listing info for cart/wishlist items"""
    class Meta:
        model = Listing
        fields = ['id', 'title', 'price', 'image', 'slug']


class CartItemSerializer(serializers.ModelSerializer):
    listing = ListingBasicSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'listing', 'quantity', 'subtotal', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'total_price', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AddToCartSerializer(serializers.Serializer):
    listing_id = serializers.UUIDField()
    quantity = serializers.IntegerField(default=1, min_value=1)

    def validate_listing_id(self, value):
        try:
            Listing.objects.get(id=value)
        except Listing.DoesNotExist:
            raise serializers.ValidationError("Listing not found.")
        return value


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class WishlistItemSerializer(serializers.ModelSerializer):
    listing = ListingBasicSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ['id', 'listing', 'created_at']
        read_only_fields = ['id', 'created_at']


class WishlistSerializer(serializers.ModelSerializer):
    items = WishlistItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'items', 'total_items', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AddToWishlistSerializer(serializers.Serializer):
    listing_id = serializers.UUIDField()

    def validate_listing_id(self, value):
        try:
            Listing.objects.get(id=value)
        except Listing.DoesNotExist:
            raise serializers.ValidationError("Listing not found.")
        return value