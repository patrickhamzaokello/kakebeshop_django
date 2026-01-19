# kakebe_apps/listings/models.py
# UPDATED: Modified images property to return only thumb and large variants

import uuid

from django.db import models
from django.core.validators import MinValueValidator

from kakebe_apps.categories.models import Category, Tag
from kakebe_apps.imagehandler.models import ImageAsset
from kakebe_apps.merchants.models import Merchant


class Listing(models.Model):
    LISTING_TYPE_CHOICES = [
        ('PRODUCT', 'Product'),
        ('SERVICE', 'Service'),
    ]

    PRICE_TYPE_CHOICES = [
        ('FIXED', 'Fixed'),
        ('RANGE', 'Range'),
        ('ON_REQUEST', 'On Request'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Review'),
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
        ('DEACTIVATED', 'Deactivated'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.CASCADE,
        related_name='listings'
    )
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    listing_type = models.CharField(max_length=20, choices=LISTING_TYPE_CHOICES)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='listings'
    )

    tags = models.ManyToManyField(Tag, through='ListingTag', related_name='listings')

    # Pricing
    price_type = models.CharField(max_length=20, choices=PRICE_TYPE_CHOICES)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    price_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    price_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default='UGX')
    is_price_negotiable = models.BooleanField(default=False)

    # Status and verification
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True
    )
    rejection_reason = models.TextField(null=True, blank=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    # Featured settings
    is_featured = models.BooleanField(default=False, db_index=True)
    featured_until = models.DateTimeField(null=True, blank=True)
    featured_order = models.PositiveIntegerField(default=0)

    # Engagement metrics
    views_count = models.PositiveIntegerField(default=0)
    contact_count = models.PositiveIntegerField(default=0)

    # Additional data
    metadata = models.JSONField(null=True, blank=True)

    # Timestamps
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'listings'
        indexes = [
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['is_verified', 'status']),
            models.Index(fields=['is_featured', 'is_verified', 'status']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['listing_type', 'status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        """Check if listing is verified, active, and not deleted"""
        return (
                self.status == 'ACTIVE'
                and self.is_verified
                and self.deleted_at is None
        )

    @property
    def primary_image(self):
        """Get the primary image or first image using ImageAsset model"""
        # Get the first image group for this listing
        first_group = (
            ImageAsset.objects
            .filter(
                image_type="listing",
                object_id=self.id,
                is_confirmed=True
            )
            .order_by("order", "created_at")
            .values_list("image_group_id", flat=True)
            .first()
        )

        if not first_group:
            return None

        # Get the THUMB variant of the first image group
        image_asset = ImageAsset.objects.filter(
            image_group_id=first_group,
            variant="thumb"
        ).first()

        # If thumb variant doesn't exist, fall back to medium
        if not image_asset:
            image_asset = ImageAsset.objects.filter(
                image_group_id=first_group,
                variant="medium"
            ).first()

        # If medium doesn't exist, get any variant from the group
        if not image_asset:
            image_asset = ImageAsset.objects.filter(
                image_group_id=first_group
            ).first()

        if image_asset:
            return {
                'id': str(image_asset.id),
                'image': image_asset.cdn_url(),
                'width': image_asset.width,
                'height': image_asset.height,
                'variant': image_asset.variant,
                'image_group_id': str(image_asset.image_group_id)
            }
        return None

    @property
    def images(self):
        """
        Get all images for this listing.

        UPDATED: Returns only THUMB and LARGE variants for optimized display.
        - THUMB: Used for thumbnails gallery below the main image
        - LARGE: Used for main image display when thumbnail is clicked
        """
        image_groups = (
            ImageAsset.objects
            .filter(
                image_type="listing",
                object_id=self.id,
                is_confirmed=True
            )
            .order_by("order", "created_at")
            .values_list("image_group_id", flat=True)
            .distinct()
        )

        images_list = []
        for group_id in image_groups:
            # Get only THUMB and LARGE variants for this group
            group_images = ImageAsset.objects.filter(
                image_group_id=group_id,
                is_confirmed=True,
                variant__in=['thumb', 'large']  # Only thumb and large
            ).order_by('order')

            group_dict = {}
            for img in group_images:
                group_dict[img.variant] = {
                    'id': str(img.id),
                    'image': img.cdn_url(),
                    'width': img.width,
                    'height': img.height,
                    'size_bytes': img.size_bytes,
                    'order': img.order
                }

            # Only add if we have both thumb and large (or at least one)
            if group_dict:
                images_list.append(group_dict)

        return images_list

    def soft_delete(self):
        """Soft delete the listing"""
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.status = 'DEACTIVATED'
        self.save(update_fields=['deleted_at', 'status'])

    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])

    def increment_contacts(self):
        """Increment contact count"""
        self.contact_count += 1
        self.save(update_fields=['contact_count'])


class ListingTag(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'listing_tags'
        unique_together = ('listing', 'tag')
        indexes = [
            models.Index(fields=['listing']),
            models.Index(fields=['tag']),
        ]

    def __str__(self):
        return f"{self.listing.title} - {self.tag.name}"


class ListingBusinessHour(models.Model):
    DAY_CHOICES = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='business_hours'
    )
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    opens_at = models.TimeField(null=True, blank=True)
    closes_at = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'listing_business_hours'
        unique_together = ('listing', 'day')
        indexes = [
            models.Index(fields=['listing']),
            models.Index(fields=['day']),
        ]
        ordering = ['day']

    def __str__(self):
        return f"{self.listing.title} - {self.get_day_display()}"