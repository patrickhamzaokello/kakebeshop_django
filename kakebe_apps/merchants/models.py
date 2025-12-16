import uuid

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Merchant(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('BANNED', 'Banned'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='merchant_profile'
    )
    display_name = models.CharField(max_length=255, db_index=True)
    business_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    business_phone = models.CharField(max_length=20, null=True, blank=True)
    business_email = models.EmailField(null=True, blank=True, unique=True)
    logo = models.URLField(null=True, blank=True)
    cover_image = models.URLField(null=True, blank=True)

    # Verification fields
    verified = models.BooleanField(default=False, db_index=True)
    verification_date = models.DateTimeField(null=True, blank=True)

    # Featured field for homepage
    featured = models.BooleanField(default=False, db_index=True)
    featured_order = models.PositiveIntegerField(default=0, db_index=True)

    # Rating with validation
    rating = models.FloatField(
        default=0.0,
        db_index=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    total_reviews = models.PositiveIntegerField(default=0)

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        db_index=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'merchants'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['verified', 'status']),
            models.Index(fields=['-rating', 'display_name']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['featured', 'verified', 'status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.display_name

    @property
    def is_active(self):
        """Check if merchant is active, verified, and not deleted"""
        return (
                self.status == 'ACTIVE'
                and self.verified
                and self.deleted_at is None
        )

    def soft_delete(self):
        """Soft delete the merchant"""
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.status = 'SUSPENDED'
        self.save(update_fields=['deleted_at', 'status'])