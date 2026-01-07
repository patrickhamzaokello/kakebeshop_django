import uuid
from django.conf import settings
from django.db import models


class ImageAsset(models.Model):
    IMAGE_TYPES = (
        ("listing", "Listing"),
        ("profile", "Profile"),
        ("store_banner", "Store Banner"),
        ("store_cover", "Store Cover"),
    )

    VARIANT_CHOICES = (
        ("thumb", "Thumbnail"),
        ("medium", "Medium"),
        ("large", "Large"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="image_assets"
    )

    # NEW: Groups variants together (thumb/medium/large of same upload)
    image_group_id = models.UUIDField(db_index=True)

    # Can be null initially (draft uploads), set when listing is created
    object_id = models.UUIDField(db_index=True, null=True, blank=True)

    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES)
    variant = models.CharField(max_length=20, choices=VARIANT_CHOICES)

    s3_key = models.CharField(max_length=500, unique=True)

    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    size_bytes = models.PositiveIntegerField()

    order = models.PositiveIntegerField(default=0)

    is_confirmed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'image_assets'
        indexes = [
            models.Index(fields=["image_type", "object_id"]),
            models.Index(fields=["image_group_id"]),
            models.Index(fields=["owner", "is_confirmed", "object_id"]),
            models.Index(fields=["created_at"]),
        ]
        unique_together = (
            ("image_group_id", "variant"),
        )

    def cdn_url(self):
        return f"{settings.AWS_CLOUDFRONT_DOMAIN}/{self.s3_key}"

    def __str__(self):
        return f"{self.image_type}:{self.object_id} [{self.variant}]"