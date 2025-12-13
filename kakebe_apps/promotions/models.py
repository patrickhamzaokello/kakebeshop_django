import uuid
from django.db import models

from kakebe_apps.listings.models import Listing



class PromotionalCampaign(models.Model):
    CAMPAIGN_TYPE_CHOICES = [
        ('FEATURED_LISTING', 'Featured Listing'),
        ('BANNER', 'Banner'),
        ('PUSH_NOTIFICATION', 'Push Notification'),
        ('EMAIL', 'Email'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    campaign_type = models.CharField(max_length=30, choices=CAMPAIGN_TYPE_CHOICES)
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(db_index=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'promotional_campaigns'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
        ]

    def __str__(self):
        return self.name


class CampaignListing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(PromotionalCampaign, on_delete=models.CASCADE, related_name='listings')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='campaigns')
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'campaign_listings'
        unique_together = ('campaign', 'listing')
        indexes = [
            models.Index(fields=['campaign']),
            models.Index(fields=['listing']),
        ]

    def __str__(self):
        return f"{self.campaign.name} - {self.listing.title}"


import uuid
from django.db import models


class CampaignCreative(models.Model):
    CREATIVE_TYPE_CHOICES = [
        ('SLIDER', 'Slider'),
        ('BANNER', 'Banner'),
        ('POPUP', 'Popup'),
    ]

    PLATFORM_CHOICES = [
        ('ANDROID', 'Android'),
        ('IOS', 'iOS'),
        ('WEB', 'Web'),
        ('ALL', 'All Platforms'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    campaign = models.ForeignKey(
        PromotionalCampaign,
        on_delete=models.CASCADE,
        related_name='creatives'
    )

    creative_type = models.CharField(
        max_length=20,
        choices=CREATIVE_TYPE_CHOICES,
        db_index=True
    )

    title = models.CharField(max_length=255, blank=True)
    subtitle = models.CharField(max_length=255, blank=True)

    image = models.URLField()
    thumbnail = models.URLField(null=True, blank=True)

    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        default='ALL',
        db_index=True
    )

    cta_text = models.CharField(max_length=50, blank=True)

    sort_order = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'campaign_creatives'
        ordering = ['sort_order']
        indexes = [
            models.Index(fields=['creative_type']),
            models.Index(fields=['platform']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.campaign.name} - {self.creative_type}"


class CampaignPlacement(models.Model):
    PLACEMENT_CHOICES = [
        ('HOME_TOP', 'Home Top Slider'),
        ('HOME_MIDDLE', 'Home Middle Banner'),
        ('HOME_BOTTOM', 'Home Bottom Banner'),
        ('CATEGORY', 'Category Page'),
        ('LISTING', 'Listing Page'),
        ('SEARCH', 'Search Results'),
    ]

    TARGET_TYPE_CHOICES = [
        ('LISTING', 'Listing'),
        ('CATEGORY', 'Category'),
        ('MERCHANT', 'Merchant'),
        ('URL', 'External URL'),
        ('NONE', 'No Action'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    creative = models.ForeignKey(
        CampaignCreative,
        on_delete=models.CASCADE,
        related_name='placements'
    )

    placement = models.CharField(
        max_length=30,
        choices=PLACEMENT_CHOICES,
        db_index=True
    )

    target_type = models.CharField(
        max_length=20,
        choices=TARGET_TYPE_CHOICES,
        default='NONE'
    )

    target_id = models.UUIDField(null=True, blank=True)
    target_url = models.URLField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'campaign_placements'
        indexes = [
            models.Index(fields=['placement']),
            models.Index(fields=['target_type']),
        ]

    def __str__(self):
        return f"{self.creative} → {self.placement}"
