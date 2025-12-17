import uuid

from django.core.validators import MinValueValidator
from django.db import models

from KakebeShop import settings
from kakebe_apps.listings.models import Listing


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

    @property
    def total_items(self):
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0

    @property
    def total_price(self):
        total = sum(item.listing.price * item.quantity for item in self.items.all())
        return total


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

    @property
    def subtotal(self):
        return self.listing.price * self.quantity


class Wishlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wishlists'
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Wishlist - {self.user.name}"

    @property
    def total_items(self):
        return self.items.count()


class WishlistItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wishlist_items'
        unique_together = ('wishlist', 'listing')
        indexes = [
            models.Index(fields=['wishlist']),
            models.Index(fields=['listing']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.listing.title}"