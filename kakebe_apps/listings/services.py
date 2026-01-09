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