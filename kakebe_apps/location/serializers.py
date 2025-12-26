# kakebe_apps/location/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Location, UserAddress

User = get_user_model()

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [
            'id', 'region', 'district', 'area', 'latitude', 'longitude',
            'address', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AddressCreateSerializer(serializers.ModelSerializer):
    """Serializer for map-based address creation"""

    class Meta:
        model = UserAddress
        fields = [
            'label', 'region', 'district', 'area', 'landmark',
            'latitude', 'longitude', 'is_default'
        ]

    def validate(self, attrs):
        """Validate address data"""
        # Ensure GPS coordinates are provided
        if not attrs.get('latitude') or not attrs.get('longitude'):
            raise serializers.ValidationError({
                'location': 'GPS coordinates are required'
            })

        # Ensure location details are provided (from reverse geocoding)
        if not attrs.get('region') or not attrs.get('district'):
            raise serializers.ValidationError({
                'location': 'Location details are required'
            })

        # Landmark is optional but recommended
        if not attrs.get('landmark'):
            attrs['landmark'] = f"{attrs.get('area', 'Selected location')}"

        return attrs

    def validate_label(self, value):
        """Ensure label is one of the allowed choices"""
        allowed_labels = ['HOME', 'WORK', 'OTHER']
        if value not in allowed_labels:
            raise serializers.ValidationError(
                f"Label must be one of: {', '.join(allowed_labels)}"
            )
        return value


class UserAddressSerializer(serializers.ModelSerializer):
    """Full address serializer with all fields"""

    class Meta:
        model = UserAddress
        fields = [
            'id', 'user', 'label', 'region', 'district', 'area',
            'landmark', 'latitude', 'longitude', 'is_default', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']