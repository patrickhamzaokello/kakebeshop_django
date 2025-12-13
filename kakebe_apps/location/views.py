# kakebe_apps/location/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Location, UserAddress
from .serializers import LocationSerializer, UserAddressSerializer


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only endpoint for Locations (used by listings, search, etc.)
    Supports search by region, district, area.
    """
    queryset = Location.objects.filter(is_active=True).order_by('region', 'district', 'area')
    serializer_class = LocationSerializer
    permission_classes = [permissions.AllowAny]

    filterset_fields = ['region', 'district', 'area']
    search_fields = ['region', 'district', 'area', 'address']
    ordering_fields = ['region', 'district', 'area']


class UserAddressViewSet(viewsets.ModelViewSet):
    """
    Private endpoint for authenticated users to manage their own addresses.
    """
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserAddress.objects.filter(user=self.request.user).order_by('-is_default', 'created_at')

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """
        Custom action: /user-addresses/{id}/set_default/
        Makes this address the default and unsets others.
        """
        address = self.get_object()
        UserAddress.objects.filter(user=request.user).update(is_default=False)
        address.is_default = True
        address.save()
        return Response(UserAddressSerializer(address, context={'request': request}).data)