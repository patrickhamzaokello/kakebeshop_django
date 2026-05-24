import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from kakebe_apps.categories.models import Category
from kakebe_apps.imagehandler.models import ImageAsset
from kakebe_apps.merchants.models import Merchant


class PromotionalBanner(models.Model):
    """
    A promotional banner/carousel item that can link to listings, categories, or URLs.
    """
    DISPLAY_TYPE_CHOICES = [
        ('CAROUSEL', 'Carousel/Slider'),
        ('BANNER', 'Banner'),
        ('AD', 'Advertisement'),
    ]

    PLACEMENT_CHOICES = [
        ('HOME_TOP', 'Home Page - Top'),
        ('HOME_MIDDLE', 'Home Page - Middle'),
        ('CATEGORY_TOP', 'Category Page - Top'),
        ('SEARCH_TOP', 'Search Results - Top'),
    ]

    LINK_TYPE_CHOICES = [
        ('LISTING', 'Single Listing'),
        ('LISTINGS', 'Multiple Listings'),
        ('CATEGORY', 'Category'),
        ('MERCHANT', 'Merchant'),
        ('URL', 'External URL'),
        ('NONE', 'No Link'),
    ]

    PLATFORM_CHOICES = [
        ('ALL', 'All Platforms'),
        ('WEB', 'Web Only'),
        ('MOBILE', 'Mobile Only'),
        ('ANDROID', 'Android Only'),
        ('IOS', 'iOS Only'),
    ]

    # Basic Info
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Display Settings
    display_type = models.CharField(max_length=20, choices=DISPLAY_TYPE_CHOICES)
    placement = models.CharField(max_length=30, choices=PLACEMENT_CHOICES)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='ALL')

    # Media
    image = models.URLField(blank=True, help_text="Main banner image URL")
    mobile_image = models.URLField(blank=True, help_text="Optional mobile-specific image")
    image_asset = models.ForeignKey(
        ImageAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_promotional_banners'
    )
    mobile_image_asset = models.ForeignKey(
        ImageAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mobile_promotional_banners'
    )

    # Link Configuration
    link_type = models.CharField(max_length=20, choices=LINK_TYPE_CHOICES, default='NONE')
    link_url = models.URLField(blank=True, help_text="For external URLs")
    link_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotional_banners'
    )
    link_merchant = models.ForeignKey(
        Merchant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promotional_banners'
    )

    # CTA
    cta_text = models.CharField(max_length=50, blank=True, help_text="Call to action text")

    # Scheduling
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    # Status & Control
    is_verified = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    # Display Order
    sort_order = models.IntegerField(default=0, help_text="Lower numbers appear first")

    # Metrics
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'promotional_banners'
        ordering = ['sort_order', '-created_at']
        indexes = [
            models.Index(fields=['placement', 'is_active', 'is_verified']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['display_type']),
            models.Index(fields=['platform']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_display_type_display()})"

    def clean(self):
        # Validate link configuration
        if self.link_type == 'URL' and not self.link_url:
            raise ValidationError("Link URL is required when link type is URL")

        if self.link_type == 'CATEGORY' and not self.link_category:
            raise ValidationError("Category is required when link type is Category")

        if self.link_type == 'MERCHANT' and not self.link_merchant:
            raise ValidationError("Merchant is required when link type is Merchant")

        # Validate dates
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date")

    def is_currently_active(self):
        """Check if banner is currently active based on dates and status"""
        if not self.start_date or not self.end_date:
            return False
        now = timezone.now()
        return (
                self.is_active and
                self.is_verified and
                self.start_date <= now <= self.end_date
        )

    def get_click_through_rate(self):
        """Calculate CTR percentage"""
        if self.impressions == 0:
            return 0
        return (self.clicks / self.impressions) * 100

    def get_target_payload(self):
        """Return a normalized navigation target for app clients."""
        payload = {'type': self.link_type}
        if self.link_type == 'URL':
            payload['url'] = self.link_url
        elif self.link_type == 'CATEGORY' and self.link_category_id:
            payload['category_id'] = str(self.link_category_id)
        elif self.link_type == 'MERCHANT' and self.link_merchant_id:
            payload['merchant_id'] = str(self.link_merchant_id)
        elif self.link_type in ['LISTING', 'LISTINGS']:
            listing_ids = list(
                self.featured_listings.order_by('sort_order').values_list('listing_id', flat=True)
            )
            payload['listing_ids'] = [str(listing_id) for listing_id in listing_ids]
            if self.link_type == 'LISTING' and listing_ids:
                payload['listing_id'] = str(listing_ids[0])
        return payload


class BannerImageImport(models.Model):
    """
    Queue item for AI/designer-generated banner files dropped into the import folder.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('UPLOADED', 'Uploaded'),
        ('FAILED', 'Failed'),
    ]

    TARGET_CHOICES = [
        ('image', 'Primary Image'),
        ('mobile_image', 'Mobile Image'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    banner = models.ForeignKey(
        PromotionalBanner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='image_imports'
    )
    source_path = models.CharField(max_length=500, unique=True)
    sidecar_path = models.CharField(max_length=500, blank=True)
    target_field = models.CharField(max_length=20, choices=TARGET_CHOICES, default='image')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    image_asset = models.ForeignKey(
        ImageAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='banner_imports'
    )
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'banner_image_imports'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['banner', 'target_field']),
        ]

    def __str__(self):
        return f"{self.source_path} [{self.status}]"


class BannerListing(models.Model):
    """
    Links promotional banners to specific listings (for grouped product showcases)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    banner = models.ForeignKey(
        PromotionalBanner,
        on_delete=models.CASCADE,
        related_name='featured_listings'
    )
    listing = models.ForeignKey(
        'listings.Listing',  # Adjust to your actual Listing model
        on_delete=models.CASCADE,
        related_name='promotional_banners'
    )
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'banner_listings'
        unique_together = ('banner', 'listing')
        ordering = ['sort_order']
        indexes = [
            models.Index(fields=['banner', 'sort_order']),
        ]

    def __str__(self):
        return f"{self.banner.title} → {self.listing.title}"
