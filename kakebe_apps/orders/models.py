import uuid

from django.core.validators import MinValueValidator
from django.db import models

from KakebeShop import settings
from kakebe_apps.listings.models import Listing
from kakebe_apps.location.models import UserAddress
from kakebe_apps.merchants.models import Merchant


# Create your models here.
class OrderIntent(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('CONTACTED', 'Contacted'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    CANCELLED_BY_CHOICES = [
        ('BUYER', 'Buyer'),
        ('MERCHANT', 'Merchant'),
        ('ADMIN', 'Admin'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name='orders')
    address = models.ForeignKey(UserAddress, on_delete=models.PROTECT)
    notes = models.TextField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW', db_index=True)
    cancelled_by = models.CharField(max_length=20, choices=CANCELLED_BY_CHOICES, null=True, blank=True)
    cancellation_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'order_intents'
        indexes = [
            models.Index(fields=['buyer']),
            models.Index(fields=['merchant']),
            models.Index(fields=['status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"


class OrderIntentItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_intent = models.ForeignKey(OrderIntent, on_delete=models.CASCADE, related_name='items')
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_intent_items'
        indexes = [
            models.Index(fields=['order_intent']),
            models.Index(fields=['listing']),
        ]

    def __str__(self):
        return f"{self.listing.title} x {self.quantity}"