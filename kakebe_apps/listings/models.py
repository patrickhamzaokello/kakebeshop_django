import uuid

from django.db import models

from kakebe_apps.categories.models import Category, Tag
from kakebe_apps.location.models import Location
from kakebe_apps.merchants.models import Merchant


# Create your models here.
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
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
        ('DEACTIVATED', 'Deactivated'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=255)
    description = models.TextField()
    listing_type = models.CharField(max_length=20, choices=LISTING_TYPE_CHOICES)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='listings')
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='listings')
    tags = models.ManyToManyField(Tag, through='ListingTag', related_name='listings')

    price_type = models.CharField(max_length=20, choices=PRICE_TYPE_CHOICES)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='UGX')
    is_price_negotiable = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', db_index=True)
    rejection_reason = models.TextField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False, db_index=True)
    featured_until = models.DateTimeField(null=True, blank=True)

    views_count = models.IntegerField(default=0)
    contact_count = models.IntegerField(default=0)
    metadata = models.JSONField(null=True, blank=True)

    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'listings'
        indexes = [
            models.Index(fields=['merchant']),
            models.Index(fields=['category']),
            models.Index(fields=['location']),
            models.Index(fields=['status']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.title


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


class ListingImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='images')
    image = models.URLField()
    thumbnail = models.URLField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'listing_images'
        indexes = [
            models.Index(fields=['listing']),
            models.Index(fields=['is_primary']),
        ]
        ordering = ['sort_order']

    def __str__(self):
        return f"Image for {self.listing.title}"


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
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='business_hours')
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    opens_at = models.TimeField()
    closes_at = models.TimeField()
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'listing_business_hours'
        indexes = [
            models.Index(fields=['listing']),
            models.Index(fields=['day']),
        ]

    def __str__(self):
        return f"{self.listing.title} - {self.day}"