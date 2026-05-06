from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TransactionTestCase

from kakebe_apps.location.models import UserAddress
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.orders.models import OrderIntent

from .models import MerchantReview, MerchantScore
from .serializers import MerchantReviewSerializer

User = get_user_model()


class MerchantReviewReputationTestCase(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='pass123',
        )
        self.merchant_user = User.objects.create_user(
            username='merchant',
            email='merchant@example.com',
            password='pass123',
        )
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            display_name='Reviewed Shop',
            description='A merchant with reviews',
            verified=True,
        )
        self.address = UserAddress.objects.create(
            user=self.buyer,
            label='HOME',
            region='Central',
            district='Kampala',
            area='Ntinda',
            landmark='Near the stage',
        )
        self.order = OrderIntent.objects.create(
            order_number=OrderIntent.generate_order_number(),
            buyer=self.buyer,
            merchant=self.merchant,
            address=self.address,
            total_amount=Decimal('25000.00'),
            status='COMPLETED',
        )

    def test_review_create_update_delete_syncs_merchant_rating_and_score(self):
        review = MerchantReview.objects.create(
            merchant=self.merchant,
            user=self.buyer,
            order_intent=self.order,
            rating=5,
            comment='Excellent merchant.',
        )

        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.rating, 5.0)
        self.assertEqual(self.merchant.total_reviews, 1)
        self.assertTrue(MerchantScore.objects.filter(merchant=self.merchant).exists())

        review.rating = 3
        review.save()
        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.rating, 3.0)
        self.assertEqual(self.merchant.total_reviews, 1)

        review.delete()
        self.merchant.refresh_from_db()
        self.assertEqual(self.merchant.rating, 0.0)
        self.assertEqual(self.merchant.total_reviews, 0)

    def test_review_serializer_requires_completed_order(self):
        request = RequestFactory().post('/api/v1/merchant-reviews/')
        request.user = self.buyer
        serializer = MerchantReviewSerializer(
            data={
                'merchant': str(self.merchant.id),
                'order_intent': str(self.order.id),
                'rating': 4,
                'comment': 'Good merchant.',
            },
            context={'request': request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
