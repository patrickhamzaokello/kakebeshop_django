# kakebe_apps/listings/management/commands/seed_listings.py

import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from kakebe_apps.listings.models import Listing, ListingBusinessHour
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.categories.models import Category, Tag


class Command(BaseCommand):
    help = 'Seed listings with realistic Ugandan products and services'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=200,
            help='Number of listings to create (default: 200)'
        )
        parser.add_argument(
            '--per-merchant',
            type=int,
            default=5,
            help='Average listings per merchant (default: 5)'
        )
        parser.add_argument(
            '--active',
            type=int,
            default=80,
            help='Percentage of active listings (default: 80)'
        )
        parser.add_argument(
            '--featured',
            type=int,
            default=15,
            help='Percentage of featured listings (default: 15)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing listings before seeding'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing listings...')
            Listing.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Listings cleared'))

        # Get merchants
        merchants = list(Merchant.objects.filter(verified=True, status='ACTIVE'))

        if not merchants:
            self.stdout.write(
                self.style.ERROR('No verified merchants found. Please run seed_merchants first.')
            )
            return

        # Get categories and tags
        categories = list(Category.objects.all())
        tags = list(Tag.objects.all())

        if not categories:
            self.stdout.write(
                self.style.ERROR('No categories found. Please create categories first.')
            )
            return

        count = options['count']
        active_percentage = options['active']
        featured_percentage = options['featured']

        self.stdout.write(f'Creating {count} listings across {len(merchants)} merchants...')

        # Listing templates by category
        listing_templates = self._get_listing_templates()

        created_count = 0
        for i in range(count):
            try:
                # Select random merchant
                merchant = random.choice(merchants)

                # Select category and matching template
                category = random.choice(categories)
                category_templates = [
                    t for t in listing_templates
                    if t['category_name'].upper() in category.name.upper()
                ]

                if not category_templates:
                    # Fall back to any template
                    category_templates = listing_templates

                template = random.choice(category_templates)

                # Determine status
                is_active = random.randint(1, 100) <= active_percentage
                is_featured = random.randint(1, 100) <= featured_percentage and is_active

                # Price configuration
                price_config = self._generate_price(template)

                # Create listing
                listing = Listing.objects.create(
                    merchant=merchant,
                    title=self._generate_title(template, i),
                    description=template['description'],
                    listing_type=template['listing_type'],
                    category=category,
                    price_type=price_config['price_type'],
                    price=price_config.get('price'),
                    price_min=price_config.get('price_min'),
                    price_max=price_config.get('price_max'),
                    currency='UGX',
                    is_price_negotiable=template.get('negotiable', False),
                    status='ACTIVE' if is_active else random.choice(['DRAFT', 'PENDING', 'CLOSED']),
                    is_verified=is_active,
                    verified_at=timezone.now() - timedelta(days=random.randint(1, 30)) if is_active else None,
                    is_featured=is_featured,
                    featured_until=timezone.now() + timedelta(days=random.randint(7, 30)) if is_featured else None,
                    featured_order=random.randint(1, 100) if is_featured else 0,
                    views_count=random.randint(10, 1000) if is_active else 0,
                    contact_count=random.randint(1, 50) if is_active else 0,
                    created_at=timezone.now() - timedelta(days=random.randint(1, 180)),
                )

                # Add tags
                if tags:
                    listing_tags = random.sample(tags, min(random.randint(2, 5), len(tags)))
                    listing.tags.set(listing_tags)

                # Add business hours for services
                if template['listing_type'] == 'SERVICE':
                    self._create_business_hours(listing)

                created_count += 1

                if created_count % 20 == 0:
                    self.stdout.write(f'Created {created_count}/{count} listings...')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating listing {i + 1}: {str(e)}')
                )
                continue

        # Display statistics
        from django.db import models
        stats = Listing.objects.aggregate(
            total=models.Count('id'),
            active=models.Count('id', filter=models.Q(status='ACTIVE', is_verified=True)),
            featured=models.Count('id', filter=models.Q(is_featured=True)),
            products=models.Count('id', filter=models.Q(listing_type='PRODUCT')),
            services=models.Count('id', filter=models.Q(listing_type='SERVICE')),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully created {created_count} listings\n'
                f'  - Active: {stats["active"]}\n'
                f'  - Featured: {stats["featured"]}\n'
                f'  - Products: {stats["products"]}\n'
                f'  - Services: {stats["services"]}'
            )
        )

    def _generate_title(self, template, index):
        """Generate listing title with variation"""
        base_title = template['title']

        # Add variations
        variations = template.get('title_variations', [])
        if variations and random.random() > 0.5:
            base_title = random.choice(variations)

        return base_title

    def _generate_price(self, template):
        """Generate realistic pricing based on template"""
        price_range = template.get('price_range', (10000, 100000))
        price_type_options = template.get('price_types', ['FIXED'])

        price_type = random.choice(price_type_options)

        if price_type == 'FIXED':
            return {
                'price_type': 'FIXED',
                'price': Decimal(str(random.randint(price_range[0], price_range[1])))
            }
        elif price_type == 'RANGE':
            min_price = random.randint(price_range[0], price_range[1] // 2)
            max_price = random.randint(min_price, price_range[1])
            return {
                'price_type': 'RANGE',
                'price_min': Decimal(str(min_price)),
                'price_max': Decimal(str(max_price))
            }
        else:  # ON_REQUEST
            return {
                'price_type': 'ON_REQUEST'
            }

    def _create_business_hours(self, listing):
        """Create business hours for service listings"""
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

        # Common business hour patterns
        patterns = [
            # Monday to Friday 8-5, Saturday 8-2, Sunday closed
            {
                'weekday': ('08:00:00', '17:00:00'),
                'saturday': ('08:00:00', '14:00:00'),
                'sunday': 'closed'
            },
            # Monday to Saturday 9-6, Sunday closed
            {
                'weekday': ('09:00:00', '18:00:00'),
                'saturday': ('09:00:00', '18:00:00'),
                'sunday': 'closed'
            },
            # Open every day 8-8
            {
                'weekday': ('08:00:00', '20:00:00'),
                'saturday': ('08:00:00', '20:00:00'),
                'sunday': ('10:00:00', '18:00:00')
            },
        ]

        pattern = random.choice(patterns)

        for day in days:
            if day == 'SUN':
                if pattern['sunday'] == 'closed':
                    ListingBusinessHour.objects.create(
                        listing=listing,
                        day=day,
                        is_closed=True
                    )
                else:
                    ListingBusinessHour.objects.create(
                        listing=listing,
                        day=day,
                        opens_at=pattern['sunday'][0],
                        closes_at=pattern['sunday'][1],
                        is_closed=False
                    )
            elif day == 'SAT':
                ListingBusinessHour.objects.create(
                    listing=listing,
                    day=day,
                    opens_at=pattern['saturday'][0],
                    closes_at=pattern['saturday'][1],
                    is_closed=False
                )
            else:
                ListingBusinessHour.objects.create(
                    listing=listing,
                    day=day,
                    opens_at=pattern['weekday'][0],
                    closes_at=pattern['weekday'][1],
                    is_closed=False
                )

    def _get_listing_templates(self):
        """Get realistic listing templates for Ugandan market"""
        return [
            # FASHION
            {
                'category_name': 'FASHION',
                'listing_type': 'PRODUCT',
                'title': 'Ladies Fashion Dress - Elegant Design',
                'title_variations': [
                    'Beautiful Ladies Dress - Latest Fashion',
                    'Elegant Women\'s Dress - Party Wear',
                    'Stylish Ladies Dress - Office & Casual'
                ],
                'description': 'Beautiful and elegant dress perfect for office wear, parties, and special occasions. Available in multiple colors and sizes (S, M, L, XL, XXL). Quality fabric that is comfortable and durable. Free delivery within Kampala for orders above 100,000 UGX.',
                'price_range': (50000, 150000),
                'price_types': ['FIXED', 'RANGE'],
                'negotiable': True,
            },
            {
                'category_name': 'FASHION',
                'listing_type': 'PRODUCT',
                'title': 'Men\'s Casual Shirt - Quality Cotton',
                'title_variations': [
                    'Gents Shirts - Cotton Fabric',
                    'Men\'s Formal Shirts - All Sizes',
                    'Quality Men\'s Shirts - Various Designs'
                ],
                'description': 'High-quality men\'s shirts made from 100% cotton. Available in various colors and designs. Perfect for office, casual outings, and events. Sizes from S to XXXL. Wholesale prices available for bulk orders.',
                'price_range': (30000, 80000),
                'price_types': ['FIXED'],
                'negotiable': True,
            },
            {
                'category_name': 'FASHION',
                'listing_type': 'PRODUCT',
                'title': 'Kids School Uniform - Complete Set',
                'description': 'Complete school uniform set including shirt, shorts/skirt, tie, and belt. Durable fabric that can withstand daily wear. Available for nursery, primary, and secondary school. Custom embroidery available.',
                'price_range': (40000, 100000),
                'price_types': ['FIXED', 'RANGE'],
                'negotiable': False,
            },

            # ELECTRONICS
            {
                'category_name': 'ELECTRONICS',
                'listing_type': 'PRODUCT',
                'title': 'Samsung Galaxy Smartphone - Original',
                'title_variations': [
                    'Samsung Phone - Brand New',
                    'Original Samsung Galaxy - Warranty Included',
                    'Samsung Smartphone - Latest Model'
                ],
                'description': 'Brand new original Samsung Galaxy smartphone. Comes with 1-year warranty, charger, earphones, and protective case. Multiple storage options available (64GB, 128GB, 256GB). Free screen protector and delivery within Kampala.',
                'price_range': (500000, 3000000),
                'price_types': ['FIXED'],
                'negotiable': True,
            },
            {
                'category_name': 'ELECTRONICS',
                'listing_type': 'PRODUCT',
                'title': 'HP Laptop - Core i5, 8GB RAM',
                'title_variations': [
                    'HP Laptop - Fast Performance',
                    'Laptop HP - Perfect for Students',
                    'HP Notebook - Business & Personal Use'
                ],
                'description': 'Refurbished HP laptop in excellent condition. Intel Core i5 processor, 8GB RAM, 500GB HDD/256GB SSD. Perfect for students, business, and personal use. Comes with charger and laptop bag. 6-months warranty.',
                'price_range': (800000, 2500000),
                'price_types': ['FIXED', 'RANGE'],
                'negotiable': True,
            },
            {
                'category_name': 'ELECTRONICS',
                'listing_type': 'PRODUCT',
                'title': 'Smart TV - 32 inch Full HD',
                'description': 'Brand new smart TV with built-in WiFi, Netflix, YouTube, and more. Full HD display, USB ports, HDMI inputs. Wall mount bracket included. Free installation and setup within Kampala.',
                'price_range': (600000, 1500000),
                'price_types': ['FIXED'],
                'negotiable': False,
            },

            # FOOD
            {
                'category_name': 'FOOD',
                'listing_type': 'SERVICE',
                'title': 'Catering Services - Events & Functions',
                'description': 'Professional catering services for weddings, meetings, parties, and all types of events. Ugandan cuisine, continental dishes, and buffet options available. Experienced chefs and staff. Free consultation and menu planning.',
                'price_range': (500000, 5000000),
                'price_types': ['RANGE', 'ON_REQUEST'],
                'negotiable': True,
            },
            {
                'category_name': 'FOOD',
                'listing_type': 'PRODUCT',
                'title': 'Fresh Chicken - Whole & Pieces',
                'title_variations': [
                    'Farm Fresh Chicken - Whole Birds',
                    'Quality Chicken - Free Range',
                    'Fresh Poultry - Chicken & Turkey'
                ],
                'description': 'Fresh farm chicken delivered daily. Available whole or in pieces (breast, thighs, wings, drumsticks). Free-range and grain-fed. Minimum order 2kg. Free delivery for orders above 50,000 UGX within Kampala.',
                'price_range': (12000, 18000),  # per kg
                'price_types': ['FIXED'],
                'negotiable': False,
            },

            # BEAUTY
            {
                'category_name': 'BEAUTY',
                'listing_type': 'SERVICE',
                'title': 'Professional Hair Styling Services',
                'description': 'Expert hair styling services including braiding, weaving, hair treatment, coloring, and cutting. Experienced stylists using quality products. Book your appointment today. Walk-ins welcome!',
                'price_range': (20000, 200000),
                'price_types': ['RANGE'],
                'negotiable': False,
            },
            {
                'category_name': 'BEAUTY',
                'listing_type': 'PRODUCT',
                'title': 'Makeup Kit - Professional Quality',
                'description': 'Complete professional makeup kit with foundation, eyeshadow palette, lipsticks, brushes, and more. Perfect for makeup artists or personal use. Original products from trusted brands.',
                'price_range': (80000, 300000),
                'price_types': ['FIXED', 'RANGE'],
                'negotiable': True,
            },

            # HOME
            {
                'category_name': 'HOME',
                'listing_type': 'PRODUCT',
                'title': 'Sofa Set - 7 Seater (3+2+2)',
                'title_variations': [
                    'Living Room Sofa - Modern Design',
                    'Quality Sofa Set - Leather/Fabric',
                    'Comfortable Sofa - All Sizes Available'
                ],
                'description': 'Beautiful and comfortable sofa set perfect for your living room. Available in leather and fabric. Multiple color options. Strong wooden frame. Free delivery and assembly within Kampala. Custom sizes available.',
                'price_range': (1200000, 3500000),
                'price_types': ['FIXED', 'RANGE'],
                'negotiable': True,
            },
            {
                'category_name': 'HOME',
                'listing_type': 'PRODUCT',
                'title': 'King Size Bed with Mattress',
                'description': 'Quality king-size bed frame with orthopedic mattress. Strong construction, modern design. Mattress is 10-inch thick with memory foam top layer. Headboard included. Free delivery within Kampala.',
                'price_range': (800000, 2000000),
                'price_types': ['FIXED'],
                'negotiable': True,
            },

            # AGRO
            {
                'category_name': 'AGRO',
                'listing_type': 'PRODUCT',
                'title': 'Hybrid Maize Seeds - High Yield',
                'description': 'Certified hybrid maize seeds with high yield potential. Suitable for both commercial and small-scale farming. Drought resistant and disease tolerant. Available in 10kg, 25kg, and 50kg bags.',
                'price_range': (150000, 800000),
                'price_types': ['FIXED'],
                'negotiable': False,
            },
            {
                'category_name': 'AGRO',
                'listing_type': 'PRODUCT',
                'title': 'Fresh Tomatoes - Direct from Farm',
                'description': 'Fresh organic tomatoes harvested daily from our farm. Available in crates and boxes. Wholesale prices available for bulk buyers. Free delivery for orders above 100,000 UGX.',
                'price_range': (40000, 80000),  # per crate
                'price_types': ['FIXED'],
                'negotiable': True,
            },

            # HEALTH
            {
                'category_name': 'HEALTH',
                'listing_type': 'SERVICE',
                'title': 'Gym Membership - Monthly & Annual',
                'description': 'Full gym membership with access to all equipment, group classes, and personal trainer consultations. Modern facility with changing rooms and showers. Flexible payment plans available.',
                'price_range': (80000, 500000),
                'price_types': ['FIXED', 'RANGE'],
                'negotiable': False,
            },
            {
                'category_name': 'HEALTH',
                'listing_type': 'PRODUCT',
                'title': 'Herbal Supplements - Natural Health',
                'description': 'Natural herbal supplements for various health needs. Made from organic ingredients. Approved by health authorities. Available in capsules, tablets, and powder form.',
                'price_range': (30000, 120000),
                'price_types': ['FIXED'],
                'negotiable': False,
            },

            # KIDS
            {
                'category_name': 'KIDS',
                'listing_type': 'PRODUCT',
                'title': 'Baby Stroller - Foldable & Lightweight',
                'description': 'Quality baby stroller with comfortable seat, safety harness, and storage basket. Easy to fold and lightweight for travel. Suitable for babies 0-3 years. Multiple color options available.',
                'price_range': (250000, 600000),
                'price_types': ['FIXED'],
                'negotiable': True,
            },
            {
                'category_name': 'KIDS',
                'listing_type': 'PRODUCT',
                'title': 'Educational Toys - Learning & Fun',
                'description': 'Educational toys for children of all ages. Helps develop motor skills, creativity, and learning. Safe materials, non-toxic. Perfect for gifts and playtime.',
                'price_range': (15000, 150000),
                'price_types': ['FIXED', 'RANGE'],
                'negotiable': False,
            },

            # CRAFTS
            {
                'category_name': 'CRAFTS',
                'listing_type': 'PRODUCT',
                'title': 'Handmade Basket - Traditional Design',
                'description': 'Beautiful handmade baskets crafted by local artisans. Perfect for home decor, storage, or gifts. Various sizes and designs available. Support local craftsmanship.',
                'price_range': (20000, 100000),
                'price_types': ['FIXED', 'RANGE'],
                'negotiable': True,
            },
            {
                'category_name': 'CRAFTS',
                'listing_type': 'PRODUCT',
                'title': 'African Wall Art - Canvas Print',
                'description': 'Stunning African-themed wall art on high-quality canvas. Modern and traditional designs available. Perfect for living rooms, offices, and hotels. Custom sizes available.',
                'price_range': (50000, 250000),
                'price_types': ['FIXED', 'RANGE'],
                'negotiable': True,
            },

            # MARKET (General goods)
            {
                'category_name': 'MARKET',
                'listing_type': 'PRODUCT',
                'title': 'Rice - Quality Long Grain (25kg)',
                'description': 'Premium quality long-grain rice. Aromatic and perfectly cooked every time. Available in 5kg, 10kg, and 25kg bags. Wholesale prices for bulk orders.',
                'price_range': (60000, 120000),
                'price_types': ['FIXED'],
                'negotiable': False,
            },

            # TVS & APPLIANCES
            {
                'category_name': 'TVS',
                'listing_type': 'PRODUCT',
                'title': 'Washing Machine - Automatic 7kg',
                'description': 'Fully automatic washing machine with 7kg capacity. Multiple wash programs, energy efficient. Brand new with 1-year warranty. Free delivery and installation within Kampala.',
                'price_range': (600000, 1200000),
                'price_types': ['FIXED'],
                'negotiable': True,
            },
        ]