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
        self.assertTrue(merchant.is_active)
        self.assertEqual(merchant.rating, 0.0)

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

        self.merchant1 = Merchant.objects.create(
            user=self.user1,
            display_name='Shop One',
            description='First shop',
            rating=4.5
        )
        self.merchant2 = Merchant.objects.create(
            user=self.user2,
            display_name='Shop Two',
            description='Second shop',
            rating=3.5,
            verified=True
        )

    def test_list_merchants(self):
        response = self.client.get('/merchants/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_merchants_pagination(self):
        # Create more merchants
        for i in range(25):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='pass'
            )
            Merchant.objects.create(
                user=user,
                display_name=f'Shop {i}',
                description='Test shop'
            )

        response = self.client.get('/merchants/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 20)  # default page size
        self.assertIsNotNone(response.data['next'])

    def test_search_merchants(self):
        response = self.client.get('/merchants/?search=Shop One')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['display_name'], 'Shop One')

    def test_filter_verified(self):
        response = self.client.get('/merchants/?verified=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertTrue(response.data['results'][0]['verified'])

    def test_retrieve_merchant(self):
        response = self.client.get(f'/merchants/{self.merchant1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Shop One')

    def test_get_own_profile_authenticated(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/merchants/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Shop One')

    def test_get_own_profile_unauthenticated(self):
        response = self.client.get('/merchants/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_own_profile(self):
        self.client.force_authenticate(user=self.user1)
        data = {'display_name': 'Updated Shop'}
        response = self.client.patch('/merchants/me/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Updated Shop')

    def test_create_merchant_profile(self):
        user3 = User.objects.create_user(
            username='newmerchant',
            email='new@example.com',
            password='pass123'
        )
        self.client.force_authenticate(user=user3)
        data = {
            'display_name': 'New Shop',
            'description': 'Brand new shop'
        }
        response = self.client.post('/merchants/create_profile/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['display_name'], 'New Shop')

    def test_cannot_create_duplicate_profile(self):
        self.client.force_authenticate(user=self.user1)
        data = {
            'display_name': 'Another Shop',
            'description': 'Should fail'
        }
        response = self.client.post('/merchants/create_profile/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)