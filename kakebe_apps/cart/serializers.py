from rest_framework import serializers
from .models import Cart, CartItem, Wishlist, WishlistItem
from kakebe_apps.listings.models import Listing


class ListingBasicSerializer(serializers.ModelSerializer):
    """Basic listing info for cart/wishlist items"""
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = ['id', 'title', 'price', 'primary_image', 'status', 'is_active']

    def get_primary_image(self, obj):
        """
        Get the primary image URL or first image.

        FIXED: The obj.primary_image returns a dict, not an object.
        We need to handle it as a dictionary.
        """
        primary_img = obj.primary_image

        if primary_img and isinstance(primary_img, dict):
            # primary_img is already a dictionary with structure:
            # {
            #     'id': '...',
            #     'image': 'https://...',
            #     'width': 240,
            #     'height': 240,
            #     'variant': 'thumb',
            #     'image_group_id': '...'
            # }
            return {
                'id': primary_img.get('id'),
                'image': primary_img.get('image'),
                'width': primary_img.get('width'),
                'height': primary_img.get('height'),
                'variant': primary_img.get('variant', 'thumb')
            }

        # Fallback: if no primary image, try to get from images list
        if hasattr(obj, 'images') and obj.images:
            images_list = obj.images
            if images_list and len(images_list) > 0:
                first_image = images_list[0]
                # Get thumb variant from first image
                if isinstance(first_image, dict) and 'thumb' in first_image:
                    thumb = first_image['thumb']
                    return {
                        'id': thumb.get('id'),
                        'image': thumb.get('image'),
                        'width': thumb.get('width'),
                        'height': thumb.get('height'),
                        'variant': 'thumb'
                    }

        return None


class CartItemSerializer(serializers.ModelSerializer):
    listing = ListingBasicSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'listing', 'quantity', 'subtotal', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_subtotal(self, obj):
        """Calculate subtotal for this cart item"""
        return obj.subtotal


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'total_price', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        """Calculate total price of all items in cart"""
        return obj.total_price


class AddToCartSerializer(serializers.Serializer):
    listing_id = serializers.UUIDField()
    quantity = serializers.IntegerField(default=1, min_value=1)

    def validate_listing_id(self, value):
        try:
            listing = Listing.objects.get(id=value)
            # Check if listing is active
            if not listing.is_active:
                raise serializers.ValidationError("This listing is no longer available.")
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
            listing = Listing.objects.get(id=value)
            # Check if listing is active
            if not listing.is_active:
                raise serializers.ValidationError("This listing is no longer available.")
        except Listing.DoesNotExist:
            raise serializers.ValidationError("Listing not found.")
        return value