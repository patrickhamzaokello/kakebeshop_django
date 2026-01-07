from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .serializers import (
    PresignUploadSerializer,
    ConfirmUploadSerializer,
    AttachImagesToObjectSerializer,
    ImageAssetSerializer
)
from .rules import IMAGE_RULES
from .utils import build_s3_key
from .s3 import generate_presigned_put_url
from .models import ImageAsset


class PresignUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PresignUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_type = serializer.validated_data["image_type"]
        image_group_id = serializer.validated_data["image_group_id"]
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

        # Build S3 key using image_group_id instead of object_id
        s3_key = build_s3_key(image_type, str(image_group_id), variant)

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

        # Create ImageAsset with image_group_id, object_id is null for now (draft)
        asset = ImageAsset.objects.create(
            owner=request.user,
            image_type=data["image_type"],
            image_group_id=data["image_group_id"],
            object_id=None,  # Will be set when attached to listing
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
                "image_group_id": asset.image_group_id,
                "cdn_url": asset.cdn_url(),
            },
            status=status.HTTP_201_CREATED,
        )


class AttachImagesToObjectView(APIView):
    """
    Attach confirmed draft images to a listing/profile/store.
    Called after listing is created on frontend.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = AttachImagesToObjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_group_ids = serializer.validated_data["image_group_ids"]
        object_id = serializer.validated_data["object_id"]
        image_type = serializer.validated_data["image_type"]

        # Verify all image groups exist and belong to user
        for group_id in image_group_ids:
            group_images = ImageAsset.objects.filter(
                image_group_id=group_id,
                owner=request.user,
                image_type=image_type,
                is_confirmed=True
            )

            if not group_images.exists():
                return Response(
                    {"detail": f"Image group {group_id} not found or not confirmed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Attach all images to object_id with proper ordering
        for order, group_id in enumerate(image_group_ids):
            ImageAsset.objects.filter(
                image_group_id=group_id,
                owner=request.user
            ).update(
                object_id=object_id,
                order=order
            )

        # Return updated images
        attached_images = ImageAsset.objects.filter(
            object_id=object_id,
            owner=request.user
        ).order_by('order', 'variant')

        return Response(
            {
                "detail": "Images attached successfully",
                "images": ImageAssetSerializer(attached_images, many=True).data
            },
            status=status.HTTP_200_OK,
        )


class ReorderImagesView(APIView):
    """Reorder images for a listing/profile"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        object_id = request.data.get('object_id')
        image_group_ids = request.data.get('image_group_ids', [])

        if not object_id or not image_group_ids:
            return Response(
                {"detail": "object_id and image_group_ids required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify ownership
        for order, group_id in enumerate(image_group_ids):
            ImageAsset.objects.filter(
                image_group_id=group_id,
                object_id=object_id,
                owner=request.user
            ).update(order=order)

        return Response({"detail": "Images reordered successfully"})


class CleanupAbandonedUploadsView(APIView):
    """
    Cleanup draft images older than 24 hours.
    Can be called by a cron job or manually.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cutoff_time = timezone.now() - timedelta(hours=24)

        # Find abandoned uploads (confirmed but not attached to any object)
        abandoned = ImageAsset.objects.filter(
            owner=request.user,
            object_id__isnull=True,
            is_confirmed=True,
            created_at__lt=cutoff_time
        )

        count = abandoned.count()

        # TODO: Delete from S3 before deleting from DB
        # for asset in abandoned:
        #     delete_from_s3(asset.s3_key)

        abandoned.delete()

        return Response({
            "detail": f"Cleaned up {count} abandoned uploads"
        })


class MyDraftImagesView(APIView):
    """Get current user's draft images (not attached to any object yet)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        image_type = request.query_params.get('image_type')

        queryset = ImageAsset.objects.filter(
            owner=request.user,
            object_id__isnull=True,
            is_confirmed=True
        )

        if image_type:
            queryset = queryset.filter(image_type=image_type)

        # Group by image_group_id
        from itertools import groupby
        from operator import attrgetter

        queryset = queryset.order_by('image_group_id', 'variant')

        grouped = {}
        for group_id, images in groupby(queryset, key=attrgetter('image_group_id')):
            images_list = list(images)
            grouped[str(group_id)] = {
                'image_group_id': group_id,
                'created_at': images_list[0].created_at,
                'variants': {img.variant: ImageAssetSerializer(img).data for img in images_list}
            }

        return Response({
            'draft_images': list(grouped.values())
        })