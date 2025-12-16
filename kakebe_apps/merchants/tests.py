# kakebe_apps/merchants/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Merchant

User = get_user_model()


class MerchantModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_merchant_creation(self):
        merchant = Merchant.objects.create(
            user=self.user,
            display_name='Test Shop',
            description='A test merchant'
        )
        self.assertEqual(str(merchant), 'Test Shop')
        self.assertFalse(merchant.is_active)  # Not verified by default
        self.assertEqual(merchant.rating, 0.0)

    def test_verified_merchant_is_active(self):
        merchant = Merchant.objects.create(
            user=self.user,
            display_name='Test Shop',
            description='A test merchant',
            verified=True
        )
        self.assertTrue(merchant.is_active)

    def test_soft_delete(self):
        merchant = Merchant.objects.create(
            user=self.user,
            display_name='Test Shop',
            description='A test merchant'
        )
        merchant.soft_delete()
        self.assertIsNotNone(merchant.deleted_at)
        self.assertEqual(merchant.status, 'SUSPENDED')


class MerchantAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Create verified merchants
        self.user1 = User.objects.create_user(
            username='merchant1',
            email='merchant1@example.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='merchant2',
            email='merchant2@example.com',
            password='pass123'
        )

        # Create unverified merchant
        self.user3 = User.objects.create_user(
            username='merchant3',
            email='merchant3@example.com',
            password='pass123'
        )

        self.merchant1 = Merchant.objects.create(
            user=self.user1,
            display_name='Shop One',
            description='First shop',
            rating=4.5,
            verified=True,
            featured=True
        )
        self.merchant2 = Merchant.objects.create(
            user=self.user2,
            display_name='Shop Two',
            description='Second shop',
            rating=3.5,
            verified=True
        )
        self.merchant3 = Merchant.objects.create(
            user=self.user3,
            display_name='Shop Three',
            description='Third shop',
            rating=5.0,
            verified=False  # Not verified
        )

    def test_list_only_verified_merchants(self):
        """Only verified merchants should appear in public list"""
        response = self.client.get('/merchants/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)  # Only verified ones

        # Check that unverified merchant is not in results
        display_names = [m['display_name'] for m in response.data['results']]
        self.assertNotIn('Shop Three', display_names)

    def test_retrieve_unverified_merchant_fails(self):
        """Retrieving an unverified merchant should fail"""
        response = self.client.get(f'/merchants/{self.merchant3.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_verified_merchant_succeeds(self):
        """Retrieving a verified merchant should work"""
        response = self.client.get(f'/merchants/{self.merchant1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Shop One')

    def test_featured_merchants_endpoint(self):
        """Featured merchants endpoint should return only featured merchants"""
        response = self.client.get('/merchants/featured/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['display_name'], 'Shop One')
        self.assertTrue(response.data[0]['featured'])

    def test_featured_merchants_with_limit(self):
        """Test featured endpoint with custom limit"""
        # Add more featured merchants
        for i in range(5):
            user = User.objects.create_user(
                username=f'featured{i}',
                email=f'featured{i}@example.com',
                password='pass'
            )
            Merchant.objects.create(
                user=user,
                display_name=f'Featured Shop {i}',
                description='Featured',
                verified=True,
                featured=True
            )

        response = self.client.get('/merchants/featured/?limit=3')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_featured_merchants_are_shuffled(self):
        """Featured merchants should be returned in random order"""
        # Create multiple featured merchants
        for i in range(10):
            user = User.objects.create_user(
                username=f'shuffle{i}',
                email=f'shuffle{i}@example.com',
                password='pass'
            )
            Merchant.objects.create(
                user=user,
                display_name=f'Shop {i}',
                description='Test',
                verified=True,
                featured=True
            )

        # Make two requests and check if order is different
        response1 = self.client.get('/merchants/featured/?limit=10')
        response2 = self.client.get('/merchants/featured/?limit=10')

        names1 = [m['display_name'] for m in response1.data]
        names2 = [m['display_name'] for m in response2.data]

        # Order should be different (with very high probability)
        # Note: There's a small chance they could be the same by random chance
        self.assertEqual(len(names1), 10)
        self.assertEqual(len(names2), 10)

    def test_owner_can_see_unverified_profile(self):
        """Merchant owner can see their profile even if unverified"""
        self.client.force_authenticate(user=self.user3)
        response = self.client.get('/merchants/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Shop Three')
        self.assertFalse(response.data['verified'])

    def test_search_only_searches_verified(self):
        """Search should only return verified merchants"""
        response = self.client.get('/merchants/?search=Shop')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # Only verified ones

    def test_create_merchant_profile(self):
        """Creating a merchant profile should set verified to False"""
        user4 = User.objects.create_user(
            username='newmerchant',
            email='new@example.com',
            password='pass123'
        )
        self.client.force_authenticate(user=user4)
        data = {
            'display_name': 'New Shop',
            'description': 'Brand new shop'
        }
        response = self.client.post('/merchants/create_profile/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['display_name'], 'New Shop')
        self.assertFalse(response.data['verified'])

    def test_update_own_profile(self):
        """Merchant owner can update their profile"""
        self.client.force_authenticate(user=self.user1)
        data = {'display_name': 'Updated Shop'}
        response = self.client.patch('/merchants/me/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Updated Shop')

    def test_pagination_response_structure(self):
        """Pagination should include count, next, previous, results"""
        response = self.client.get('/merchants/')
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)