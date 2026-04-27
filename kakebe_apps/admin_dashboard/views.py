from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from celery import current_app
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from kakebe_apps.analytics import events as analytics
from kakebe_apps.categories.models import Category, Tag
from kakebe_apps.imagehandler.models import ImageAsset
from kakebe_apps.listings.models import Listing
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.orders.models import OrderIntent
from kakebe_apps.notifications.models import BroadcastNotificationCampaign
from kakebe_apps.notifications.tasks import send_broadcast_campaign
from .permissions import IsStaffUser
from .serializers import (
    AdminBroadcastCampaignCreateSerializer,
    AdminBroadcastCampaignSerializer,
    AdminCategorySerializer,
    AdminCategoryUpdateSerializer,
    AdminImageAssetSerializer,
    AdminListingSerializer,
    AdminListingUpdateSerializer,
    AdminMerchantSerializer,
    AdminMerchantUpdateSerializer,
    AdminOrderSerializer,
    AdminOrderUpdateSerializer,
    AdminStatsSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
)

User = get_user_model()


class AdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })


# ─────────────────────────── Stats ───────────────────────────

class AdminStatsView(ViewSet):
    """GET /api/v1/admin/stats/ — platform-wide counts for the dashboard overview."""
    permission_classes = [IsStaffUser]

    def list(self, request):
        data = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'staff_users': User.objects.filter(is_staff=True).count(),

            'total_merchants': Merchant.objects.count(),
            'verified_merchants': Merchant.objects.filter(verified=True).count(),
            'pending_merchants': Merchant.objects.filter(verified=False, deleted_at__isnull=True).count(),

            'total_listings': Listing.objects.filter(deleted_at__isnull=True).count(),
            'active_listings': Listing.objects.filter(status='ACTIVE', deleted_at__isnull=True).count(),
            'pending_listings': Listing.objects.filter(status='PENDING', deleted_at__isnull=True).count(),

            'total_orders': OrderIntent.objects.count(),
            'new_orders': OrderIntent.objects.filter(status='NEW').count(),
            'completed_orders': OrderIntent.objects.filter(status='COMPLETED').count(),
            'cancelled_orders': OrderIntent.objects.filter(status='CANCELLED').count(),

            'total_categories': Category.objects.count(),
            'total_images': ImageAsset.objects.filter(is_confirmed=True).count(),
        }
        serializer = AdminStatsSerializer(data)
        return Response({'success': True, 'data': serializer.data})


# ─────────────────────────── Users ───────────────────────────

class AdminUserViewSet(ViewSet):
    """
    Admin CRUD for users.

    GET    /api/v1/admin/users/          — list all users (search, filter)
    GET    /api/v1/admin/users/{id}/     — retrieve single user
    PATCH  /api/v1/admin/users/{id}/     — update is_active / is_staff / is_verified
    DELETE /api/v1/admin/users/{id}/     — deactivate user (soft)
    POST   /api/v1/admin/users/{id}/make-staff/    — grant staff access
    POST   /api/v1/admin/users/{id}/revoke-staff/  — revoke staff access
    """
    permission_classes = [IsStaffUser]
    pagination_class = AdminPagination

    def list(self, request):
        qs = User.objects.order_by('-date_joined') if hasattr(User, 'date_joined') else User.objects.order_by('-created_at')

        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(email__icontains=q) |
                Q(username__icontains=q)
            )

        is_staff = request.query_params.get('is_staff')
        if is_staff is not None:
            qs = qs.filter(is_staff=is_staff.lower() == 'true')

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(AdminUserSerializer(page, many=True).data)
        return Response({'success': True, 'data': AdminUserSerializer(qs, many=True).data})

    def retrieve(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': AdminUserSerializer(user).data})

    def partial_update(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'data': AdminUserSerializer(user).data})

    def destroy(self, request, pk=None):
        """Soft-deactivate a user (sets is_active=False)."""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if user == request.user:
            return Response(
                {'success': False, 'error': 'You cannot deactivate your own account'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'success': True, 'message': 'User deactivated'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='make-staff')
    def make_staff(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        return Response({'success': True, 'message': f'{user.email} granted staff access'})

    @action(detail=True, methods=['post'], url_path='revoke-staff')
    def revoke_staff(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        if user == request.user:
            return Response(
                {'success': False, 'error': 'You cannot revoke your own staff access'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_staff = False
        user.save(update_fields=['is_staff'])
        return Response({'success': True, 'message': f'{user.email} staff access revoked'})


# ─────────────────────────── Merchants ───────────────────────────

class AdminMerchantViewSet(ViewSet):
    """
    Admin CRUD for merchants.

    GET    /api/v1/admin/merchants/              — list all merchants
    GET    /api/v1/admin/merchants/{id}/         — retrieve single merchant
    PATCH  /api/v1/admin/merchants/{id}/         — update fields (verified, status, featured …)
    DELETE /api/v1/admin/merchants/{id}/         — soft delete merchant
    POST   /api/v1/admin/merchants/{id}/verify/  — verify merchant
    POST   /api/v1/admin/merchants/{id}/suspend/ — suspend merchant
    POST   /api/v1/admin/merchants/{id}/ban/     — ban merchant
    """
    permission_classes = [IsStaffUser]
    pagination_class = AdminPagination

    def _get_base_qs(self):
        return Merchant.objects.select_related('user').order_by('-created_at')

    def list(self, request):
        qs = self._get_base_qs()

        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(display_name__icontains=q) |
                Q(business_name__icontains=q) |
                Q(user__email__icontains=q)
            )

        verified = request.query_params.get('verified')
        if verified is not None:
            qs = qs.filter(verified=verified.lower() == 'true')

        merchant_status = request.query_params.get('status', '').strip().upper()
        if merchant_status:
            qs = qs.filter(status=merchant_status)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(AdminMerchantSerializer(page, many=True).data)
        return Response({'success': True, 'data': AdminMerchantSerializer(qs, many=True).data})

    def retrieve(self, request, pk=None):
        try:
            merchant = self._get_base_qs().get(pk=pk)
        except Merchant.DoesNotExist:
            return Response({'success': False, 'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': AdminMerchantSerializer(merchant).data})

    def partial_update(self, request, pk=None):
        try:
            merchant = Merchant.objects.get(pk=pk)
        except Merchant.DoesNotExist:
            return Response({'success': False, 'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminMerchantUpdateSerializer(merchant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'data': AdminMerchantSerializer(merchant).data})

    def destroy(self, request, pk=None):
        try:
            merchant = Merchant.objects.get(pk=pk)
        except Merchant.DoesNotExist:
            return Response({'success': False, 'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)
        merchant.soft_delete()
        return Response({'success': True, 'message': 'Merchant deleted'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        try:
            merchant = Merchant.objects.get(pk=pk)
        except Merchant.DoesNotExist:
            return Response({'success': False, 'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)
        merchant.verified = True
        merchant.verification_date = timezone.now()
        merchant.save(update_fields=['verified', 'verification_date', 'updated_at'])
        analytics.merchant_verified(merchant)
        return Response({'success': True, 'message': 'Merchant verified', 'data': AdminMerchantSerializer(merchant).data})

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        try:
            merchant = Merchant.objects.get(pk=pk)
        except Merchant.DoesNotExist:
            return Response({'success': False, 'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)
        merchant.status = 'SUSPENDED'
        merchant.save(update_fields=['status', 'updated_at'])
        return Response({'success': True, 'message': 'Merchant suspended', 'data': AdminMerchantSerializer(merchant).data})

    @action(detail=True, methods=['post'])
    def ban(self, request, pk=None):
        try:
            merchant = Merchant.objects.get(pk=pk)
        except Merchant.DoesNotExist:
            return Response({'success': False, 'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)
        merchant.status = 'BANNED'
        merchant.save(update_fields=['status', 'updated_at'])
        return Response({'success': True, 'message': 'Merchant banned', 'data': AdminMerchantSerializer(merchant).data})


# ─────────────────────────── Listings ───────────────────────────

class AdminListingViewSet(ViewSet):
    """
    Admin CRUD for listings.

    GET    /api/v1/admin/listings/               — list ALL listings (any status)
    GET    /api/v1/admin/listings/{id}/          — retrieve single listing
    PATCH  /api/v1/admin/listings/{id}/          — update fields
    DELETE /api/v1/admin/listings/{id}/          — soft delete
    POST   /api/v1/admin/listings/{id}/approve/  — set status=ACTIVE + is_verified=True
    POST   /api/v1/admin/listings/{id}/reject/   — set status=REJECTED
    POST   /api/v1/admin/listings/{id}/feature/  — toggle is_featured
    """
    permission_classes = [IsStaffUser]
    pagination_class = AdminPagination

    def _get_base_qs(self):
        return Listing.objects.select_related(
            'merchant', 'category'
        ).filter(deleted_at__isnull=True).order_by('-created_at')

    def list(self, request):
        qs = self._get_base_qs()

        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(merchant__display_name__icontains=q)
            )

        listing_status = request.query_params.get('status', '').strip().upper()
        if listing_status:
            qs = qs.filter(status=listing_status)

        merchant_id = request.query_params.get('merchant_id', '').strip()
        if merchant_id:
            qs = qs.filter(merchant_id=merchant_id)

        category_id = request.query_params.get('category_id', '').strip()
        if category_id:
            qs = qs.filter(category_id=category_id)

        is_verified = request.query_params.get('is_verified')
        if is_verified is not None:
            qs = qs.filter(is_verified=is_verified.lower() == 'true')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(AdminListingSerializer(page, many=True).data)
        return Response({'success': True, 'data': AdminListingSerializer(qs, many=True).data})

    def retrieve(self, request, pk=None):
        try:
            listing = self._get_base_qs().get(pk=pk)
        except Listing.DoesNotExist:
            return Response({'success': False, 'error': 'Listing not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': AdminListingSerializer(listing).data})

    def partial_update(self, request, pk=None):
        try:
            listing = Listing.objects.get(pk=pk, deleted_at__isnull=True)
        except Listing.DoesNotExist:
            return Response({'success': False, 'error': 'Listing not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminListingUpdateSerializer(listing, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'data': AdminListingSerializer(listing).data})

    def destroy(self, request, pk=None):
        try:
            listing = Listing.objects.get(pk=pk, deleted_at__isnull=True)
        except Listing.DoesNotExist:
            return Response({'success': False, 'error': 'Listing not found'}, status=status.HTTP_404_NOT_FOUND)
        listing.deleted_at = timezone.now()
        listing.save(update_fields=['deleted_at'])
        return Response({'success': True, 'message': 'Listing deleted'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        try:
            listing = Listing.objects.get(pk=pk, deleted_at__isnull=True)
        except Listing.DoesNotExist:
            return Response({'success': False, 'error': 'Listing not found'}, status=status.HTTP_404_NOT_FOUND)
        listing.status = 'ACTIVE'
        listing.is_verified = True
        listing.save(update_fields=['status', 'is_verified', 'updated_at'])
        analytics.listing_approved(listing)
        return Response({'success': True, 'message': 'Listing approved', 'data': AdminListingSerializer(listing).data})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        try:
            listing = Listing.objects.get(pk=pk, deleted_at__isnull=True)
        except Listing.DoesNotExist:
            return Response({'success': False, 'error': 'Listing not found'}, status=status.HTTP_404_NOT_FOUND)
        reason = request.data.get('reason', '').strip()
        listing.status = 'REJECTED'
        listing.is_verified = False
        listing.save(update_fields=['status', 'is_verified', 'updated_at'])
        return Response({
            'success': True,
            'message': 'Listing rejected',
            'reason': reason,
            'data': AdminListingSerializer(listing).data,
        })

    @action(detail=True, methods=['post'])
    def feature(self, request, pk=None):
        try:
            listing = Listing.objects.get(pk=pk, deleted_at__isnull=True)
        except Listing.DoesNotExist:
            return Response({'success': False, 'error': 'Listing not found'}, status=status.HTTP_404_NOT_FOUND)
        listing.is_featured = not listing.is_featured
        listing.save(update_fields=['is_featured', 'updated_at'])
        state = 'featured' if listing.is_featured else 'unfeatured'
        return Response({'success': True, 'message': f'Listing {state}', 'data': AdminListingSerializer(listing).data})


# ─────────────────────────── Categories ───────────────────────────

class AdminCategoryViewSet(ViewSet):
    """
    Admin CRUD for categories.

    GET    /api/v1/admin/categories/         — list all categories (including inactive)
    GET    /api/v1/admin/categories/{id}/    — retrieve single category
    POST   /api/v1/admin/categories/         — create category
    PATCH  /api/v1/admin/categories/{id}/    — update category
    DELETE /api/v1/admin/categories/{id}/    — delete category
    POST   /api/v1/admin/categories/{id}/toggle-active/ — activate / deactivate
    """
    permission_classes = [IsStaffUser]
    pagination_class = AdminPagination

    def _get_base_qs(self):
        return Category.objects.select_related('parent').annotate(
            listings_count=Count('listings', filter=Q(listings__deleted_at__isnull=True))
        ).order_by('sort_order', 'name')

    def list(self, request):
        qs = self._get_base_qs()

        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        parent_only = request.query_params.get('parent_only')
        if parent_only and parent_only.lower() == 'true':
            qs = qs.filter(parent=None)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(AdminCategorySerializer(page, many=True).data)
        return Response({'success': True, 'data': AdminCategorySerializer(qs, many=True).data})

    def retrieve(self, request, pk=None):
        try:
            category = self._get_base_qs().get(pk=pk)
        except Category.DoesNotExist:
            return Response({'success': False, 'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': AdminCategorySerializer(category).data})

    def create(self, request):
        serializer = AdminCategoryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        return Response(
            {'success': True, 'data': AdminCategorySerializer(category).data},
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, pk=None):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({'success': False, 'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminCategoryUpdateSerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'data': AdminCategorySerializer(category).data})

    def destroy(self, request, pk=None):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({'success': False, 'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

        if category.children.exists():
            return Response(
                {'success': False, 'error': 'Cannot delete a category that has subcategories'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if category.listings.filter(deleted_at__isnull=True).exists():
            return Response(
                {'success': False, 'error': 'Cannot delete a category that has active listings'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        category.delete()
        return Response({'success': True, 'message': 'Category deleted'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({'success': False, 'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
        category.is_active = not category.is_active
        category.save(update_fields=['is_active'])
        state = 'activated' if category.is_active else 'deactivated'
        return Response({'success': True, 'message': f'Category {state}', 'data': AdminCategorySerializer(category).data})


# ─────────────────────────── Orders ───────────────────────────

class AdminOrderViewSet(ViewSet):
    """
    Admin view of all orders (all buyers + all merchants).

    GET   /api/v1/admin/orders/                        — list all orders
    GET   /api/v1/admin/orders/{id}/                   — retrieve single order
    PATCH /api/v1/admin/orders/{id}/                   — update status / notes
    POST  /api/v1/admin/orders/{id}/update-status/     — convenience status-change endpoint
    """
    permission_classes = [IsStaffUser]
    pagination_class = AdminPagination

    def _get_base_qs(self):
        return OrderIntent.objects.select_related(
            'buyer', 'merchant', 'address', 'order_group'
        ).prefetch_related(
            'items__listing'
        ).order_by('-created_at')

    def list(self, request):
        qs = self._get_base_qs()

        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(order_number__icontains=q) |
                Q(buyer__name__icontains=q) |
                Q(buyer__email__icontains=q) |
                Q(merchant__display_name__icontains=q)
            )

        order_status = request.query_params.get('status', '').strip().upper()
        if order_status:
            qs = qs.filter(status=order_status)

        merchant_id = request.query_params.get('merchant_id', '').strip()
        if merchant_id:
            qs = qs.filter(merchant_id=merchant_id)

        buyer_id = request.query_params.get('buyer_id', '').strip()
        if buyer_id:
            qs = qs.filter(buyer_id=buyer_id)

        date_from = request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(AdminOrderSerializer(page, many=True).data)
        return Response({'success': True, 'data': AdminOrderSerializer(qs, many=True).data})

    def retrieve(self, request, pk=None):
        try:
            order = self._get_base_qs().get(pk=pk)
        except OrderIntent.DoesNotExist:
            return Response({'success': False, 'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': AdminOrderSerializer(order).data})

    def partial_update(self, request, pk=None):
        try:
            order = OrderIntent.objects.get(pk=pk)
        except OrderIntent.DoesNotExist:
            return Response({'success': False, 'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminOrderUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'data': AdminOrderSerializer(order).data})

    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        try:
            order = OrderIntent.objects.get(pk=pk)
        except OrderIntent.DoesNotExist:
            return Response({'success': False, 'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status', '').strip().upper()
        valid_statuses = ['NEW', 'CONTACTED', 'CONFIRMED', 'COMPLETED', 'CANCELLED']
        if new_status not in valid_statuses:
            return Response(
                {'success': False, 'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = new_status
        notes = request.data.get('notes', '').strip()
        if notes:
            order.notes = notes
        order.save()
        return Response({
            'success': True,
            'message': f'Order status updated to {new_status}',
            'data': AdminOrderSerializer(order).data,
        })


# ─────────────────────────── Images ───────────────────────────

class AdminImageViewSet(ViewSet):
    """
    Admin read / delete access for all image assets.

    GET    /api/v1/admin/images/          — list all confirmed images
    GET    /api/v1/admin/images/{id}/     — retrieve single image
    DELETE /api/v1/admin/images/{id}/     — delete image record
    GET    /api/v1/admin/images/orphans/  — images with no object_id (dangling drafts)
    POST   /api/v1/admin/images/cleanup-orphans/ — delete orphan images older than 24 h
    """
    permission_classes = [IsStaffUser]
    pagination_class = AdminPagination

    def list(self, request):
        qs = ImageAsset.objects.select_related('owner').filter(
            is_confirmed=True
        ).order_by('-created_at')

        image_type = request.query_params.get('image_type', '').strip()
        if image_type:
            qs = qs.filter(image_type=image_type)

        owner_id = request.query_params.get('owner_id', '').strip()
        if owner_id:
            qs = qs.filter(owner_id=owner_id)

        object_id = request.query_params.get('object_id', '').strip()
        if object_id:
            qs = qs.filter(object_id=object_id)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(AdminImageAssetSerializer(page, many=True).data)
        return Response({'success': True, 'data': AdminImageAssetSerializer(qs, many=True).data})

    def retrieve(self, request, pk=None):
        try:
            asset = ImageAsset.objects.select_related('owner').get(pk=pk)
        except ImageAsset.DoesNotExist:
            return Response({'success': False, 'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': AdminImageAssetSerializer(asset).data})

    def destroy(self, request, pk=None):
        try:
            asset = ImageAsset.objects.get(pk=pk)
        except ImageAsset.DoesNotExist:
            return Response({'success': False, 'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        asset.delete()
        return Response({'success': True, 'message': 'Image deleted'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def orphans(self, request):
        """List confirmed images with no object_id (draft / abandoned uploads)."""
        qs = ImageAsset.objects.filter(
            is_confirmed=True,
            object_id__isnull=True,
        ).select_related('owner').order_by('-created_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(AdminImageAssetSerializer(page, many=True).data)
        return Response({'success': True, 'count': qs.count(), 'data': AdminImageAssetSerializer(qs, many=True).data})

    @action(detail=False, methods=['post'], url_path='cleanup-orphans')
    def cleanup_orphans(self, request):
        """Delete orphan images older than 24 hours."""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=24)
        abandoned = ImageAsset.objects.filter(
            is_confirmed=True,
            object_id__isnull=True,
            created_at__lt=cutoff,
        )
        count = abandoned.count()
        abandoned.delete()
        return Response({'success': True, 'message': f'Deleted {count} orphan image(s)'})


class AdminBroadcastCampaignViewSet(ViewSet):
    """
    Staff-only scheduled broadcasts.

    GET  /api/v1/admin/broadcasts/                 - list campaigns
    GET  /api/v1/admin/broadcasts/{id}/            - retrieve campaign
    POST /api/v1/admin/broadcasts/                 - schedule email or push
    POST /api/v1/admin/broadcasts/schedule-email/  - schedule email to all active users
    POST /api/v1/admin/broadcasts/schedule-push/   - schedule push to all active users with push tokens
    POST /api/v1/admin/broadcasts/{id}/cancel/     - cancel a scheduled campaign
    """

    permission_classes = [IsStaffUser]
    pagination_class = AdminPagination

    def _get_queryset(self):
        return BroadcastNotificationCampaign.objects.select_related('created_by').order_by(
            '-scheduled_at', '-created_at'
        )

    def _eligible_count(self, channel):
        if channel == 'EMAIL':
            return User.objects.filter(is_active=True).exclude(email__isnull=True).exclude(email='').count()
        if channel == 'PUSH':
            return User.objects.filter(is_active=True, push_tokens__is_active=True).distinct().count()
        return 0

    def _schedule_campaign(self, campaign):
        task = send_broadcast_campaign.apply_async(
            args=[str(campaign.id)],
            eta=campaign.scheduled_at,
        )
        campaign.celery_task_id = task.id
        campaign.target_count = self._eligible_count(campaign.channel)
        campaign.save(update_fields=['celery_task_id', 'target_count', 'updated_at'])
        return campaign

    def list(self, request):
        qs = self._get_queryset()

        channel = request.query_params.get('channel', '').strip().upper()
        if channel:
            qs = qs.filter(channel=channel)

        campaign_status = request.query_params.get('status', '').strip().upper()
        if campaign_status:
            qs = qs.filter(status=campaign_status)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(AdminBroadcastCampaignSerializer(page, many=True).data)
        return Response({'success': True, 'data': AdminBroadcastCampaignSerializer(qs, many=True).data})

    def retrieve(self, request, pk=None):
        try:
            campaign = self._get_queryset().get(pk=pk)
        except BroadcastNotificationCampaign.DoesNotExist:
            return Response({'success': False, 'error': 'Broadcast campaign not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': AdminBroadcastCampaignSerializer(campaign).data})

    def create(self, request):
        serializer = AdminBroadcastCampaignCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = serializer.save(created_by=request.user)
        campaign = self._schedule_campaign(campaign)
        return Response(
            {
                'success': True,
                'message': f'{campaign.get_channel_display()} broadcast scheduled',
                'data': AdminBroadcastCampaignSerializer(campaign).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='schedule-email')
    def schedule_email(self, request):
        data = request.data.copy()
        data['channel'] = 'EMAIL'
        serializer = AdminBroadcastCampaignCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        campaign = serializer.save(created_by=request.user)
        campaign = self._schedule_campaign(campaign)
        return Response(
            {
                'success': True,
                'message': 'Email broadcast scheduled',
                'data': AdminBroadcastCampaignSerializer(campaign).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='schedule-push')
    def schedule_push(self, request):
        data = request.data.copy()
        data['channel'] = 'PUSH'
        serializer = AdminBroadcastCampaignCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        campaign = serializer.save(created_by=request.user)
        campaign = self._schedule_campaign(campaign)
        return Response(
            {
                'success': True,
                'message': 'Push broadcast scheduled',
                'data': AdminBroadcastCampaignSerializer(campaign).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        try:
            campaign = BroadcastNotificationCampaign.objects.get(pk=pk)
        except BroadcastNotificationCampaign.DoesNotExist:
            return Response({'success': False, 'error': 'Broadcast campaign not found'}, status=status.HTTP_404_NOT_FOUND)

        if campaign.status != 'SCHEDULED':
            return Response(
                {'success': False, 'error': f'Cannot cancel a campaign with status {campaign.status}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if campaign.celery_task_id:
            current_app.control.revoke(campaign.celery_task_id)

        campaign.status = 'CANCELLED'
        campaign.save(update_fields=['status', 'updated_at'])
        return Response({
            'success': True,
            'message': 'Broadcast campaign cancelled',
            'data': AdminBroadcastCampaignSerializer(campaign).data,
        })
