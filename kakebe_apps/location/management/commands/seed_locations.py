# kakebe_apps/location/management/commands/seed_locations.py

from decimal import Decimal
from django.core.management.base import BaseCommand
from kakebe_apps.location.models import Location


class Command(BaseCommand):
    help = 'Seed locations with realistic Ugandan geographic data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--region',
            type=str,
            help='Seed only specific region (e.g., Central, Western, Eastern, Northern)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing locations before seeding'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Seed all regions (default: Central only)'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing locations...')
            Location.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Locations cleared'))

        specific_region = options.get('region')
        seed_all = options.get('all')

        if specific_region:
            self.stdout.write(f'Seeding {specific_region} region locations...')
            locations = self._get_locations_by_region(specific_region)
        elif seed_all:
            self.stdout.write('Seeding all regions...')
            locations = self._get_all_locations()
        else:
            self.stdout.write('Seeding Central region (default)...')
            locations = self._get_locations_by_region('Central')

        created_count = 0
        skipped_count = 0

        for location_data in locations:
            try:
                # Check if location already exists
                existing = Location.objects.filter(
                    district=location_data['district'],
                    area=location_data['area']
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                Location.objects.create(**location_data)
                created_count += 1

                if created_count % 10 == 0:
                    self.stdout.write(f'Created {created_count} locations...')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error creating location {location_data["area"]}: {str(e)}'
                    )
                )
                continue

        # Display statistics
        stats = self._get_statistics()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully created {created_count} locations'
                f' (skipped {skipped_count} existing)\n'
            )
        )

        self.stdout.write(self.style.HTTP_INFO('📊 LOCATION STATISTICS:\n'))
        for region, count in stats.items():
            self.stdout.write(f'  • {region}: {count} locations')

        self.stdout.write(
            self.style.SUCCESS(
                f'\n  Total: {sum(stats.values())} locations in database\n'
            )
        )

    def _get_statistics(self):
        """Get location statistics by region"""
        from django.db.models import Count

        stats = {}
        regions = Location.objects.values('region').annotate(
            count=Count('id')
        ).order_by('region')

        for item in regions:
            stats[item['region']] = item['count']

        return stats

    def _get_locations_by_region(self, region):
        """Get locations for a specific region"""
        all_locations = self._get_all_locations()
        return [loc for loc in all_locations if loc['region'] == region]

    def _get_all_locations(self):
        """Get all Ugandan locations with accurate coordinates"""
        return [
            # ===== CENTRAL REGION =====

            # KAMPALA DISTRICT
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Kampala Central Division',
                'latitude': Decimal('0.31628000'),
                'longitude': Decimal('32.58219000'),
                'address': 'Kampala Central Business District, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Nakasero',
                'latitude': Decimal('0.32562000'),
                'longitude': Decimal('32.58156000'),
                'address': 'Nakasero Hill, Kampala Central Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Kololo',
                'latitude': Decimal('0.32891000'),
                'longitude': Decimal('32.59641000'),
                'address': 'Kololo, Kampala Central Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Naguru',
                'latitude': Decimal('0.33456000'),
                'longitude': Decimal('32.60123000'),
                'address': 'Naguru, Nakawa Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Bugolobi',
                'latitude': Decimal('0.32012000'),
                'longitude': Decimal('32.61234000'),
                'address': 'Bugolobi, Nakawa Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Ntinda',
                'latitude': Decimal('0.35123000'),
                'longitude': Decimal('32.62456000'),
                'address': 'Ntinda, Nakawa Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Kamwokya',
                'latitude': Decimal('0.34567000'),
                'longitude': Decimal('32.59234000'),
                'address': 'Kamwokya, Kampala Central Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Wandegeya',
                'latitude': Decimal('0.33789000'),
                'longitude': Decimal('32.57234000'),
                'address': 'Wandegeya, Kawempe Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Makerere',
                'latitude': Decimal('0.33012000'),
                'longitude': Decimal('32.56789000'),
                'address': 'Makerere, Kawempe Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Mulago',
                'latitude': Decimal('0.33845000'),
                'longitude': Decimal('32.57512000'),
                'address': 'Mulago, Kawempe Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Kawempe',
                'latitude': Decimal('0.37234000'),
                'longitude': Decimal('32.56123000'),
                'address': 'Kawempe Town, Kawempe Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Kalerwe',
                'latitude': Decimal('0.36789000'),
                'longitude': Decimal('32.57456000'),
                'address': 'Kalerwe, Kawempe Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Nansana',
                'latitude': Decimal('0.36234000'),
                'longitude': Decimal('32.52345000'),
                'address': 'Nansana, Wakiso District (Greater Kampala)',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Mengo',
                'latitude': Decimal('0.30345000'),
                'longitude': Decimal('32.55678000'),
                'address': 'Mengo, Rubaga Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Rubaga',
                'latitude': Decimal('0.29876000'),
                'longitude': Decimal('32.55123000'),
                'address': 'Rubaga Hill, Rubaga Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Nateete',
                'latitude': Decimal('0.29123000'),
                'longitude': Decimal('32.53456000'),
                'address': 'Nateete, Rubaga Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Busega',
                'latitude': Decimal('0.28567000'),
                'longitude': Decimal('32.52789000'),
                'address': 'Busega, Rubaga Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Katwe',
                'latitude': Decimal('0.29890000'),
                'longitude': Decimal('32.57234000'),
                'address': 'Katwe, Makindye Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Nsambya',
                'latitude': Decimal('0.29456000'),
                'longitude': Decimal('32.59123000'),
                'address': 'Nsambya, Makindye Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Kabalagala',
                'latitude': Decimal('0.28234000'),
                'longitude': Decimal('32.59789000'),
                'address': 'Kabalagala, Makindye Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Kibuli',
                'latitude': Decimal('0.30123000'),
                'longitude': Decimal('32.59456000'),
                'address': 'Kibuli, Makindye Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Muyenga',
                'latitude': Decimal('0.27890000'),
                'longitude': Decimal('32.61234000'),
                'address': 'Muyenga, Makindye Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Bukoto',
                'latitude': Decimal('0.34890000'),
                'longitude': Decimal('32.59567000'),
                'address': 'Bukoto, Nakawa Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Kisaasi',
                'latitude': Decimal('0.36123000'),
                'longitude': Decimal('32.61456000'),
                'address': 'Kisaasi, Nakawa Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Kyanja',
                'latitude': Decimal('0.37456000'),
                'longitude': Decimal('32.60789000'),
                'address': 'Kyanja, Nakawa Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Najjera',
                'latitude': Decimal('0.38789000'),
                'longitude': Decimal('32.62345000'),
                'address': 'Najjera, Kira Municipality, Wakiso District',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Kiwatule',
                'latitude': Decimal('0.36456000'),
                'longitude': Decimal('32.63123000'),
                'address': 'Kiwatule, Nakawa Division, Kampala',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Kampala',
                'area': 'Namugongo',
                'latitude': Decimal('0.37890000'),
                'longitude': Decimal('32.65456000'),
                'address': 'Namugongo, Kira Municipality, Wakiso District',
                'is_active': True,
            },

            # WAKISO DISTRICT
            {
                'region': 'Central',
                'district': 'Wakiso',
                'area': 'Entebbe',
                'latitude': Decimal('0.06420000'),
                'longitude': Decimal('32.47950000'),
                'address': 'Entebbe Municipality, Wakiso District',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Wakiso',
                'area': 'Kira',
                'latitude': Decimal('0.38234000'),
                'longitude': Decimal('32.64567000'),
                'address': 'Kira Town, Kira Municipality, Wakiso District',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Wakiso',
                'area': 'Makindye Ssabagabo',
                'latitude': Decimal('0.23456000'),
                'longitude': Decimal('32.58789000'),
                'address': 'Makindye Ssabagabo, Wakiso District',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Wakiso',
                'area': 'Wakiso Town',
                'latitude': Decimal('0.40567000'),
                'longitude': Decimal('32.50234000'),
                'address': 'Wakiso Town, Wakiso District',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Wakiso',
                'area': 'Nangabo',
                'latitude': Decimal('0.39890000'),
                'longitude': Decimal('32.51456000'),
                'address': 'Nangabo, Wakiso District',
                'is_active': True,
            },

            # MUKONO DISTRICT
            {
                'region': 'Central',
                'district': 'Mukono',
                'area': 'Mukono Town',
                'latitude': Decimal('0.35321000'),
                'longitude': Decimal('32.75539000'),
                'address': 'Mukono Town, Mukono District',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Mukono',
                'area': 'Seeta',
                'latitude': Decimal('0.36890000'),
                'longitude': Decimal('32.70234000'),
                'address': 'Seeta, Mukono District',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Mukono',
                'area': 'Kyampisi',
                'latitude': Decimal('0.41234000'),
                'longitude': Decimal('32.78567000'),
                'address': 'Kyampisi, Mukono District',
                'is_active': True,
            },

            # MPIGI DISTRICT
            {
                'region': 'Central',
                'district': 'Mpigi',
                'area': 'Mpigi Town',
                'latitude': Decimal('0.22531000'),
                'longitude': Decimal('32.31462000'),
                'address': 'Mpigi Town, Mpigi District',
                'is_active': True,
            },

            # MASAKA DISTRICT
            {
                'region': 'Central',
                'district': 'Masaka',
                'area': 'Masaka City',
                'latitude': Decimal('-0.33790000'),
                'longitude': Decimal('31.73409000'),
                'address': 'Masaka City, Masaka District',
                'is_active': True,
            },
            {
                'region': 'Central',
                'district': 'Masaka',
                'area': 'Nyendo',
                'latitude': Decimal('-0.35123000'),
                'longitude': Decimal('31.73890000'),
                'address': 'Nyendo, Masaka City',
                'is_active': True,
            },

            # ===== WESTERN REGION =====

            # MBARARA DISTRICT
            {
                'region': 'Western',
                'district': 'Mbarara',
                'area': 'Mbarara City',
                'latitude': Decimal('-0.60467000'),
                'longitude': Decimal('30.65837000'),
                'address': 'Mbarara City, Mbarara District',
                'is_active': True,
            },
            {
                'region': 'Western',
                'district': 'Mbarara',
                'area': 'Kakiika',
                'latitude': Decimal('-0.62345000'),
                'longitude': Decimal('30.64123000'),
                'address': 'Kakiika Division, Mbarara City',
                'is_active': True,
            },
            {
                'region': 'Western',
                'district': 'Mbarara',
                'area': 'Kamukuzi',
                'latitude': Decimal('-0.60890000'),
                'longitude': Decimal('30.66234000'),
                'address': 'Kamukuzi Division, Mbarara City',
                'is_active': True,
            },

            # FORT PORTAL (KABAROLE DISTRICT)
            {
                'region': 'Western',
                'district': 'Kabarole',
                'area': 'Fort Portal City',
                'latitude': Decimal('0.67121000'),
                'longitude': Decimal('30.27500000'),
                'address': 'Fort Portal City, Kabarole District',
                'is_active': True,
            },

            # KASESE DISTRICT
            {
                'region': 'Western',
                'district': 'Kasese',
                'area': 'Kasese Town',
                'latitude': Decimal('0.18330000'),
                'longitude': Decimal('30.08330000'),
                'address': 'Kasese Municipality, Kasese District',
                'is_active': True,
            },

            # HOIMA DISTRICT
            {
                'region': 'Western',
                'district': 'Hoima',
                'area': 'Hoima City',
                'latitude': Decimal('1.43314000'),
                'longitude': Decimal('31.35241000'),
                'address': 'Hoima City, Hoima District',
                'is_active': True,
            },

            # KABALE DISTRICT
            {
                'region': 'Western',
                'district': 'Kabale',
                'area': 'Kabale Town',
                'latitude': Decimal('-1.24857000'),
                'longitude': Decimal('29.98985000'),
                'address': 'Kabale Municipality, Kabale District',
                'is_active': True,
            },

            # ===== EASTERN REGION =====

            # JINJA DISTRICT
            {
                'region': 'Eastern',
                'district': 'Jinja',
                'area': 'Jinja City',
                'latitude': Decimal('0.42415000'),
                'longitude': Decimal('33.20315000'),
                'address': 'Jinja City, Jinja District',
                'is_active': True,
            },
            {
                'region': 'Eastern',
                'district': 'Jinja',
                'area': 'Njeru',
                'latitude': Decimal('0.44567000'),
                'longitude': Decimal('33.18234000'),
                'address': 'Njeru Municipality, Buikwe District',
                'is_active': True,
            },

            # MBALE DISTRICT
            {
                'region': 'Eastern',
                'district': 'Mbale',
                'area': 'Mbale City',
                'latitude': Decimal('1.08209000'),
                'longitude': Decimal('34.17503000'),
                'address': 'Mbale City, Mbale District',
                'is_active': True,
            },

            # SOROTI DISTRICT
            {
                'region': 'Eastern',
                'district': 'Soroti',
                'area': 'Soroti City',
                'latitude': Decimal('1.71466000'),
                'longitude': Decimal('33.61110000'),
                'address': 'Soroti City, Soroti District',
                'is_active': True,
            },

            # TORORO DISTRICT
            {
                'region': 'Eastern',
                'district': 'Tororo',
                'area': 'Tororo Town',
                'latitude': Decimal('0.69290000'),
                'longitude': Decimal('34.18086000'),
                'address': 'Tororo Municipality, Tororo District',
                'is_active': True,
            },

            # IGANGA DISTRICT
            {
                'region': 'Eastern',
                'district': 'Iganga',
                'area': 'Iganga Town',
                'latitude': Decimal('0.60917000'),
                'longitude': Decimal('33.46861000'),
                'address': 'Iganga Municipality, Iganga District',
                'is_active': True,
            },

            # ===== NORTHERN REGION =====

            # GULU DISTRICT
            {
                'region': 'Northern',
                'district': 'Gulu',
                'area': 'Gulu City',
                'latitude': Decimal('2.77457000'),
                'longitude': Decimal('32.29899000'),
                'address': 'Gulu City, Gulu District',
                'is_active': True,
            },
            {
                'region': 'Northern',
                'district': 'Gulu',
                'area': 'Bardege',
                'latitude': Decimal('2.76890000'),
                'longitude': Decimal('32.29234000'),
                'address': 'Bardege Division, Gulu City',
                'is_active': True,
            },

            # LIRA DISTRICT
            {
                'region': 'Northern',
                'district': 'Lira',
                'area': 'Lira City',
                'latitude': Decimal('2.23970000'),
                'longitude': Decimal('32.89940000'),
                'address': 'Lira City, Lira District',
                'is_active': True,
            },

            # ARUA DISTRICT
            {
                'region': 'Northern',
                'district': 'Arua',
                'area': 'Arua City',
                'latitude': Decimal('3.01980000'),
                'longitude': Decimal('30.91105000'),
                'address': 'Arua City, Arua District',
                'is_active': True,
            },

            # KITGUM DISTRICT
            {
                'region': 'Northern',
                'district': 'Kitgum',
                'area': 'Kitgum Town',
                'latitude': Decimal('3.29650000'),
                'longitude': Decimal('32.88660000'),
                'address': 'Kitgum Municipality, Kitgum District',
                'is_active': True,
            },
        ]