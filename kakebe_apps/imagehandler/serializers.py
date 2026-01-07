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
        read_only_fields = ['id', 'created_at']

    def get_cdn_url(self, obj):
        return obj.cdn_url()