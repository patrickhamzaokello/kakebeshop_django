# kakebe_apps/orders/serializers.py

from rest_framework import serializers
from django.db import transaction
from decimal import Decimal

from .models import OrderIntent, OrderIntentItem
from kakebe_apps.listings.models import Listing
from kakebe_apps.location.models import UserAddress
from kakebe_apps.merchants.models import Merchant


class OrderIntentItemSerializer(serializers.ModelSerializer):
    listing_id = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.all(),
        source='listing',
        write_only=True
    )
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    listing_image = serializers.ImageField(source='listing.main_image', read_only=True)  # adjust if field name differs

    class Meta:
        model = OrderIntentItem
        fields = [
            'id', 'listing_id', 'listing_title', 'listing_image',
            'quantity', 'unit_price', 'total_price', 'created_at'
        ]
        read_only_fields = ['unit_price', 'total_price', 'created_at']

    def validate(self, attrs):
        listing = attrs['listing']
        quantity = attrs['quantity']

        if not listing.is_active:
            raise serializers.ValidationError("Cannot order an inactive listing.")

        if listing.stock < quantity:
            raise serializers.ValidationError(
                f"Only {listing.stock} units available for {listing.title}."
            )

        # Set unit_price from current listing price
        attrs['unit_price'] = listing.price
        attrs['total_price'] = listing.price * quantity

        return attrs


class OrderIntentSerializer(serializers.ModelSerializer):
    items = OrderIntentItemSerializer(many=True, write_only=True)
    order_items = OrderIntentItemSerializer(many=True, source='items', read_only=True)
    buyer = serializers.StringRelatedField(read_only=True)
    merchant = serializers.PrimaryKeyRelatedField(queryset=Merchant.objects.all())
    address = serializers.PrimaryKeyRelatedField(queryset=UserAddress.objects.all())

    class Meta:
        model = OrderIntent
        fields = [
            'id', 'order_number', 'buyer', 'merchant', 'address', 'notes',
            'total_amount', 'delivery_fee', 'expected_delivery_date',
            'status', 'cancelled_by', 'cancellation_reason',
            'created_at', 'updated_at',
            'items', 'order_items'
        ]
        read_only_fields = [
            'id', 'order_number', 'buyer', 'total_amount',
            'status', 'cancelled_by', 'cancellation_reason',
            'created_at', 'updated_at'
        ]

    def validate_address(self, address):
        if address.user != self.context['request'].user:
            raise serializers.ValidationError("You can only use your own addresses.")
        return address

    def validate_merchant(self, merchant):
        # Optional: ensure all items belong to this merchant
        return merchant

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        request = self.context['request']
        validated_data['buyer'] = request.user

        # Calculate total
        total_amount = Decimal('0.0')
        for item_data in items_data:
            total_amount += item_data['total_price']

        validated_data['total_amount'] = total_amount

        # Generate order number (you might have a custom logic)
        import string
        import random
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        validated_data['order_number'] = f"ORD-{suffix}"

        order = OrderIntent.objects.create(**validated_data)

        # Create items
        order_items = []
        for item_data in items_data:
            order_items.append(OrderIntentItem(
                order_intent=order,
                listing=item_data['listing'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_data['total_price']
            ))
        OrderIntentItem.objects.bulk_create(order_items)

        # Optional: reduce stock
        for item_data in items_data:
            listing = item_data['listing']
            listing.stock -= item_data['quantity']
            listing.save(update_fields=['stock'])

        return order


class OrderIntentUpdateSerializer(serializers.ModelSerializer):
    """Limited serializer for status updates (used by merchant/admin)"""
    class Meta:
        model = OrderIntent
        fields = [
            'status', 'delivery_fee', 'expected_delivery_date',
            'cancelled_by', 'cancellation_reason'
        ]

    def validate(self, attrs):
        status = attrs.get('status')
        instance = self.instance

        if status == 'CANCELLED' and not attrs.get('cancellation_reason'):
            raise serializers.ValidationError({"cancellation_reason": "This field is required when cancelling."})

        # Optional: add status transition rules
        valid_transitions = {
            'NEW': ['CONTACTED', 'CONFIRMED', 'CANCELLED'],
            'CONTACTED': ['CONFIRMED', 'CANCELLED'],
            'CONFIRMED': ['COMPLETED', 'CANCELLED'],
        }
        if status != instance.status and status not in valid_transitions.get(instance.status, []):
            raise serializers.ValidationError(f"Cannot change status from {instance.status} to {status}.")

        return attrs