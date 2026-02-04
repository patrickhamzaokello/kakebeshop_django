"""
Django management command to seed categories and subcategories for marketplace
Usage: python manage.py seed_categories
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from kakebe_apps.categories.models import Category  # Update 'your_app' with your actual app name


class Command(BaseCommand):
    help = 'Seeds categories and subcategories for the marketplace'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting category seeding...')

        categories_data = [
            {
                'name': 'Electronics',
                'icon': 'phone',
                'description': 'Mobile phones, computers, accessories and electronics',
                'is_featured': True,
                'sort_order': 1,
                'allows_cart': True,
                'subcategories': [
                    {'name': 'Mobile Phones', 'icon': 'smartphone', 'allows_cart': True},
                    {'name': 'Phone Accessories', 'icon': 'headphones', 'allows_cart': True},
                    {'name': 'Computers & Laptops', 'icon': 'laptop', 'allows_cart': True},
                    {'name': 'Computer Accessories', 'icon': 'keyboard', 'allows_cart': True},
                    {'name': 'Tablets', 'icon': 'tablet', 'allows_cart': True},
                    {'name': 'TVs & Audio', 'icon': 'tv', 'allows_cart': True},
                    {'name': 'Cameras', 'icon': 'camera', 'allows_cart': True},
                    {'name': 'Gaming', 'icon': 'gamepad', 'allows_cart': True},
                ]
            },
            {
                'name': 'Fashion & Apparel',
                'icon': 'shirt',
                'description': 'Clothing, shoes, bags and fashion accessories',
                'is_featured': True,
                'sort_order': 2,
                'allows_cart': True,
                'subcategories': [
                    {'name': "Men's Clothing", 'icon': 'user', 'allows_cart': True},
                    {'name': "Women's Clothing", 'icon': 'user', 'allows_cart': True},
                    {'name': "Children's Clothing", 'icon': 'baby', 'allows_cart': True},
                    {'name': 'Shoes & Footwear', 'icon': 'shoe', 'allows_cart': True},
                    {'name': 'Bags & Luggage', 'icon': 'briefcase', 'allows_cart': True},
                    {'name': 'Watches & Jewelry', 'icon': 'watch', 'allows_cart': True},
                    {'name': 'Fashion Accessories', 'icon': 'sunglasses', 'allows_cart': True},
                ]
            },
            {
                'name': 'Home & Living',
                'icon': 'home',
                'description': 'Furniture, appliances and home essentials',
                'is_featured': True,
                'sort_order': 3,
                'allows_cart': True,
                'subcategories': [
                    {'name': 'Furniture', 'icon': 'couch', 'allows_cart': True},
                    {'name': 'Home Appliances', 'icon': 'refrigerator', 'allows_cart': True},
                    {'name': 'Kitchen & Dining', 'icon': 'utensils', 'allows_cart': True},
                    {'name': 'Bedding & Linen', 'icon': 'bed', 'allows_cart': True},
                    {'name': 'Home Decor', 'icon': 'picture', 'allows_cart': True},
                    {'name': 'Lighting', 'icon': 'lightbulb', 'allows_cart': True},
                    {'name': 'Garden & Outdoor', 'icon': 'tree', 'allows_cart': True},
                ]
            },
            {
                'name': 'Vehicles',
                'icon': 'car',
                'description': 'Cars, motorcycles, bikes and vehicle parts',
                'is_featured': True,
                'sort_order': 4,
                'is_contact_only': True,
                'subcategories': [
                    {'name': 'Cars', 'icon': 'car', 'is_contact_only': True},
                    {'name': 'Motorcycles & Boda Bodas', 'icon': 'motorcycle', 'is_contact_only': True},
                    {'name': 'Bicycles', 'icon': 'bicycle', 'allows_cart': True},
                    {'name': 'Vehicle Parts & Accessories', 'icon': 'cog', 'allows_cart': True},
                    {'name': 'Trucks & Commercial Vehicles', 'icon': 'truck', 'is_contact_only': True},
                ]
            },
            {
                'name': 'Property',
                'icon': 'building',
                'description': 'Houses, apartments, land and commercial property',
                'is_featured': True,
                'sort_order': 5,
                'is_contact_only': True,
                'subcategories': [
                    {'name': 'Houses for Sale', 'icon': 'home', 'is_contact_only': True},
                    {'name': 'Houses for Rent', 'icon': 'home', 'is_contact_only': True},
                    {'name': 'Apartments for Rent', 'icon': 'building', 'is_contact_only': True},
                    {'name': 'Land for Sale', 'icon': 'map', 'is_contact_only': True},
                    {'name': 'Commercial Property', 'icon': 'store', 'is_contact_only': True},
                    {'name': 'Event Spaces', 'icon': 'calendar', 'is_contact_only': True},
                    {'name': 'Short-term Rentals', 'icon': 'key', 'is_contact_only': True},
                ]
            },
            {
                'name': 'Health & Beauty',
                'icon': 'heart',
                'description': 'Beauty products, cosmetics and wellness items',
                'sort_order': 6,
                'allows_cart': True,
                'subcategories': [
                    {'name': 'Skincare', 'icon': 'droplet', 'allows_cart': True},
                    {'name': 'Makeup & Cosmetics', 'icon': 'palette', 'allows_cart': True},
                    {'name': 'Hair Care', 'icon': 'scissors', 'allows_cart': True},
                    {'name': 'Fragrances', 'icon': 'spray', 'allows_cart': True},
                    {'name': 'Personal Care', 'icon': 'user', 'allows_cart': True},
                    {'name': 'Vitamins & Supplements', 'icon': 'pill', 'allows_cart': True},
                ]
            },
            {
                'name': 'Sports & Outdoors',
                'icon': 'football',
                'description': 'Sports equipment, outdoor gear and fitness items',
                'sort_order': 7,
                'allows_cart': True,
                'subcategories': [
                    {'name': 'Fitness & Gym Equipment', 'icon': 'dumbbell', 'allows_cart': True},
                    {'name': 'Team Sports', 'icon': 'football', 'allows_cart': True},
                    {'name': 'Outdoor Recreation', 'icon': 'mountain', 'allows_cart': True},
                    {'name': 'Sports Clothing', 'icon': 'shirt', 'allows_cart': True},
                    {'name': 'Cycling', 'icon': 'bicycle', 'allows_cart': True},
                ]
            },
            {
                'name': 'Kids & Babies',
                'icon': 'baby',
                'description': 'Baby products, toys and children essentials',
                'sort_order': 8,
                'allows_cart': True,
                'subcategories': [
                    {'name': 'Baby Clothing', 'icon': 'baby', 'allows_cart': True},
                    {'name': 'Baby Gear & Furniture', 'icon': 'stroller', 'allows_cart': True},
                    {'name': 'Toys & Games', 'icon': 'puzzle', 'allows_cart': True},
                    {'name': 'Baby Feeding', 'icon': 'bottle', 'allows_cart': True},
                    {'name': 'Diapers & Potty', 'icon': 'diaper', 'allows_cart': True},
                    {'name': 'School Supplies', 'icon': 'book', 'allows_cart': True},
                ]
            },
            {
                'name': 'Books & Media',
                'icon': 'book',
                'description': 'Books, magazines, music and educational materials',
                'sort_order': 9,
                'allows_cart': True,
                'subcategories': [
                    {'name': 'Books', 'icon': 'book', 'allows_cart': True},
                    {'name': 'Magazines', 'icon': 'newspaper', 'allows_cart': True},
                    {'name': 'Music & Instruments', 'icon': 'music', 'allows_cart': True},
                    {'name': 'Educational Materials', 'icon': 'graduation-cap', 'allows_cart': True},
                ]
            },
            {
                'name': 'Services',
                'icon': 'briefcase',
                'description': 'Professional services and business solutions',
                'sort_order': 10,
                'allows_order_intent': True,
                'subcategories': [
                    {'name': 'Professional Services', 'icon': 'briefcase', 'allows_order_intent': True},
                    {'name': 'Home Services', 'icon': 'wrench', 'allows_order_intent': True},
                    {'name': 'Events & Entertainment', 'icon': 'calendar', 'allows_order_intent': True},
                    {'name': 'Automotive Services', 'icon': 'car', 'allows_order_intent': True},
                    {'name': 'Beauty & Wellness', 'icon': 'spa', 'allows_order_intent': True},
                    {'name': 'Education & Training', 'icon': 'book', 'allows_order_intent': True},
                ]
            },
            {
                'name': 'Food & Groceries',
                'icon': 'shopping-cart',
                'description': 'Fresh produce, groceries and food items',
                'sort_order': 11,
                'allows_cart': True,
                'subcategories': [
                    {'name': 'Fresh Produce', 'icon': 'apple', 'allows_cart': True},
                    {'name': 'Groceries & Staples', 'icon': 'shopping-bag', 'allows_cart': True},
                    {'name': 'Beverages', 'icon': 'coffee', 'allows_cart': True},
                    {'name': 'Snacks & Sweets', 'icon': 'candy', 'allows_cart': True},
                    {'name': 'Meat & Seafood', 'icon': 'drumstick', 'allows_cart': True},
                ]
            },
            {
                'name': 'Agriculture',
                'icon': 'tractor',
                'description': 'Farm equipment, livestock and agricultural supplies',
                'sort_order': 12,
                'is_contact_only': True,
                'subcategories': [
                    {'name': 'Farm Equipment', 'icon': 'tractor', 'is_contact_only': True},
                    {'name': 'Livestock', 'icon': 'cow', 'is_contact_only': True},
                    {'name': 'Seeds & Fertilizers', 'icon': 'seedling', 'allows_cart': True},
                    {'name': 'Poultry', 'icon': 'egg', 'is_contact_only': True},
                ]
            },
            {
                'name': 'Business & Industry',
                'icon': 'industry',
                'description': 'Commercial equipment and industrial supplies',
                'sort_order': 13,
                'is_contact_only': True,
                'subcategories': [
                    {'name': 'Office Equipment', 'icon': 'printer', 'allows_cart': True},
                    {'name': 'Industrial Machinery', 'icon': 'cog', 'is_contact_only': True},
                    {'name': 'Safety Equipment', 'icon': 'shield', 'allows_cart': True},
                    {'name': 'Restaurant & Hospitality', 'icon': 'utensils', 'is_contact_only': True},
                ]
            },
            {
                'name': 'Pets',
                'icon': 'paw',
                'description': 'Pets, pet supplies and accessories',
                'sort_order': 14,
                'allows_cart': True,
                'subcategories': [
                    {'name': 'Dogs', 'icon': 'dog', 'allows_cart': True},
                    {'name': 'Cats', 'icon': 'cat', 'allows_cart': True},
                    {'name': 'Pet Food & Accessories', 'icon': 'bone', 'allows_cart': True},
                    {'name': 'Birds & Fish', 'icon': 'fish', 'allows_cart': True},
                ]
            },
            {
                'name': 'Jobs',
                'icon': 'briefcase',
                'description': 'Job listings and career opportunities',
                'sort_order': 15,
                'is_contact_only': True,
                'subcategories': [
                    {'name': 'Full-time Jobs', 'icon': 'briefcase', 'is_contact_only': True},
                    {'name': 'Part-time Jobs', 'icon': 'clock', 'is_contact_only': True},
                    {'name': 'Freelance & Contract', 'icon': 'laptop', 'is_contact_only': True},
                    {'name': 'Internships', 'icon': 'graduation-cap', 'is_contact_only': True},
                ]
            },
        ]

        created_count = 0
        updated_count = 0

        for category_data in categories_data:
            subcategories_data = category_data.pop('subcategories', [])

            # Create or update parent category
            category, created = Category.objects.update_or_create(
                slug=slugify(category_data['name']),
                defaults=category_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created category: {category.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated category: {category.name}')
                )

            # Create or update subcategories
            for subcategory_data in subcategories_data:
                subcategory_data['parent'] = category

                subcategory, sub_created = Category.objects.update_or_create(
                    slug=slugify(subcategory_data['name']),
                    defaults=subcategory_data
                )

                if sub_created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Created subcategory: {subcategory.name}')
                    )
                else:
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'  ↻ Updated subcategory: {subcategory.name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Seeding complete! Created: {created_count}, Updated: {updated_count}'
            )
        )