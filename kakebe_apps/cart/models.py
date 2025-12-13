import uuid

from django.core.validators import MinValueValidator
from django.db import models

from KakebeShop import settings
from kakebe_apps.listings.models import Listing


# Create your models here.
class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Cart - {self.user.name}"


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_items'
        unique_together = ('cart', 'listing')
        indexes = [
            models.Index(fields=['cart']),
            models.Index(fields=['listing']),
        ]

    def __str__(self):
        return f"{self.listing.title} x {self.quantity}"