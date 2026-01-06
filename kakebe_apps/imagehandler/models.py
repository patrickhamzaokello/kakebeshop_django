from django.conf import settings
from django.db import models


class ImageAsset(models.Model):
    IMAGE_TYPES = (
        ("listing", "Listing"),
        ("profile", "Profile"),
        ("store_banner", "Store Banner"),
        ("store_cover", "Store Cover"),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="image_assets"
    )

    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES)

    s3_key = models.CharField(max_length=500, unique=True)
    variant = models.CharField(max_length=20)

    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    size_bytes = models.PositiveIntegerField()

    is_confirmed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def cdn_url(self):
        from django.conf import settings
        return f"{settings.AWS_CLOUDFRONT_DOMAIN}/{self.s3_key}"

    def __str__(self):
        return f"{self.image_type} - {self.variant}"
