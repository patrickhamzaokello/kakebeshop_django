from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import UserAddress, Location
from .serializers import UserAddressSerializer, AddressCreateSerializer


class UserAddressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user addresses
    """
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return addresses for the authenticated user"""
        return UserAddress.objects.filter(
            user=self.request.user
        ).order_by('-is_default', '-created_at')

    def get_serializer_class(self):
        """Use different serializer for creation"""
        if self.action == 'create':
            return AddressCreateSerializer
        return UserAddressSerializer

    def create(self, request, *args, **kwargs):
        """Create a new address"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check if this is the user's first address
        user_has_addresses = UserAddress.objects.filter(
            user=request.user
        ).exists()

        # If no addresses exist, make this one default
        if not user_has_addresses:
            serializer.validated_data['is_default'] = True

        # Handle default address logic
        is_default = serializer.validated_data.get('is_default', False)
        if is_default:
            UserAddress.objects.filter(
                user=request.user,
                is_default=True
            ).update(is_default=False)

        # Create the address
        address = UserAddress.objects.create(
            user=request.user,
            **serializer.validated_data
        )

        # Return with full serializer
        output_serializer = UserAddressSerializer(address)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Update an address"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Ensure user owns this address
        if instance.user != request.user:
            return Response(
                {'error': 'You do not have permission to edit this address'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Delete an address"""
        instance = self.get_object()

        # Ensure user owns this address
        if instance.user != request.user:
            return Response(
                {'error': 'You do not have permission to delete this address'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Prevent deletion of default address if it's the only one
        if instance.is_default:
            other_addresses = UserAddress.objects.filter(
                user=request.user
            ).exclude(id=instance.id)

            if other_addresses.exists():
                # Set another address as default
                other_addresses.first().update(is_default=True)
            elif other_addresses.count() == 0:
                return Response(
                    {'error': 'Cannot delete your only address'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, pk=None):
        """Set an address as default"""
        address = self.get_object()

        # Ensure user owns this address
        if address.user != request.user:
            return Response(
                {'error': 'You do not have permission to modify this address'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Unset all other default addresses
        UserAddress.objects.filter(
            user=request.user,
            is_default=True
        ).exclude(id=address.id).update(is_default=False)

        # Set this as default
        address.is_default = True
        address.save()

        serializer = self.get_serializer(address)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='default')
    def get_default(self, request):
        """Get the default address"""
        address = UserAddress.objects.filter(
            user=request.user,
            is_default=True
        ).first()

        if not address:
            return Response(
                {'error': 'No default address found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(address)
        return Response(serializer.data)


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for browsing available locations
    """
    queryset = Location.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='regions')
    def list_regions(self, request):
        """Get list of unique regions"""
        regions = Location.objects.filter(
            is_active=True
        ).values_list('region', flat=True).distinct().order_by('region')

        return Response(list(regions))

    @action(detail=False, methods=['get'], url_path='districts')
    def list_districts(self, request):
        """Get list of districts for a region"""
        region = request.query_params.get('region')

        queryset = Location.objects.filter(is_active=True)
        if region:
            queryset = queryset.filter(region=region)

        districts = queryset.values_list(
            'district', flat=True
        ).distinct().order_by('district')

        return Response(list(districts))

    @action(detail=False, methods=['get'], url_path='areas')
    def list_areas(self, request):
        """Get list of areas for a district"""
        region = request.query_params.get('region')
        district = request.query_params.get('district')

        queryset = Location.objects.filter(is_active=True)
        if region:
            queryset = queryset.filter(region=region)
        if district:
            queryset = queryset.filter(district=district)

        areas = queryset.values_list(
            'area', flat=True
        ).distinct().order_by('area')

        return Response(list(areas))