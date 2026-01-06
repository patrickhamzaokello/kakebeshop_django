from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .serializers import PresignUploadSerializer
from .rules import IMAGE_RULES
from .utils import build_s3_key
from .s3 import generate_presigned_put_url

from .models import ImageAsset
from .serializers import ConfirmUploadSerializer


class PresignUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PresignUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_type = serializer.validated_data["image_type"]
        object_id = serializer.validated_data["object_id"]
        variant = serializer.validated_data["variant"]

        rules = IMAGE_RULES.get(image_type)
        if not rules:
            return Response(
                {"detail": "Unsupported image type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if variant not in rules["variants"]:
            return Response(
                {"detail": "Invalid variant"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        s3_key = build_s3_key(image_type, object_id, variant)

        upload_url = generate_presigned_put_url(s3_key)

        return Response(
            {
                "upload_url": upload_url,
                "s3_key": s3_key,
                "expires_in": 300,
            }
        )

class ConfirmUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConfirmUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        rules = IMAGE_RULES.get(data["image_type"])
        if not rules:
            return Response(
                {"detail": "Invalid image type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        variant_rules = rules["variants"].get(data["variant"])
        if not variant_rules:
            return Response(
                {"detail": "Invalid variant"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if data["size_bytes"] > variant_rules["max_size"]:
            return Response(
                {"detail": "Image exceeds size limit"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset = ImageAsset.objects.create(
            owner=request.user,
            image_type=data["image_type"],
            s3_key=data["s3_key"],
            variant=data["variant"],
            width=data["width"],
            height=data["height"],
            size_bytes=data["size_bytes"],
            is_confirmed=True,
        )

        return Response(
            {
                "id": asset.id,
                "cdn_url": asset.cdn_url(),
            },
            status=status.HTTP_201_CREATED,
        )
