# kakebe_apps/merchants/management/commands/seed_merchants.py

import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from kakebe_apps.merchants.models import Merchant
from kakebe_apps.location.models import Location

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed merchants with realistic Ugandan business data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of merchants to create (default: 50)'
        )
        parser.add_argument(
            '--verified',
            type=int,
            default=70,
            help='Percentage of verified merchants (default: 70)'
        )
        parser.add_argument(
            '--featured',
            type=int,
            default=20,
            help='Percentage of featured merchants (default: 20)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing merchants before seeding'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing merchants...')
            Merchant.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Merchants cleared'))

        count = options['count']
        verified_percentage = options['verified']
        featured_percentage = options['featured']

        self.stdout.write(f'Creating {count} merchants...')

        # Get or create locations
        locations = self._get_or_create_locations()

        # Create users if they don't exist
        users = self._get_or_create_users(count)

        # Merchant templates - Ugandan businesses
        merchant_templates = self._get_merchant_templates()

        created_count = 0
        for i in range(count):
            try:
                # Select a template
                template = random.choice(merchant_templates)

                # Determine status
                is_verified = random.randint(1, 100) <= verified_percentage
                is_featured = random.randint(1, 100) <= featured_percentage and is_verified

                # Format names
                display_name = template['display_name'].format(i + 1) if '{}' in template['display_name'] else template[
                    'display_name']
                business_name = None
                if template.get('business_name'):
                    business_name = template['business_name'].format(i + 1) if '{}' in template['business_name'] else \
                    template['business_name']

                # Create merchant
                merchant = Merchant.objects.create(
                    user=users[i],
                    display_name=display_name,
                    business_name=business_name,
                    description=template['description'],
                    business_phone=self._generate_ugandan_phone(),
                    business_email=f"business{i + 1}@{template['email_domain']}",
                    location=random.choice(locations) if locations else None,
                    verified=is_verified,
                    verification_date=timezone.now() - timedelta(days=random.randint(1, 365)) if is_verified else None,
                    featured=is_featured,
                    featured_order=random.randint(1, 100) if is_featured else 0,
                    rating=round(random.uniform(3.5, 5.0), 1) if is_verified else 0.0,
                    total_reviews=random.randint(5, 500) if is_verified else 0,
                    status='ACTIVE',
                )

                created_count += 1

                if created_count % 10 == 0:
                    self.stdout.write(f'Created {created_count}/{count} merchants...')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating merchant {i + 1}: {str(e)}')
                )
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully created {created_count} merchants\n'
                f'  - Verified: {Merchant.objects.filter(verified=True).count()}\n'
                f'  - Featured: {Merchant.objects.filter(featured=True).count()}\n'
                f'  - Average Rating: {Merchant.objects.filter(verified=True).aggregate(avg_rating=models.Avg("rating"))["avg_rating"]:.1f}'
            )
        )

    def _get_or_create_locations(self):
        """Get existing locations or prompt to seed them"""
        locations = list(Location.objects.filter(is_active=True))

        if not locations:
            self.stdout.write(
                self.style.WARNING(
                    'No locations found. Please run: python manage.py seed_locations'
                )
            )
            self.stdout.write('Continuing without location assignment...')
            return []

        self.stdout.write(f'Found {len(locations)} locations')
        return locations

    def _get_or_create_users(self, count):
        """Get or create users for merchants"""
        users = []

        for i in range(count):
            username = f'merchant_user_{i + 1}'
            email = f'merchant{i + 1}@kakebe.ug'
            name = f'Merchant User {i + 1}'

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'name': name,
                }
            )

            if created:
                user.set_password('password123')
                user.save()

            users.append(user)

        return users

    def _generate_ugandan_phone(self):
        """Generate realistic Ugandan phone number"""
        prefixes = ['0700', '0701', '0702', '0703', '0704', '0705',
                    '0750', '0751', '0752', '0753', '0754', '0755',
                    '0760', '0761', '0762', '0763', '0764', '0765',
                    '0770', '0771', '0772', '0773', '0774', '0775',
                    '0780', '0781', '0782', '0783', '0784', '0785',
                    '0790', '0791', '0792', '0793', '0794', '0795']

        prefix = random.choice(prefixes)
        suffix = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        return f'{prefix}{suffix}'

    def _get_merchant_templates(self):
        """Get realistic Ugandan merchant templates"""
        return [
            # Fashion & Clothing
            {
                'display_name': 'Trendy Fashion Hub {}',
                'business_name': 'Trendy Fashion Hub Ltd {}',
                'description': 'Your one-stop shop for the latest fashion trends in Kampala. We offer quality clothing for men, women, and children at affordable prices.',
                'email_domain': 'trendyfashion.ug',
            },
            {
                'display_name': 'Elite Boutique {}',
                'business_name': 'Elite Boutique Uganda {}',
                'description': 'Premium fashion boutique offering designer wear, accessories, and custom tailoring services. Visit us for elegant outfits for all occasions.',
                'email_domain': 'eliteboutique.ug',
            },
            {
                'display_name': 'Kampala Fashion Store',
                'business_name': None,
                'description': 'Affordable and trendy fashion for the modern Ugandan. From casual wear to office attire, we have it all.',
                'email_domain': 'kampalafashion.ug',
            },

            # Electronics
            {
                'display_name': 'TechHub Uganda {}',
                'business_name': 'TechHub Electronics Ltd {}',
                'description': 'Leading supplier of genuine electronics in Uganda. Laptops, phones, accessories, and more with warranty and after-sales support.',
                'email_domain': 'techhub.ug',
            },
            {
                'display_name': 'Digital World {}',
                'business_name': 'Digital World Electronics {}',
                'description': 'Your trusted electronics dealer. We stock original smartphones, computers, TVs, and home appliances at competitive prices.',
                'email_domain': 'digitalworld.ug',
            },
            {
                'display_name': 'Gadgets Palace',
                'business_name': None,
                'description': 'Latest tech gadgets and accessories. Fast delivery within Kampala and nationwide shipping available.',
                'email_domain': 'gadgetspalace.ug',
            },

            # Food & Restaurants
            {
                'display_name': 'Mama\'s Kitchen {}',
                'business_name': 'Mama\'s Kitchen Restaurant {}',
                'description': 'Authentic Ugandan cuisine prepared with love. From luwombo to matoke, enjoy homemade meals that remind you of home.',
                'email_domain': 'mamaskitchen.ug',
            },
            {
                'display_name': 'Rolex Express',
                'business_name': None,
                'description': 'The best rolex in town! Fresh ingredients, generous portions, and fast service. Open daily from 6 AM to 10 PM.',
                'email_domain': 'rolexexpress.ug',
            },
            {
                'display_name': 'Taste of Uganda {}',
                'business_name': 'Taste of Uganda Ltd {}',
                'description': 'Experience the rich flavors of Ugandan cuisine. Catering services available for events and functions.',
                'email_domain': 'tasteuganda.ug',
            },

            # Beauty & Spa
            {
                'display_name': 'Glow Beauty Salon {}',
                'business_name': 'Glow Beauty & Spa {}',
                'description': 'Professional beauty services including hair styling, makeup, manicure, pedicure, and spa treatments. Walk-ins welcome!',
                'email_domain': 'glowbeauty.ug',
            },
            {
                'display_name': 'Queen\'s Touch Salon',
                'business_name': None,
                'description': 'Affordable beauty services for the modern woman. Expert stylists, quality products, and a relaxing atmosphere.',
                'email_domain': 'queenstouch.ug',
            },
            {
                'display_name': 'Urban Barber Shop {}',
                'business_name': 'Urban Barber Shop {}',
                'description': 'Premium grooming services for men. Professional barbers, modern techniques, and a cool vibe.',
                'email_domain': 'urbanbarber.ug',
            },

            # Home & Furniture
            {
                'display_name': 'Home Comfort Furniture {}',
                'business_name': 'Home Comfort Furniture Ltd {}',
                'description': 'Quality furniture for every home. Sofas, beds, dining sets, and custom-made pieces. Free delivery within Kampala.',
                'email_domain': 'homecomfort.ug',
            },
            {
                'display_name': 'Elegant Interiors {}',
                'business_name': 'Elegant Interiors Uganda {}',
                'description': 'Transform your space with our premium furniture and interior decor. Expert consultation available.',
                'email_domain': 'elegantinteriors.ug',
            },

            # Agro & Farming
            {
                'display_name': 'Fresh Harvest Uganda {}',
                'business_name': 'Fresh Harvest Agro Ltd {}',
                'description': 'Farm-fresh produce delivered to your doorstep. Vegetables, fruits, eggs, and poultry from our organic farm.',
                'email_domain': 'freshharvest.ug',
            },
            {
                'display_name': 'AgroLink Supplies {}',
                'business_name': 'AgroLink Supplies {}',
                'description': 'Agricultural inputs and equipment. Seeds, fertilizers, pesticides, and farming tools at wholesale prices.',
                'email_domain': 'agrolink.ug',
            },

            # Health & Wellness
            {
                'display_name': 'HealthPlus Pharmacy {}',
                'business_name': 'HealthPlus Pharmacy Ltd {}',
                'description': 'Licensed pharmacy offering genuine medications, health supplements, and medical equipment. Free consultations available.',
                'email_domain': 'healthplus.ug',
            },
            {
                'display_name': 'WellFit Gym {}',
                'business_name': 'WellFit Fitness Center {}',
                'description': 'Modern gym with state-of-the-art equipment, personal trainers, and group fitness classes. Transform your body today!',
                'email_domain': 'wellfit.ug',
            },

            # Services
            {
                'display_name': 'QuickFix Repairs {}',
                'business_name': 'QuickFix Repair Services {}',
                'description': 'Professional repair services for phones, laptops, TVs, and home appliances. Same-day service available.',
                'email_domain': 'quickfix.ug',
            },
            {
                'display_name': 'CleanHome Services {}',
                'business_name': 'CleanHome Cleaning Services {}',
                'description': 'Professional cleaning services for homes and offices. Reliable staff, eco-friendly products, flexible schedules.',
                'email_domain': 'cleanhome.ug',
            },

            # Kids & Baby
            {
                'display_name': 'Little Angels Store {}',
                'business_name': 'Little Angels Baby Shop {}',
                'description': 'Everything for your little one. Baby clothes, toys, diapers, strollers, and more. Quality products at family-friendly prices.',
                'email_domain': 'littleangels.ug',
            },
            {
                'display_name': 'Kidz World',
                'business_name': None,
                'description': 'Fun and educational toys, clothing, and accessories for children of all ages. Visit our showroom today!',
                'email_domain': 'kidzworld.ug',
            },

            # Crafts & Art
            {
                'display_name': 'African Crafts {}',
                'business_name': 'African Crafts Uganda {}',
                'description': 'Authentic African crafts, artwork, and souvenirs. Support local artisans and take home a piece of Uganda.',
                'email_domain': 'africancrafts.ug',
            },
            {
                'display_name': 'Creative Hands Studio',
                'business_name': None,
                'description': 'Custom artwork, handmade gifts, and creative workshops. Perfect for unique presents and home decor.',
                'email_domain': 'creativehands.ug',
            },

            # General Stores
            {
                'display_name': 'City Supermarket {}',
                'business_name': 'City Supermarket Ltd {}',
                'description': 'Your neighborhood supermarket with a wide range of groceries, household items, and fresh produce. Open 7 days a week.',
                'email_domain': 'citysupermarket.ug',
            },
            {
                'display_name': 'Value Mart {}',
                'business_name': 'Value Mart Uganda {}',
                'description': 'Quality products at unbeatable prices. From food to electronics, find everything you need under one roof.',
                'email_domain': 'valuemart.ug',
            },
        ]


# Import models for aggregate function
from django.db import models