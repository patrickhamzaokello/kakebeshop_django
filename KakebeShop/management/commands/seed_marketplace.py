# kakebe_apps/core/management/commands/seed_marketplace.py

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Seed the entire marketplace with merchants and listings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--merchants',
            type=int,
            default=50,
            help='Number of merchants to create (default: 50)'
        )
        parser.add_argument(
            '--listings',
            type=int,
            default=200,
            help='Number of listings to create (default: 200)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding'
        )
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Quick seed with minimal data (10 merchants, 50 listings)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🌱 KAKEBE MARKETPLACE SEEDER'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        if options['quick']:
            merchants_count = 10
            listings_count = 50
            self.stdout.write('\n📦 Quick seed mode activated\n')
        else:
            merchants_count = options['merchants']
            listings_count = options['listings']

        clear = options['clear']

        # Step 1: Seed Merchants
        self.stdout.write(self.style.HTTP_INFO('\n[1/2] Seeding Merchants...'))
        self.stdout.write('-' * 60)

        call_command(
            'seed_merchants',
            count=merchants_count,
            verified=70,
            featured=20,
            clear=clear
        )

        # Step 2: Seed Listings
        self.stdout.write(self.style.HTTP_INFO('\n[2/2] Seeding Listings...'))
        self.stdout.write('-' * 60)

        call_command(
            'seed_listings',
            count=listings_count,
            active=80,
            featured=15,
            clear=clear
        )

        # Final Summary
        self._display_summary()

    def _display_summary(self):
        """Display final seeding summary"""
        from kakebe_apps.merchants.models import Merchant
        from kakebe_apps.listings.models import Listing
        from django.db.models import Count, Q

        merchant_stats = Merchant.objects.aggregate(
            total=Count('id'),
            verified=Count('id', filter=Q(verified=True)),
            featured=Count('id', filter=Q(featured=True)),
            active=Count('id', filter=Q(status='ACTIVE')),
        )

        listing_stats = Listing.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status='ACTIVE', is_verified=True)),
            featured=Count('id', filter=Q(is_featured=True)),
            products=Count('id', filter=Q(listing_type='PRODUCT')),
            services=Count('id', filter=Q(listing_type='SERVICE')),
        )

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('✅ SEEDING COMPLETE!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        self.stdout.write(self.style.HTTP_INFO('\n📊 MARKETPLACE STATISTICS:\n'))

        # Merchants
        self.stdout.write(self.style.WARNING('MERCHANTS:'))
        self.stdout.write(f'  • Total Merchants: {merchant_stats["total"]}')
        self.stdout.write(f'  • Verified: {merchant_stats["verified"]}')
        self.stdout.write(f'  • Featured: {merchant_stats["featured"]}')
        self.stdout.write(f'  • Active: {merchant_stats["active"]}')

        # Listings
        self.stdout.write(self.style.WARNING('\nLISTINGS:'))
        self.stdout.write(f'  • Total Listings: {listing_stats["total"]}')
        self.stdout.write(f'  • Active: {listing_stats["active"]}')
        self.stdout.write(f'  • Featured: {listing_stats["featured"]}')
        self.stdout.write(f'  • Products: {listing_stats["products"]}')
        self.stdout.write(f'  • Services: {listing_stats["services"]}')

        # Distribution
        avg_per_merchant = listing_stats["total"] / merchant_stats["total"] if merchant_stats["total"] > 0 else 0
        self.stdout.write(self.style.WARNING('\nDISTRIBUTION:'))
        self.stdout.write(f'  • Avg Listings per Merchant: {avg_per_merchant:.1f}')

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('🚀 Your marketplace is ready!\n'))