# kakebe_apps/listings/services.py
"""
Business logic layer for Listing operations.

This service layer separates business logic from views, making the code:
- More testable
- More maintainable
- Easier to reuse across different interfaces (API, admin, CLI)
"""

from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate
from typing import List, Dict, Optional
import logging
from decimal import Decimal

from .models import Listing, ListingBusinessHour, ListingTag
from ..imagehandler.models import ImageAsset
from ..categories.models import Tag

logger = logging.getLogger(__name__)


class ListingService:
    """Service class for Listing business logic"""

    @staticmethod
    @transaction.atomic
    def create_listing(
            merchant,
            validated_data: Dict,
            tag_ids: Optional[List[int]] = None,
            image_group_ids: Optional[List[str]] = None,
            business_hours_data: Optional[List[Dict]] = None
    ) -> Listing:
        """
        Create a listing with all related objects in a single transaction.

        Args:
            merchant: Merchant instance
            validated_data: Dictionary of validated listing data
            tag_ids: List of tag IDs to associate with listing
            image_group_ids: List of image group UUIDs to attach
            business_hours_data: List of business hours dictionaries

        Returns:
            Created Listing instance

        Raises:
            ValueError: If validation fails
        """
        try:
            # Create the listing
            listing = Listing.objects.create(
                merchant=merchant,
                status='PENDING',
                is_verified=False,
                **validated_data
            )

            logger.info(
                f"Listing created: {listing.id} by merchant {merchant.id}",
                extra={
                    'listing_id': str(listing.id),
                    'merchant_id': str(merchant.id),
                    'listing_type': listing.listing_type
                }
            )

            # Add tags
            if tag_ids:
                tags = Tag.objects.filter(id__in=tag_ids)
                listing.tags.set(tags)
                logger.debug(f"Added {len(tag_ids)} tags to listing {listing.id}")

            # Attach images
            if image_group_ids:
                updated_count = ImageAsset.objects.filter(
                    image_group_id__in=image_group_ids,
                    owner=merchant.user
                ).update(
                    object_id=listing.id,
                    is_confirmed=True
                )
                logger.debug(f"Attached {updated_count} image groups to listing {listing.id}")

            # Add business hours
            if business_hours_data:
                business_hours = [
                    ListingBusinessHour(listing=listing, **hours_data)
                    for hours_data in business_hours_data
                ]
                ListingBusinessHour.objects.bulk_create(business_hours)
                logger.debug(f"Added {len(business_hours)} business hours to listing {listing.id}")

            return listing

        except Exception as e:
            logger.error(
                f"Failed to create listing: {str(e)}",
                exc_info=True,
                extra={'merchant_id': str(merchant.id)}
            )
            raise

    @staticmethod
    @transaction.atomic
    def update_listing(
            listing: Listing,
            validated_data: Dict,
            tag_ids: Optional[List[int]] = None,
            add_image_groups: Optional[List[str]] = None,
            remove_image_groups: Optional[List[str]] = None
    ) -> Listing:
        """
        Update listing with atomic operations.

        Args:
            listing: Listing instance to update
            validated_data: Dictionary of validated update data
            tag_ids: List of tag IDs (replaces all existing tags)
            add_image_groups: List of image group UUIDs to add
            remove_image_groups: List of image group UUIDs to remove

        Returns:
            Updated Listing instance
        """
        try:
            # Update basic fields
            for attr, value in validated_data.items():
                setattr(listing, attr, value)

            # Handle status changes
            if 'status' in validated_data and validated_data['status'] == 'PENDING':
                listing.is_verified = False
                listing.verified_at = None

            listing.save()

            # Update tags if provided (replaces all existing tags)
            if tag_ids is not None:
                tags = Tag.objects.filter(id__in=tag_ids)
                listing.tags.set(tags)
                logger.debug(f"Updated tags for listing {listing.id}")

            # Add new images
            if add_image_groups:
                # Get current max order
                current_max_order = ImageAsset.objects.filter(
                    object_id=listing.id,
                    image_type="listing"
                ).count()

                # Update images with incremental order
                ImageAsset.objects.filter(
                    image_group_id__in=add_image_groups
                ).update(
                    object_id=listing.id,
                    is_confirmed=True,
                    order=current_max_order
                )
                logger.debug(f"Added {len(add_image_groups)} image groups to listing {listing.id}")

            # Remove images
            if remove_image_groups:
                removed_count = ImageAsset.objects.filter(
                    image_group_id__in=remove_image_groups,
                    object_id=listing.id
                ).update(
                    object_id=None,
                    is_confirmed=False,
                    order=0
                )
                logger.debug(f"Removed {removed_count} image groups from listing {listing.id}")

            logger.info(f"Listing updated: {listing.id}")
            return listing

        except Exception as e:
            logger.error(
                f"Failed to update listing {listing.id}: {str(e)}",
                exc_info=True
            )
            raise

    @staticmethod
    def soft_delete_listing(listing: Listing) -> None:
        """
        Soft delete a listing by setting deleted_at timestamp.

        Args:
            listing: Listing instance to delete
        """
        listing.deleted_at = timezone.now()
        listing.status = 'DEACTIVATED'
        listing.save(update_fields=['deleted_at', 'status'])

        logger.info(f"Listing soft deleted: {listing.id}")

    @staticmethod
    def increment_views(listing: Listing, user_ip: str) -> int:
        """
        Increment view count with rate limiting per IP.

        Args:
            listing: Listing instance
            user_ip: IP address of viewer

        Returns:
            Updated view count
        """
        cache_key = f"listing_view_{listing.id}_{user_ip}"

        # Check if this IP recently viewed
        if cache.get(cache_key):
            return listing.views_count

        # Increment and cache
        listing.views_count += 1
        listing.save(update_fields=['views_count'])

        # Set 5-minute cooldown
        cache.set(cache_key, True, 300)

        logger.debug(f"View incremented for listing {listing.id}")
        return listing.views_count

    @staticmethod
    def increment_contacts(listing: Listing, user_ip: str) -> int:
        """
        Increment contact count with rate limiting per IP.

        Args:
            listing: Listing instance
            user_ip: IP address of contact initiator

        Returns:
            Updated contact count
        """
        cache_key = f"listing_contact_{listing.id}_{user_ip}"

        # Check if this IP recently contacted
        if cache.get(cache_key):
            return listing.contact_count

        # Increment and cache
        listing.contact_count += 1
        listing.save(update_fields=['contact_count'])

        # Set 1-hour cooldown
        cache.set(cache_key, True, 3600)

        logger.info(f"Contact incremented for listing {listing.id}")
        return listing.contact_count

    @staticmethod
    def get_listing_stats(listing: Listing) -> Dict:
        """
        Get comprehensive statistics for a listing.

        Args:
            listing: Listing instance

        Returns:
            Dictionary with listing statistics
        """
        images_count = ImageAsset.objects.filter(
            object_id=listing.id,
            is_confirmed=True
        ).values('image_group_id').distinct().count()

        days_active = 0
        if listing.status == 'ACTIVE' and listing.verified_at:
            days_active = (timezone.now() - listing.verified_at).days

        return {
            'views': listing.views_count,
            'contacts': listing.contact_count,
            'images_count': images_count,
            'is_active': listing.is_active,
            'days_active': days_active,
            'engagement_rate': (
                (listing.contact_count / listing.views_count * 100)
                if listing.views_count > 0 else 0
            )
        }

    @staticmethod
    def get_merchant_analytics(merchant, days: int = 30) -> Dict:
        """
        Get analytics for a merchant's listings.

        Args:
            merchant: Merchant instance
            days: Number of days to include in time-based analytics

        Returns:
            Dictionary with comprehensive analytics
        """
        # Date range
        start_date = timezone.now() - timezone.timedelta(days=days)

        # Overall stats
        overall_stats = Listing.objects.filter(
            merchant=merchant,
            deleted_at__isnull=True
        ).aggregate(
            total_listings=Count('id'),
            active_listings=Count('id', filter=Q(status='ACTIVE', is_verified=True)),
            pending_listings=Count('id', filter=Q(status='PENDING')),
            draft_listings=Count('id', filter=Q(status='DRAFT')),
            total_views=Sum('views_count') or 0,
            total_contacts=Sum('contact_count') or 0,
            avg_views=Avg('views_count') or 0,
            avg_contacts=Avg('contact_count') or 0
        )

        # Listings by status
        by_status = list(
            Listing.objects.filter(
                merchant=merchant,
                deleted_at__isnull=True
            ).values('status').annotate(count=Count('id')).order_by('-count')
        )

        # Listings by type
        by_type = list(
            Listing.objects.filter(
                merchant=merchant,
                deleted_at__isnull=True
            ).values('listing_type').annotate(count=Count('id'))
        )

        # Recent listings timeline
        timeline = list(
            Listing.objects.filter(
                merchant=merchant,
                created_at__gte=start_date,
                deleted_at__isnull=True
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                count=Count('id'),
                views=Sum('views_count'),
                contacts=Sum('contact_count')
            ).order_by('date')
        )

        # Top performing listings
        top_listings = list(
            Listing.objects.filter(
                merchant=merchant,
                deleted_at__isnull=True,
                status='ACTIVE'
            ).order_by('-views_count')[:5].values(
                'id', 'title', 'views_count', 'contact_count'
            )
        )

        return {
            'overview': overall_stats,
            'by_status': by_status,
            'by_type': by_type,
            'timeline': timeline,
            'top_listings': top_listings,
            'period_days': days,
            'generated_at': timezone.now().isoformat()
        }

    @staticmethod
    def bulk_update_status(
            listing_ids: List[str],
            merchant,
            new_status: str
    ) -> int:
        """
        Bulk update status for merchant's listings.

        Args:
            listing_ids: List of listing UUIDs
            merchant: Merchant instance
            new_status: New status value

        Returns:
            Number of listings updated
        """
        if new_status not in ['DRAFT', 'PENDING']:
            raise ValueError(f"Invalid status: {new_status}")

        updated = Listing.objects.filter(
            id__in=listing_ids,
            merchant=merchant,
            deleted_at__isnull=True
        ).update(status=new_status)

        logger.info(
            f"Bulk status update: {updated} listings to {new_status}",
            extra={'merchant_id': str(merchant.id)}
        )

        return updated

    @staticmethod
    def bulk_soft_delete(listing_ids: List[str], merchant) -> int:
        """
        Bulk soft delete merchant's listings.

        Args:
            listing_ids: List of listing UUIDs
            merchant: Merchant instance

        Returns:
            Number of listings deleted
        """
        listings = Listing.objects.filter(
            id__in=listing_ids,
            merchant=merchant,
            deleted_at__isnull=True
        )

        count = 0
        now = timezone.now()
        for listing in listings:
            listing.deleted_at = now
            listing.status = 'DEACTIVATED'
            listing.save(update_fields=['deleted_at', 'status'])
            count += 1

        logger.info(
            f"Bulk delete: {count} listings",
            extra={'merchant_id': str(merchant.id)}
        )

        return count

    @staticmethod
    def reorder_images(listing: Listing, order_map: Dict[str, int]) -> None:
        """
        Reorder images for a listing.

        Args:
            listing: Listing instance
            order_map: Dictionary mapping image_group_id to order number
        """
        with transaction.atomic():
            for image_group_id, order in order_map.items():
                ImageAsset.objects.filter(
                    image_group_id=image_group_id,
                    object_id=listing.id
                ).update(order=order)

        logger.debug(f"Reordered images for listing {listing.id}")

    @staticmethod
    def get_uploadable_images(user) -> List[Dict]:
        """
        Get draft images that can be attached to listings.

        Args:
            user: User instance

        Returns:
            List of dictionaries with image group information
        """
        draft_images = ImageAsset.objects.filter(
            owner=user,
            image_type="listing",
            is_confirmed=False,
            object_id__isnull=True
        ).order_by('-created_at')

        # Group by image_group_id
        grouped_images = {}
        for img in draft_images:
            group_id = str(img.image_group_id)
            if group_id not in grouped_images:
                grouped_images[group_id] = {
                    'image_group_id': group_id,
                    'created_at': img.created_at,
                    'variants': []
                }
            grouped_images[group_id]['variants'].append({
                'id': str(img.id),
                'variant': img.variant,
                'url': img.cdn_url(),
                'width': img.width,
                'height': img.height,
                'size_bytes': img.size_bytes
            })

        return list(grouped_images.values())


    """
      Service class for finding similar listings based on various criteria.
      Uses category, tags, price range, and listing type to determine similarity.
    
      FIXED: Properly handles Decimal types for price calculations
      """


    @staticmethod
    def get_similar_from_merchant(listing, limit=6, exclude_current=True):
        """
        Get similar listings from the same merchant.

        Args:
            listing: The reference Listing object
            limit: Maximum number of similar listings to return (default: 6)
            exclude_current: Whether to exclude the current listing (default: True)

        Returns:
            QuerySet of similar listings
        """
        cache_key = f'similar_merchant_{listing.id}_{limit}'
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        queryset = Listing.objects.filter(
            merchant=listing.merchant,
            status='ACTIVE',
            is_verified=True,
            deleted_at__isnull=True
        ).select_related(
            'merchant',
            'merchant__user',
            'category'
        ).prefetch_related('tags')

        # Exclude current listing if requested
        if exclude_current:
            queryset = queryset.exclude(id=listing.id)

        # Prioritize similar items
        similar_listings = []

        # 1. Same category and listing type
        same_category_type = queryset.filter(
            category=listing.category,
            listing_type=listing.listing_type
        ).order_by('-is_featured', '-views_count')[:limit]

        similar_listings.extend(same_category_type)

        # 2. If we need more, get same category (different type)
        if len(similar_listings) < limit:
            remaining = limit - len(similar_listings)
            same_category = queryset.filter(
                category=listing.category
            ).exclude(
                id__in=[l.id for l in similar_listings]
            ).order_by('-is_featured', '-views_count')[:remaining]

            similar_listings.extend(same_category)

        # 3. If still need more, get same listing type
        if len(similar_listings) < limit:
            remaining = limit - len(similar_listings)
            same_type = queryset.filter(
                listing_type=listing.listing_type
            ).exclude(
                id__in=[l.id for l in similar_listings]
            ).order_by('-is_featured', '-views_count')[:remaining]

            similar_listings.extend(same_type)

        # 4. Finally, just get any other listings from merchant
        if len(similar_listings) < limit:
            remaining = limit - len(similar_listings)
            other_listings = queryset.exclude(
                id__in=[l.id for l in similar_listings]
            ).order_by('-is_featured', '-created_at')[:remaining]

            similar_listings.extend(other_listings)

        # Cache for 15 minutes
        try:
            cache.set(cache_key, similar_listings, 60 * 15)
        except Exception as e:
            logger.warning(f"Failed to cache similar merchant listings: {e}")

        return similar_listings


    @staticmethod
    def get_similar_from_marketplace(listing, limit=12, exclude_current=True):
        """
        Get similar listings from the entire marketplace.
        Uses a scoring system based on:
        - Same category (highest weight)
        - Common tags
        - Similar price range
        - Same listing type

        Args:
            listing: The reference Listing object
            limit: Maximum number of similar listings to return (default: 12)
            exclude_current: Whether to exclude the current listing (default: True)

        Returns:
            List of similar listings ordered by relevance score

        FIXED: Properly handles Decimal types in price calculations
        """
        cache_key = f'similar_marketplace_{listing.id}_{limit}'
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        base_queryset = Listing.objects.filter(
            status='ACTIVE',
            is_verified=True,
            deleted_at__isnull=True,
            merchant__verified=True
        ).select_related(
            'merchant',
            'merchant__user',
            'category'
        ).prefetch_related('tags')

        # Exclude current listing and same merchant if requested
        if exclude_current:
            base_queryset = base_queryset.exclude(id=listing.id)

        # Get listing tags for comparison
        listing_tag_ids = list(listing.tags.values_list('id', flat=True))

        # Build complex query for similarity
        similar_listings = []

        # 1. HIGHEST PRIORITY: Same category + same listing type + matching tags
        if listing_tag_ids:
            category_type_tags = base_queryset.filter(
                category=listing.category,
                listing_type=listing.listing_type,
                tags__id__in=listing_tag_ids
            ).annotate(
                common_tags=Count('tags')
            ).order_by('-common_tags', '-is_featured', '-views_count').distinct()[:limit // 3]

            similar_listings.extend(category_type_tags)

        # 2. HIGH PRIORITY: Same category + same listing type (no tag match required)
        if len(similar_listings) < limit:
            remaining = limit - len(similar_listings)
            category_type = base_queryset.filter(
                category=listing.category,
                listing_type=listing.listing_type
            ).exclude(
                id__in=[l.id for l in similar_listings]
            ).order_by('-is_featured', '-views_count')[:remaining]

            similar_listings.extend(category_type)

        # 3. MEDIUM PRIORITY: Same category (different type OK)
        if len(similar_listings) < limit:
            remaining = limit - len(similar_listings)
            same_category = base_queryset.filter(
                category=listing.category
            ).exclude(
                id__in=[l.id for l in similar_listings]
            ).order_by('-is_featured', '-views_count')[:remaining]

            similar_listings.extend(same_category)

        # 4. LOWER PRIORITY: Similar price range + same listing type
        # FIXED: Convert float to Decimal for price calculations
        if len(similar_listings) < limit and listing.price:
            remaining = limit - len(similar_listings)

            # Convert listing.price to Decimal if it isn't already
            if isinstance(listing.price, Decimal):
                reference_price = listing.price
            else:
                reference_price = Decimal(str(listing.price))

            # Price within 50% range - use Decimal for calculations
            price_min = reference_price * Decimal('0.5')
            price_max = reference_price * Decimal('1.5')

            similar_price = base_queryset.filter(
                listing_type=listing.listing_type,
                price__gte=price_min,
                price__lte=price_max,
                price__isnull=False  # Only include listings with prices
            ).exclude(
                id__in=[l.id for l in similar_listings]
            ).order_by('-is_featured', '-views_count')[:remaining]

            similar_listings.extend(similar_price)

        # 5. ALTERNATIVE: Similar price range (price_min/price_max) + same listing type
        # FIXED: Handle price_min and price_max with Decimal
        if len(similar_listings) < limit and (listing.price_min or listing.price_max):
            remaining = limit - len(similar_listings)

            # Determine reference price from range
            if listing.price_min and listing.price_max:
                # Use average of min and max
                if isinstance(listing.price_min, Decimal):
                    avg_price = (listing.price_min + listing.price_max) / Decimal('2')
                else:
                    avg_price = (Decimal(str(listing.price_min)) + Decimal(str(listing.price_max))) / Decimal('2')
            elif listing.price_min:
                avg_price = Decimal(str(listing.price_min)) if not isinstance(listing.price_min,
                                                                              Decimal) else listing.price_min
            else:
                avg_price = Decimal(str(listing.price_max)) if not isinstance(listing.price_max,
                                                                              Decimal) else listing.price_max

            price_min = avg_price * Decimal('0.5')
            price_max = avg_price * Decimal('1.5')

            similar_price_range = base_queryset.filter(
                listing_type=listing.listing_type
            ).filter(
                Q(price__gte=price_min, price__lte=price_max) |
                Q(price_min__gte=price_min, price_min__lte=price_max) |
                Q(price_max__gte=price_min, price_max__lte=price_max)
            ).exclude(
                id__in=[l.id for l in similar_listings]
            ).order_by('-is_featured', '-views_count')[:remaining]

            similar_listings.extend(similar_price_range)

        # 6. LOWEST PRIORITY: Just same listing type
        if len(similar_listings) < limit:
            remaining = limit - len(similar_listings)
            same_type = base_queryset.filter(
                listing_type=listing.listing_type
            ).exclude(
                id__in=[l.id for l in similar_listings]
            ).order_by('-is_featured', '-views_count')[:remaining]

            similar_listings.extend(same_type)

        # Cache for 30 minutes
        try:
            cache.set(cache_key, similar_listings, 60 * 30)
        except Exception as e:
            logger.warning(f"Failed to cache similar marketplace listings: {e}")

        return similar_listings


    @staticmethod
    def clear_similarity_cache(listing):
        """
        Clear cached similar listings when a listing is updated.

        Args:
            listing: The Listing object that was updated
        """
        try:
            # Clear merchant similar cache
            for limit in [6, 8, 10, 12, 20]:  # Common limit values
                cache.delete(f'similar_merchant_{listing.id}_{limit}')

            # Clear marketplace similar cache
            for limit in [6, 8, 10, 12, 15, 20, 50]:  # Common limit values
                cache.delete(f'similar_marketplace_{listing.id}_{limit}')

            logger.info(f"Cleared similarity cache for listing {listing.id}")
        except Exception as e:
            logger.warning(f"Failed to clear similarity cache: {e}")


    @staticmethod
    def get_recommendations_for_user(user, limit=20):
        """
        Get personalized recommendations based on user's viewing/interaction history.
        This is a placeholder for future implementation with user behavior tracking.

        Args:
            user: User object
            limit: Maximum number of recommendations

        Returns:
            QuerySet of recommended listings
        """
        # For now, return popular listings
        # TODO: Implement based on user viewing history, purchases, etc.

        return Listing.objects.filter(
            status='ACTIVE',
            is_verified=True,
            deleted_at__isnull=True,
            merchant__verified=True
        ).select_related(
            'merchant',
            'category'
        ).order_by('-views_count', '-is_featured')[:limit]


# Helper function to safely convert to Decimal
def to_decimal(value):
    """
    Safely convert a value to Decimal.

    Args:
        value: Value to convert (can be int, float, str, or Decimal)

    Returns:
        Decimal or None if value is None
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return None