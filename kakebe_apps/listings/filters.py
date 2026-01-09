# kakebe_apps/listings/filters.py

from django_filters import rest_framework as filters
from django.db.models import Q
from .models import Listing


class ListingFilter(filters.FilterSet):
    """
    Advanced filtering for listings.

    Usage examples:
    - /listings/?min_price=100&max_price=500
    - /listings/?search=phone&category=electronics
    - /listings/?tags=smartphone,android&listing_type=PRODUCT
    - /listings/?is_negotiable=true
    - /listings/?created_after=2024-01-01
    """

    # Price filters
    min_price = filters.NumberFilter(method='filter_min_price', label='Minimum price')
    max_price = filters.NumberFilter(method='filter_max_price', label='Maximum price')

    # Search filter
    search = filters.CharFilter(method='filter_search', label='Search in title and description')

    # Category filter
    category = filters.UUIDFilter(field_name='category__id', label='Category ID')
    category_slug = filters.CharFilter(field_name='category__slug', label='Category slug')

    # Merchant filter
    merchant = filters.UUIDFilter(field_name='merchant__id', label='Merchant ID')

    # Tags filter
    tags = filters.CharFilter(method='filter_tags', label='Comma-separated tag names')

    # Price negotiability
    is_negotiable = filters.BooleanFilter(field_name='is_price_negotiable', label='Is price negotiable')

    # Date filters
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte', label='Created after')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte', label='Created before')

    # Featured filter
    is_featured = filters.BooleanFilter(field_name='is_featured', label='Is featured')

    class Meta:
        model = Listing
        fields = {
            'listing_type': ['exact'],
            'price_type': ['exact'],
            'status': ['exact'],
            'is_verified': ['exact'],
        }

    def filter_min_price(self, queryset, name, value):
        """
        Filter by minimum price.
        Considers both fixed prices and range prices.
        """
        return queryset.filter(
            Q(price__gte=value) |
            Q(price_min__gte=value)
        )

    def filter_max_price(self, queryset, name, value):
        """
        Filter by maximum price.
        Considers both fixed prices and range prices.
        """
        return queryset.filter(
            Q(price__lte=value) |
            Q(price_max__lte=value)
        )

    def filter_search(self, queryset, name, value):
        """
        Full-text search on title and description.
        Case-insensitive search.
        """
        return queryset.filter(
            Q(title__icontains=value) | Q(description__icontains=value)
        )

    def filter_tags(self, queryset, name, value):
        """
        Filter by comma-separated tag names.
        Returns listings that have ANY of the specified tags.
        """
        tag_names = [tag.strip() for tag in value.split(',') if tag.strip()]
        if not tag_names:
            return queryset

        return queryset.filter(tags__name__in=tag_names).distinct()


class MerchantListingFilter(filters.FilterSet):
    """
    Filter for merchant's own listings.
    Includes filters for all statuses and internal management.
    """

    # All filters from ListingFilter
    min_price = filters.NumberFilter(method='filter_min_price')
    max_price = filters.NumberFilter(method='filter_max_price')
    search = filters.CharFilter(method='filter_search')
    category = filters.UUIDFilter(field_name='category__id')
    tags = filters.CharFilter(method='filter_tags')
    is_negotiable = filters.BooleanFilter(field_name='is_price_negotiable')
    created_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    is_featured = filters.BooleanFilter(field_name='is_featured')

    # Additional filters for merchant view
    status = filters.MultipleChoiceFilter(
        choices=Listing.STATUS_CHOICES,
        label='Status (can select multiple)'
    )
    is_verified = filters.BooleanFilter(field_name='is_verified')
    has_images = filters.BooleanFilter(method='filter_has_images', label='Has images')

    class Meta:
        model = Listing
        fields = {
            'listing_type': ['exact'],
            'price_type': ['exact'],
        }

    def filter_min_price(self, queryset, name, value):
        return queryset.filter(
            Q(price__gte=value) | Q(price_min__gte=value)
        )

    def filter_max_price(self, queryset, name, value):
        return queryset.filter(
            Q(price__lte=value) | Q(price_max__lte=value)
        )

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) | Q(description__icontains=value)
        )

    def filter_tags(self, queryset, name, value):
        tag_names = [tag.strip() for tag in value.split(',') if tag.strip()]
        if not tag_names:
            return queryset
        return queryset.filter(tags__name__in=tag_names).distinct()

    def filter_has_images(self, queryset, name, value):
        """Filter listings that have or don't have images"""
        from ..imagehandler.models import ImageAsset

        listings_with_images = ImageAsset.objects.filter(
            image_type="listing",
            is_confirmed=True
        ).values_list('object_id', flat=True).distinct()

        if value:
            return queryset.filter(id__in=listings_with_images)
        else:
            return queryset.exclude(id__in=listings_with_images)