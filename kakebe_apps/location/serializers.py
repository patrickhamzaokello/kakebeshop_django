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


class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = [
            'id', 'user', 'label', 'region', 'district', 'area',
            'landmark', 'latitude', 'longitude', 'is_default', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']

    def validate(self, attrs):
        """
        Validate address data
        """
        # Ensure at least one location field is provided
        if not attrs.get('area'):
            raise serializers.ValidationError({
                'area': 'Area is required'
            })

        return attrs

    def create(self, validated_data):
        """
        Create new address and handle default logic
        """
        user = self.context['request'].user
        is_default = validated_data.get('is_default', False)

        # If this is set as default, unset other defaults
        if is_default:
            UserAddress.objects.filter(user=user, is_default=True).update(
                is_default=False
            )

        # Create the address
        address = UserAddress.objects.create(user=user, **validated_data)

        return address

    def update(self, instance, validated_data):
        """
        Update address and handle default logic
        """
        is_default = validated_data.get('is_default', instance.is_default)

        # If setting as default, unset other defaults
        if is_default and not instance.is_default:
            UserAddress.objects.filter(
                user=instance.user,
                is_default=True
            ).exclude(id=instance.id).update(is_default=False)

        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class AddressCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for address creation"""

    class Meta:
        model = UserAddress
        fields = [
            'label', 'region', 'district', 'area', 'landmark',
            'latitude', 'longitude', 'is_default'
        ]

    def validate_label(self, value):
        """Ensure label is one of the allowed choices"""
        allowed_labels = ['HOME', 'WORK', 'OTHER']
        if value not in allowed_labels:
            raise serializers.ValidationError(
                f"Label must be one of: {', '.join(allowed_labels)}"
            )
        return value