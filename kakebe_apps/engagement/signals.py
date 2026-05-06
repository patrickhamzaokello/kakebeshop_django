from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import MerchantReview
from .services import MerchantReputationService


@receiver(post_save, sender=MerchantReview)
def sync_merchant_reputation_after_review_save(sender, instance, **kwargs):
    transaction.on_commit(
        lambda: MerchantReputationService.sync_merchant(instance.merchant)
    )


@receiver(post_delete, sender=MerchantReview)
def sync_merchant_reputation_after_review_delete(sender, instance, **kwargs):
    transaction.on_commit(
        lambda: MerchantReputationService.sync_merchant(instance.merchant)
    )
