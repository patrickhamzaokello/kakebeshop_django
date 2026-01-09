# kakebe_apps/listings/tests.py

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import uuid

from .models import Listing, ListingBusinessHour, ListingTag
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.categories.models import Category, Tag

User = get_user_model()


class ListingModelTestCase(TestCase):
    """Test cases for Listing model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            display_name='Test Merchant',
            verified=True
        )
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )

    def test_listing_creation(self):
        """Test creating a listing"""
        listing = Listing.objects.create(
            merchant=self.merchant,
            title='Test Product',
            description='Test description',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=Decimal('100.00'),
            currency='UGX',
            status='DRAFT'
        )

        self.assertEqual(listing.title, 'Test Product')
        self.assertEqual(listing.merchant, self.merchant)
        self.assertEqual(listing.status, 'DRAFT')
        self.assertIsNotNone(listing.id)

    def test_is_active_property(self):
        """Test is_active property"""
        listing = Listing.objects.create(
            merchant=self.merchant,
            title='Test Product',
            description='Test description',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=Decimal('100.00'),
            status='ACTIVE',
            is_verified=True
        )

        self.assertTrue(listing.is_active)

        # Change status
        listing.status = 'DRAFT'
        listing.save()
        self.assertFalse(listing.is_active)

    def test_soft_delete(self):
        """Test soft delete functionality"""
        listing = Listing.objects.create(
            merchant=self.merchant,
            title='Test Product',
            description='Test description',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=Decimal('100.00')
        )

        listing.soft_delete()
        listing.refresh_from_db()

        self.assertIsNotNone(listing.deleted_at)
        self.assertEqual(listing.status, 'DEACTIVATED')

    def test_increment_views(self):
        """Test view count increment"""
        listing = Listing.objects.create(
            merchant=self.merchant,
            title='Test Product',
            description='Test description',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=Decimal('100.00')
        )

        initial_views = listing.views_count
        listing.increment_views()
        listing.refresh_from_db()

        self.assertEqual(listing.views_count, initial_views + 1)

    def test_increment_contacts(self):
        """Test contact count increment"""
        listing = Listing.objects.create(
            merchant=self.merchant,
            title='Test Product',
            description='Test description',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=Decimal('100.00')
        )

        initial_contacts = listing.contact_count
        listing.increment_contacts()
        listing.refresh_from_db()

        self.assertEqual(listing.contact_count, initial_contacts + 1)


class ListingAPITestCase(APITestCase):
    """Test suite for Listing API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        # Create test user and merchant
        self.user = User.objects.create_user(
            username='testmerchant',
            email='test@example.com',
            password='testpass123'
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            display_name='Test Merchant',
            verified=True
        )

        # Create second user for permission tests
        self.other_user = User.objects.create_user(
            username='othermerchant',
            email='other@example.com',
            password='testpass123'
        )
        self.other_merchant = Merchant.objects.create(
            user=self.other_user,
            display_name='Other Merchant',
            verified=True
        )

        # Create category
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )

        # Create tags
        self.tag1 = Tag.objects.create(name='Smartphone', slug='smartphone')
        self.tag2 = Tag.objects.create(name='Android', slug='android')

        # Create test listing
        self.listing = Listing.objects.create(
            merchant=self.merchant,
            title='Test Product',
            description='Test description',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=Decimal('100.00'),
            currency='UGX',
            status='ACTIVE',
            is_verified=True
        )
        self.listing.tags.add(self.tag1)

    def test_list_listings_public(self):
        """Test public listing list endpoint"""
        url = reverse('listing-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Test Product')

    def test_list_listings_with_search(self):
        """Test listing search functionality"""
        url = reverse('listing-list')
        response = self.client.get(url, {'search': 'Test'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_listings_with_filters(self):
        """Test listing filtering"""
        # Create another listing with different category
        other_category = Category.objects.create(
            name='Fashion',
            slug='fashion'
        )
        Listing.objects.create(
            merchant=self.merchant,
            title='Fashion Item',
            description='Fashion description',
            listing_type='PRODUCT',
            category=other_category,
            price_type='FIXED',
            price=Decimal('50.00'),
            status='ACTIVE',
            is_verified=True
        )

        # Filter by category
        url = reverse('listing-list')
        response = self.client.get(url, {'category': str(self.category.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Test Product')

    def test_retrieve_listing(self):
        """Test retrieving single listing"""
        url = reverse('listing-detail', kwargs={'pk': self.listing.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Product')
        self.assertEqual(response.data['merchant']['display_name'], 'Test Merchant')

    def test_featured_listings(self):
        """Test featured listings endpoint"""
        self.listing.is_featured = True
        self.listing.save()

        url = reverse('listing-featured')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Test Product')

    def test_create_listing_authenticated(self):
        """Test creating listing with authentication"""
        self.client.force_authenticate(user=self.user)

        url = reverse('listing-list')
        data = {
            'title': 'New Product',
            'description': 'New description',
            'listing_type': 'PRODUCT',
            'category': str(self.category.id),
            'price_type': 'FIXED',
            'price': '150.00',
            'currency': 'UGX'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Listing.objects.count(), 2)
        self.assertEqual(response.data['title'], 'New Product')
        self.assertEqual(response.data['status'], 'PENDING')

    def test_create_listing_without_auth(self):
        """Test creating listing without authentication"""
        url = reverse('listing-list')
        data = {'title': 'Should Fail'}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_listing_without_merchant_profile(self):
        """Test creating listing without merchant profile"""
        user_no_merchant = User.objects.create_user(
            username='nomerchant',
            password='testpass123'
        )
        self.client.force_authenticate(user=user_no_merchant)

        url = reverse('listing-list')
        data = {'title': 'Should Fail'}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_listing_with_tags(self):
        """Test creating listing with tags"""
        self.client.force_authenticate(user=self.user)

        url = reverse('listing-list')
        data = {
            'title': 'Tagged Product',
            'description': 'Product with tags',
            'listing_type': 'PRODUCT',
            'category': str(self.category.id),
            'price_type': 'FIXED',
            'price': '200.00',
            'tag_ids': [self.tag1.id, self.tag2.id]
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        listing = Listing.objects.get(id=response.data['id'])
        self.assertEqual(listing.tags.count(), 2)

    def test_update_own_listing(self):
        """Test updating own listing"""
        self.client.force_authenticate(user=self.user)

        url = reverse('listing-detail', kwargs={'pk': self.listing.id})
        data = {'title': 'Updated Title'}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, 'Updated Title')

    def test_cannot_update_others_listing(self):
        """Test that user cannot update another merchant's listing"""
        self.client.force_authenticate(user=self.other_user)

        url = reverse('listing-detail', kwargs={'pk': self.listing.id})
        data = {'title': 'Hacked Title'}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_listing(self):
        """Test soft deleting own listing"""
        self.client.force_authenticate(user=self.user)

        url = reverse('listing-detail', kwargs={'pk': self.listing.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.listing.refresh_from_db()
        self.assertIsNotNone(self.listing.deleted_at)
        self.assertEqual(self.listing.status, 'DEACTIVATED')

    def test_my_listings(self):
        """Test retrieving merchant's own listings"""
        self.client.force_authenticate(user=self.user)

        # Create another listing for this merchant
        Listing.objects.create(
            merchant=self.merchant,
            title='Another Product',
            description='Another description',
            listing_type='SERVICE',
            category=self.category,
            price_type='ON_REQUEST',
            status='DRAFT'
        )

        url = reverse('listing-my-listings')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_my_listings_with_status_filter(self):
        """Test filtering own listings by status"""
        self.client.force_authenticate(user=self.user)

        Listing.objects.create(
            merchant=self.merchant,
            title='Draft Product',
            description='Draft description',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=Decimal('75.00'),
            status='DRAFT'
        )

        url = reverse('listing-my-listings')
        response = self.client.get(url, {'status': 'ACTIVE'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['status'], 'ACTIVE')

    def test_increment_views(self):
        """Test view count increment"""
        url = reverse('listing-increment-views', kwargs={'pk': self.listing.id})
        initial_views = self.listing.views_count

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.views_count, initial_views + 1)

    def test_increment_views_rate_limiting(self):
        """Test view count rate limiting"""
        url = reverse('listing-increment-views', kwargs={'pk': self.listing.id})

        # First request should increment
        response1 = self.client.post(url)
        views_after_first = response1.data['views_count']

        # Second request within rate limit should not increment
        response2 = self.client.post(url)
        views_after_second = response2.data['views_count']

        self.assertEqual(views_after_first, views_after_second)

    def test_increment_contacts(self):
        """Test contact count increment"""
        url = reverse('listing-increment-contacts', kwargs={'pk': self.listing.id})
        initial_contacts = self.listing.contact_count

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.contact_count, initial_contacts + 1)

    def test_bulk_update_status(self):
        """Test bulk status update"""
        self.client.force_authenticate(user=self.user)

        # Create multiple listings
        listing2 = Listing.objects.create(
            merchant=self.merchant,
            title='Product 2',
            description='Description 2',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=Decimal('200.00'),
            status='DRAFT'
        )

        url = reverse('listing-bulk-update-status')
        data = {
            'listing_ids': [str(self.listing.id), str(listing2.id)],
            'status': 'PENDING'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('updated_count', response.data)

    def test_bulk_delete(self):
        """Test bulk soft delete"""
        self.client.force_authenticate(user=self.user)

        listing2 = Listing.objects.create(
            merchant=self.merchant,
            title='Product 2',
            description='Description 2',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=Decimal('200.00')
        )

        url = reverse('listing-bulk-delete')
        data = {
            'listing_ids': [str(self.listing.id), str(listing2.id)]
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted_count'], 2)

        # Verify soft delete
        self.listing.refresh_from_db()
        listing2.refresh_from_db()
        self.assertIsNotNone(self.listing.deleted_at)
        self.assertIsNotNone(listing2.deleted_at)

    def test_analytics(self):
        """Test analytics endpoint"""
        self.client.force_authenticate(user=self.user)

        url = reverse('listing-analytics')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('overview', response.data)
        self.assertIn('by_status', response.data)
        self.assertIn('timeline', response.data)

    def test_export_csv(self):
        """Test CSV export"""
        self.client.force_authenticate(user=self.user)

        url = reverse('listing-export-csv')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_listing_stats(self):
        """Test listing stats endpoint"""
        self.client.force_authenticate(user=self.user)

        url = reverse('listing-stats', kwargs={'pk': self.listing.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('views', response.data)
        self.assertIn('contacts', response.data)
        self.assertIn('is_active', response.data)


class ListingBusinessHourTestCase(TestCase):
    """Test cases for ListingBusinessHour model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            display_name='Test Merchant'
        )
        self.category = Category.objects.create(
            name='Services',
            slug='services'
        )
        self.listing = Listing.objects.create(
            merchant=self.merchant,
            title='Test Service',
            description='Test description',
            listing_type='SERVICE',
            category=self.category,
            price_type='FIXED',
            price=Decimal('100.00')
        )

    def test_create_business_hour(self):
        """Test creating business hours"""
        hour = ListingBusinessHour.objects.create(
            listing=self.listing,
            day='MON',
            opens_at='09:00:00',
            closes_at='17:00:00',
            is_closed=False
        )

        self.assertEqual(hour.listing, self.listing)
        self.assertEqual(hour.day, 'MON')
        self.assertFalse(hour.is_closed)

    def test_closed_day(self):
        """Test creating a closed day"""
        hour = ListingBusinessHour.objects.create(
            listing=self.listing,
            day='SUN',
            is_closed=True
        )

        self.assertTrue(hour.is_closed)
        self.assertIsNone(hour.opens_at)
        self.assertIsNone(hour.closes_at)

    def test_unique_day_per_listing(self):
        """Test that days are unique per listing"""
        ListingBusinessHour.objects.create(
            listing=self.listing,
            day='MON',
            opens_at='09:00:00',
            closes_at='17:00:00'
        )

        # Try to create duplicate
        with self.assertRaises(Exception):
            ListingBusinessHour.objects.create(
                listing=self.listing,
                day='MON',
                opens_at='10:00:00',
                closes_at='18:00:00'
            )


class ListingServiceTestCase(TestCase):
    """Test cases for ListingService"""

    def setUp(self):
        """Set up test data"""
        from .services import ListingService

        self.service = ListingService
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            display_name='Test Merchant',
            verified=True
        )
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )

    def test_create_listing_service(self):
        """Test creating listing through service"""
        validated_data = {
            'title': 'Service Created Listing',
            'description': 'Created through service',
            'listing_type': 'PRODUCT',
            'category': self.category,
            'price_type': 'FIXED',
            'price': Decimal('150.00'),
            'currency': 'UGX'
        }

        listing = self.service.create_listing(
            merchant=self.merchant,
            validated_data=validated_data
        )

        self.assertIsNotNone(listing.id)
        self.assertEqual(listing.title, 'Service Created Listing')
        self.assertEqual(listing.status, 'PENDING')

    def test_get_listing_stats(self):
        """Test getting listing statistics"""
        listing = Listing.objects.create(
            merchant=self.merchant,
            title='Test Product',
            description='Test description',
            listing_type='PRODUCT',
            category=self.category,
            price_type='FIXED',
            price=Decimal('100.00'),
            status='ACTIVE',
            is_verified=True,
            views_count=50,
            contact_count=10
        )

        stats = self.service.get_listing_stats(listing)

        self.assertEqual(stats['views'], 50)
        self.assertEqual(stats['contacts'], 10)
        self.assertTrue(stats['is_active'])
        self.assertIn('engagement_rate', stats)