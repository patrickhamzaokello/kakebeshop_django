# kakebe_apps/transactions/serializers.py

from rest_framework import serializers

from .models import Transaction
from kakebe_apps.orders.models import OrderIntent


class TransactionSerializer(serializers.ModelSerializer):
    order_intent = serializers.PrimaryKeyRelatedField(
        queryset=OrderIntent.objects.all(),
        write_only=True
    )
    order_number = serializers.CharField(source='order_intent.order_number', read_only=True)
    buyer = serializers.StringRelatedField(source='order_intent.buyer', read_only=True)
    merchant = serializers.StringRelatedField(source='order_intent.merchant', read_only=True)
    total_amount = serializers.DecimalField(
        source='order_intent.total_amount',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_number', 'order_intent', 'order_number',
            'amount', 'currency', 'payment_method', 'payment_reference',
            'status', 'completed_at', 'created_at',
            'buyer', 'merchant', 'total_amount'
        ]
        read_only_fields = ['transaction_number', 'status', 'completed_at', 'created_at','buyer', 'merchant', 'total_amount']

    def validate(self, attrs):
        order_intent = attrs['order_intent']
        request = self.context['request']

        # Ensure the order belongs to the buyer
        if order_intent.buyer != request.user:
            raise serializers.ValidationError("You can only create transactions for your own orders.")

        # Check order status – only allow payment if order is in acceptable state
        if order_intent.status not in ['NEW', 'CONTACTED', 'CONFIRMED']:
            raise serializers.ValidationError(
                f"Cannot initiate payment for order in status: {order_intent.get_status_display()}."
            )

        # Amount must match order total (or total + delivery if applicable)
        expected_amount = order_intent.total_amount
        if order_intent.delivery_fee:
            expected_amount += order_intent.delivery_fee

        if attrs['amount'] != expected_amount:
            raise serializers.ValidationError(
                f"Amount must be exactly {expected_amount} {order_intent.currency or 'UGX'}."
            )

        # Optional: Prevent multiple pending transactions
        if Transaction.objects.filter(
            order_intent=order_intent,
            status__in=['PENDING', 'COMPLETED']
        ).exists():
            raise serializers.ValidationError("This order already has an active or completed transaction.")

        return attrs

    def create(self, validated_data):
        import string
        import random

        # Generate unique transaction number
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        transaction_number = f"TXN-{suffix}"

        transaction = Transaction.objects.create(
            transaction_number=transaction_number,
            **validated_data
        )
        return transaction


class TransactionStatusUpdateSerializer(serializers.ModelSerializer):
    """Used only by admin or webhook to update transaction status"""
    class Meta:
        model = Transaction
        fields = ['status', 'payment_reference', 'completed_at']
        read_only_fields = ['payment_reference',]  # can be set by webhook

    def validate_status(self, value):
        instance = self.instance
        valid_transitions = {
            'PENDING': ['COMPLETED', 'FAILED'],
            'COMPLETED': ['REFUNDED'],
            'FAILED': ['PENDING'],  # retry possible?
        }
        if value != instance.status and value not in valid_transitions.get(instance.status, []):
            raise serializers.ValidationError(f"Invalid status transition from {instance.status} to {value}.")
        return value