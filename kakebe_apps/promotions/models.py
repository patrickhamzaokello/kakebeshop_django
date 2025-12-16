import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from kakebe_apps.categories.models import Category


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
    image = models.URLField(help_text="Main banner image URL")
    mobile_image = models.URLField(blank=True, help_text="Optional mobile-specific image")

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

        # Validate dates
        if self.end_date <= self.start_date:
            raise ValidationError("End date must be after start date")

    def is_currently_active(self):
        """Check if banner is currently active based on dates and status"""
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