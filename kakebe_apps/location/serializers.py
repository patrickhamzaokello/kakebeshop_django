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
    user = serializers.PrimaryKeyRelatedField(read_only=True)  # Will be set automatically

    class Meta:
        model = UserAddress
        fields = [
            'id', 'user', 'label', 'region', 'district', 'area',
            'landmark', 'latitude', 'longitude', 'is_default', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']

    def validate(self, attrs):
        # Ensure only one address is default per user
        if attrs.get('is_default'):
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                if UserAddress.objects.filter(
                    user=request.user, is_default=True
                ).exclude(pk=self.instance.pk if self.instance else None).exists():
                    raise serializers.ValidationError(
                        {"is_default": "You already have a default address."}
                    )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)