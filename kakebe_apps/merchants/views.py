# kakebe_apps/merchants/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Merchant
from .serializers import MerchantSerializer, MerchantUpdateSerializer


class IsMerchantOwner(permissions.BasePermission):
    """
    Custom permission: only the owner (linked user) can edit their merchant profile.
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class MerchantViewSet(viewsets.ViewSet):
    """
    Public endpoints:
    - list: search merchants (active only)
    - retrieve: public merchant profile by UUID

    Authenticated merchant owner endpoints:
    - me: get/update own merchant profile
    """

    def get_queryset(self):
        return Merchant.objects.filter(status='ACTIVE', deleted_at__isnull=True)

    # Public: List active merchants
    def list(self, request):
        queryset = self.get_queryset().order_by('-rating', 'display_name')
        serializer = MerchantSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    # Public: Retrieve single merchant profile
    def retrieve(self, request, pk=None):
        merchant = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = MerchantSerializer(merchant, context={'request': request})
        return Response(serializer.data)

    # Authenticated: Get my own merchant profile
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        merchant = get_object_or_404(Merchant, user=request.user)
        serializer = MerchantSerializer(merchant, context={'request': request})
        return Response(serializer.data)

    # Authenticated: Update my own merchant profile
    @me.mapping.patch
    def update_me(self, request):
        merchant = get_object_or_404(Merchant, user=request.user)
        serializer = MerchantUpdateSerializer(
            merchant, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MerchantSerializer(merchant, context={'request': request}).data)

    # Optional: Future admin actions (e.g., verify merchant) can be added here