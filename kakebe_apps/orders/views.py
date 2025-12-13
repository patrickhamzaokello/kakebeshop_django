# kakebe_apps/orders/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import OrderIntent
from .serializers import OrderIntentSerializer, OrderIntentUpdateSerializer


class OrderIntentViewSet(viewsets.ModelViewSet):
    queryset = OrderIntent.objects.select_related(
        'buyer', 'merchant', 'address'
    ).prefetch_related('items__listing')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return OrderIntentUpdateSerializer
        return OrderIntentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        elif hasattr(user, 'merchant'):
            # If user has a linked merchant
            return self.queryset.filter(merchant=user.merchant)
        else:
            # Regular buyer
            return self.queryset.filter(buyer=user)

    def perform_create(self, serializer):
        # All validation and creation logic is in serializer
        serializer.save()

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """Convenient endpoint for merchants to update status"""
        order = self.get_object()
        serializer = OrderIntentUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrderIntentSerializer(order).data)