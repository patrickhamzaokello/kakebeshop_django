from django.db.models import Avg, Count, Q
from django.utils import timezone

from kakebe_apps.listings.models import Listing
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.orders.models import OrderIntent

from .models import MerchantReview, MerchantScore, Report


class MerchantReputationService:
    """Keeps merchant reviews, cached ratings, and score records in sync."""

    @staticmethod
    def recalculate_rating(merchant):
        aggregates = MerchantReview.objects.filter(merchant=merchant).aggregate(
            average_rating=Avg('rating'),
            total_reviews=Count('id'),
        )
        merchant.rating = round(float(aggregates['average_rating'] or 0.0), 2)
        merchant.total_reviews = aggregates['total_reviews'] or 0
        merchant.save(update_fields=['rating', 'total_reviews', 'updated_at'])
        return merchant

    @staticmethod
    def recalculate_score(merchant):
        listing_counts = Listing.objects.filter(
            merchant=merchant,
            deleted_at__isnull=True,
        ).aggregate(
            active_listing_count=Count('id', filter=Q(status='ACTIVE', is_verified=True)),
            total_listing_count=Count('id'),
        )
        order_counts = OrderIntent.objects.filter(merchant=merchant).aggregate(
            completed_orders=Count('id', filter=Q(status='COMPLETED')),
            cancelled_orders=Count('id', filter=Q(status='CANCELLED')),
        )
        report_count = Report.objects.filter(
            merchant=merchant,
        ).exclude(status='DISMISSED').count()

        completed_orders = order_counts['completed_orders'] or 0
        cancelled_orders = order_counts['cancelled_orders'] or 0
        total_resolved_orders = completed_orders + cancelled_orders
        completion_rate = completed_orders / total_resolved_orders if total_resolved_orders else 0.0

        active_listing_count = listing_counts['active_listing_count'] or 0
        total_listing_count = listing_counts['total_listing_count'] or 0
        listing_health = active_listing_count / total_listing_count if total_listing_count else 0.0

        rating_component = float(merchant.rating or 0.0)
        completion_component = completion_rate * 5
        listing_component = listing_health * 5
        report_penalty = min(report_count * 0.25, 2.0)

        score = (
            (rating_component * 0.55)
            + (completion_component * 0.30)
            + (listing_component * 0.15)
            - report_penalty
        )
        score = max(0.0, min(5.0, round(score, 2)))

        merchant_score, _ = MerchantScore.objects.update_or_create(
            merchant=merchant,
            defaults={
                'active_listing_count': active_listing_count,
                'total_listing_count': total_listing_count,
                'response_rate': round(completion_rate * 100, 2),
                'average_response_time_minutes': 0,
                'completed_orders': completed_orders,
                'cancelled_orders': cancelled_orders,
                'report_count': report_count,
                'score': score,
                'last_calculated': timezone.now(),
            },
        )
        return merchant_score

    @classmethod
    def sync_merchant(cls, merchant):
        merchant = cls.recalculate_rating(merchant)
        return cls.recalculate_score(merchant)
