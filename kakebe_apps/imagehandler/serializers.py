from rest_framework import serializers
from .models import ImageAsset


class PresignUploadSerializer(serializers.Serializer):
    image_type = serializers.ChoiceField(
        choices=["listing", "profile", "store_banner", "store_cover"]
    )
    image_group_id = serializers.UUIDField()  # NEW: Groups variants together
    variant = serializers.CharField()


class ConfirmUploadSerializer(serializers.Serializer):
    s3_key = serializers.CharField()
    image_type = serializers.CharField()
    image_group_id = serializers.UUIDField()  # NEW
    variant = serializers.CharField()
    width = serializers.IntegerField(min_value=1)
    height = serializers.IntegerField(min_value=1)
    size_bytes = serializers.IntegerField(min_value=1)


class AttachImagesToObjectSerializer(serializers.Serializer):
    """Attach confirmed draft images to a listing/profile/store"""
    image_group_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=10
    )
    object_id = serializers.UUIDField()
    image_type = serializers.ChoiceField(
        choices=["listing", "profile", "store_banner", "store_cover"]
    )


class ImageAssetSerializer(serializers.ModelSerializer):
    cdn_url = serializers.SerializerMethodField()

    class Meta:
        model = ImageAsset
        fields = [
            'id', 'image_group_id', 'object_id', 'image_type',
            'variant', 's3_key', 'cdn_url', 'width', 'height',
            'size_bytes', 'order', 'is_confirmed', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'cdn_url']

    def get_cdn_url(self, obj):
        return obj.cdn_url()

class ListingImageUploadSerializer(serializers.Serializer):
    """Serializer for uploading new images to a listing"""
    image_group_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=True,
        help_text="List of image group IDs to attach to listing"
    )

    def validate(self, attrs):
        image_group_ids = attrs.get('image_group_ids', [])

        # Verify all image groups belong to the user
        user = self.context['request'].user
        listing = self.context.get('listing')

        # Check ownership and confirmation status
        existing_groups = ImageAsset.objects.filter(
            owner=user,
            image_group_id__in=image_group_ids,
            is_confirmed=False,  # Draft images
            object_id__isnull=True  # Not yet attached to any object
        ).values_list('image_group_id', flat=True).distinct()

        missing_groups = set(image_group_ids) - set(existing_groups)
        if missing_groups:
            raise serializers.ValidationError({
                'image_group_ids': f"Image groups not found or already assigned: {missing_groups}"
            })

        return attrs

    def save(self):
        image_group_ids = self.validated_data['image_group_ids']
        listing = self.context['listing']

        # Update image assets to attach to this listing
        updated = ImageAsset.objects.filter(
            image_group_id__in=image_group_ids
        ).update(
            object_id=listing.id,
            is_confirmed=True
        )

        return updated


class ListingImageReorderSerializer(serializers.Serializer):
    """Serializer for reordering listing images"""
    image_group_order = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=True,
        help_text="List of image group IDs in desired order"
    )

    def validate(self, attrs):
        image_group_order = attrs.get('image_group_order', [])
        listing = self.context.get('listing')

        # Verify all image groups belong to this listing
        existing_groups = ImageAsset.objects.filter(
            object_id=listing.id,
            image_type="listing",
            is_confirmed=True
        ).values_list('image_group_id', flat=True).distinct()

        if len(set(image_group_order)) != len(existing_groups):
            raise serializers.ValidationError({
                'image_group_order': "Mismatch in number of image groups"
            })

        return attrs

    def save(self):
        image_group_order = self.validated_data['image_group_order']

        # Update order for each image group
        for order, group_id in enumerate(image_group_order):
            ImageAsset.objects.filter(
                image_group_id=group_id,
                image_type="listing"
            ).update(order=order)

        return image_group_order