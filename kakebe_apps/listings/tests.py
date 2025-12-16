# kakebe_apps/listings/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.categories.models import Category
from .models import Listing, ListingImage

User = get_user_model()


class ListingModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            display_name='Test Merchant',
            description='A test merchant',
            verified=True
        )
        self.category = Category.objects.create(name='Test Category')

    def test_listing_creation(self):
        listing = Listing.objects.create(
            merchant=self.merchant,
            title='Test Product',
            description='A test product',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=100.00
        )
        self.assertEqual(str(listing), 'Test Product')
        self.assertFalse(listing.is_active)  # Not verified by default

    def test_verified_listing_is_active(self):
        listing = Listing.objects.create(
            merchant=self.merchant,
            title='Test Product',
            description='A test product',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=100.00,
            status='ACTIVE',
            is_verified=True
        )
        self.assertTrue(listing.is_active)

    def test_soft_delete(self):
        listing = Listing.objects.create(
            merchant=self.merchant,
            title='Test Product',
            description='A test product',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=100.00
        )
        listing.soft_delete()
        self.assertIsNotNone(listing.deleted_at)
        self.assertEqual(listing.status, 'DEACTIVATED')


class ListingAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Create users and merchants
        self.user1 = User.objects.create_user(
            username='merchant1',
            email='merchant1@example.com',
            password='pass123'
        )
        self.merchant1 = Merchant.objects.create(
            user=self.user1,
            display_name='Merchant One',
            description='First merchant',
            verified=True
        )

        self.user2 = User.objects.create_user(
            username='merchant2',
            email='merchant2@example.com',
            password='pass123'
        )
        self.merchant2 = Merchant.objects.create(
            user=self.user2,
            display_name='Merchant Two',
            description='Second merchant',
            verified=True
        )

        # Create category
        self.category = Category.objects.create(name='Electronics')

        # Create verified listing
        self.listing1 = Listing.objects.create(
            merchant=self.merchant1,
            title='Laptop',
            description='A great laptop',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=1000.00,
            status='ACTIVE',
            is_verified=True,
            is_featured=True
        )

        # Create unverified listing
        self.listing2 = Listing.objects.create(
            merchant=self.merchant1,
            title='Phone',
            description='A smartphone',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=500.00,
            status='PENDING',
            is_verified=False
        )

    def test_list_only_verified_listings(self):
        """Only verified listings should appear in public list"""
        response = self.client.get('/listings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Laptop')

    def test_retrieve_unverified_listing_fails(self):
        """Retrieving an unverified listing should fail"""
        response = self.client.get(f'/listings/{self.listing2.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_verified_listing_succeeds(self):
        """Retrieving a verified listing should work"""
        response = self.client.get(f'/listings/{self.listing1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Laptop')

    def test_featured_listings_endpoint(self):
        """Featured listings endpoint should return only featured listings"""
        response = self.client.get('/listings/featured/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Laptop')
        self.assertTrue(response.data[0]['is_featured'])

    def test_my_listings_requires_authentication(self):
        """My listings endpoint requires authentication"""
        response = self.client.get('/listings/my_listings/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_listings_shows_all_statuses(self):
        """Merchant can see their own listings regardless of status"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/listings/my_listings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_create_listing_requires_merchant_profile(self):
        """Creating a listing requires a merchant profile"""
        user3 = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='pass123'
        )
        self.client.force_authenticate(user=user3)

        data = {
            'title': 'New Product',
            'description': 'Description',
            'listing_type': 'PRODUCT',
            'category': self.category.id,
            'price_type': 'FIXED',
            'price': 100.00
        }
        response = self.client.post('/listings/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_listing_starts_as_pending(self):
        """New listings should start with PENDING status"""
        self.client.force_authenticate(user=self.user1)

        data = {
            'title': 'New Product',
            'description': 'Description',
            'listing_type': 'PRODUCT',
            'category': self.category.id,
            'price_type': 'FIXED',
            'price': 100.00
        }
        response = self.client.post('/listings/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'PENDING')
        self.assertFalse(response.data['is_verified'])

    def test_update_own_listing(self):
        """Merchant can update their own listing"""
        self.client.force_authenticate(user=self.user1)

        data = {'title': 'Updated Laptop'}
        response = self.client.patch(f'/listings/{self.listing1.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Laptop')

    def test_cannot_update_other_merchant_listing(self):
        """Merchant cannot update another merchant's listing"""
        self.client.force_authenticate(user=self.user2)

        data = {'title': 'Hacked Laptop'}
        response = self.client.patch(f'/listings/{self.listing1.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_category(self):
        """Listings can be filtered by category"""
        response = self.client.get(f'/listings/?category={self.category.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_listings(self):
        """Listings can be searched"""
        response = self.client.get('/listings/?search=Laptop')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Laptop')

    def test_increment_views(self):
        """View count can be incremented"""
        initial_views = self.listing1.views_count
        response = self.client.post(f'/listings/{self.listing1.id}/increment_views/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['views_count'], initial_views + 1)

    def test_increment_contacts(self):
        """Contact count can be incremented"""
        initial_contacts = self.listing1.contact_count
        response = self.client.post(f'/listings/{self.listing1.id}/increment_contacts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['contact_count'], initial_contacts + 1)