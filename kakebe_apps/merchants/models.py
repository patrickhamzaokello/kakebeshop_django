import uuid

from django.db import models
from django.conf import settings

# Create your models here.
class Merchant(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('BANNED', 'Banned'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='merchant_profile')
    display_name = models.CharField(max_length=255)
    business_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField()
    business_phone = models.CharField(max_length=20, null=True, blank=True)
    business_email = models.EmailField(null=True, blank=True)
    logo = models.URLField(null=True, blank=True)
    cover_image = models.URLField(null=True, blank=True)
    verified = models.BooleanField(default=False, db_index=True)
    verification_date = models.DateTimeField(null=True, blank=True)
    rating = models.FloatField(default=0.0, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'merchants'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['verified']),
            models.Index(fields=['status']),
            models.Index(fields=['rating']),
        ]

    def __str__(self):
        return self.display_name