from rest_framework import serializers
from .models import OrderIntent, OrderIntentItem, OrderGroup
from kakebe_apps.location.serializers import UserAddressSerializer
from kakebe_apps.listings.serializers import ListingListSerializer


class OrderIntentItemSerializer(serializers.ModelSerializer):
    listing = ListingListSerializer(read_only=True)

    class Meta:
        model = OrderIntentItem
        fields = ['id', 'listing', 'quantity', 'unit_price', 'total_price']



class OrderIntentSerializer(serializers.ModelSerializer):
    items = OrderIntentItemSerializer(many=True, read_only=True)
    address = UserAddressSerializer(read_only=True)
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)
    merchant_name = serializers.CharField(source='merchant.display_name', read_only=True)

    # Add group info
    order_group_number = serializers.CharField(
        source='order_group.group_number',
        read_only=True,
        allow_null=True
    )
    is_grouped = serializers.SerializerMethodField()

    class Meta:
        model = OrderIntent
        fields = [
            'id', 'order_number', 'buyer', 'buyer_name', 'merchant',
            'merchant_name', 'address', 'notes', 'total_amount',
            'delivery_fee', 'expected_delivery_date', 'status',
            'created_at', 'updated_at', 'items',
            'order_group', 'order_group_number', 'is_grouped'  # Group fields
        ]
        read_only_fields = ['id', 'order_number', 'buyer', 'created_at', 'updated_at']

    def get_is_grouped(self, obj):
        """Check if this order is part of a group"""
        return obj.order_group is not None


class OrderGroupSerializer(serializers.ModelSerializer):
    orders = OrderIntentSerializer(many=True, read_only=True)
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)

    class Meta:
        model = OrderGroup
        fields = [
            'id', 'group_number', 'buyer', 'buyer_name',
            'total_amount', 'total_orders', 'created_at', 'orders'
        ]
        read_only_fields = ['id', 'group_number', 'buyer', 'created_at']


class CheckoutRequestSerializer(serializers.Serializer):
    address_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True)
    delivery_fee = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True
    )
    expected_delivery_date = serializers.DateField(required=False, allow_null=True)