# kakebe_apps/transactions/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404

from .models import Transaction
from .serializers import TransactionSerializer, TransactionStatusUpdateSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.select_related('order_intent', 'order_intent__buyer', 'order_intent__merchant')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['update_status']:
            return TransactionStatusUpdateSerializer
        return TransactionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        elif hasattr(user, 'merchant'):  # assuming merchant users have a related merchant
            return self.queryset.filter(order_intent__merchant=user.merchant)
        else:
            # Buyer: only see their own transactions
            return self.queryset.filter(order_intent__buyer=user)

    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def update_status(self, request, pk=None):
        """
        Admin-only endpoint to update transaction status.
        In production, replace with secure webhook from payment provider.
        """
        transaction = self.get_object()
        serializer = self.get_serializer(transaction, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if serializer.validated_data['status'] == 'COMPLETED':
            # Auto-update order status if needed
            order = transaction.order_intent
            if order.status in ['NEW', 'CONTACTED', 'CONFIRMED']:
                order.status = 'CONFIRMED'  # or 'PROCESSING'
                order.save()

        return Response(TransactionSerializer(transaction).data)