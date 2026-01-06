from rest_framework import serializers


class PresignUploadSerializer(serializers.Serializer):
    image_type = serializers.ChoiceField(
        choices=["listing", "profile", "store_banner"]
    )
    object_id = serializers.CharField()
    variant = serializers.CharField()

class ConfirmUploadSerializer(serializers.Serializer):
    s3_key = serializers.CharField()
    image_type = serializers.CharField()
    variant = serializers.CharField()

    width = serializers.IntegerField(min_value=1)
    height = serializers.IntegerField(min_value=1)
    size_bytes = serializers.IntegerField(min_value=1)
