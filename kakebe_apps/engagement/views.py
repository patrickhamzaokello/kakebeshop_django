# kakebe_apps/interactions/views.py

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models, transaction

from .models import (
    SavedSearch, Conversation, Message,
    ListingReview, MerchantReview, Report, MerchantScore,
    ActivityLog, AuditLog, ApiUsage, OnboardingStatus, UserIntent, PushToken,
    ListingComment,
)
from .serializers import (
    SavedSearchSerializer, ConversationSerializer,
    MessageSerializer, ListingReviewSerializer,
    MerchantReviewSerializer, ReportSerializer, MerchantScoreSerializer,
    ActivityLogSerializer, AuditLogSerializer, ApiUsageSerializer, OnboardingStatusSerializer, UserIntentSerializer,
    PushTokenSerializer, PushTokenCreateSerializer, PushTokenUpdateUsageSerializer,
    ListingCommentSerializer, ListingCommentCreateSerializer,
    ListingCommentUpdateSerializer, ListingCommentReplySerializer,
    StartConversationSerializer, SendMessageSerializer,
)

from django.db.models import Q, Value, CharField, F, Case, When, IntegerField
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from kakebe_apps.listings.models import Listing
from kakebe_apps.merchants.models import Merchant
from kakebe_apps.orders.models import OrderIntent
from kakebe_apps.analytics import events as analytics
from kakebe_apps.notifications.models import NotificationType
from kakebe_apps.notifications.services import NotificationService



class SavedSearchViewSet(viewsets.ModelViewSet):
    serializer_class = SavedSearchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects
            .filter(models.Q(buyer=user) | models.Q(seller=user))
            .select_related(
                'buyer',
                'seller',
                'listing',
                'listing__merchant',
                'listing__merchant__user',
                'order_intent',
            )
            .prefetch_related('messages')
            .order_by(models.F('last_message_at').desc(nulls_last=True), '-created_at')
        )

    def get_serializer_class(self):
        if self.action == 'start':
            return StartConversationSerializer
        return ConversationSerializer

    def _resolve_chat_target(self, request, serializer):
        merchant = None
        listing = None
        order_intent = None

        listing_id = serializer.validated_data.get('listing_id')
        merchant_id = serializer.validated_data.get('merchant_id')
        order_intent_id = serializer.validated_data.get('order_intent_id')

        if order_intent_id:
            order_intent = get_object_or_404(
                OrderIntent.objects.select_related('merchant', 'merchant__user'),
                id=order_intent_id,
                buyer=request.user,
            )
            merchant = order_intent.merchant

        if listing_id:
            listing = get_object_or_404(
                Listing.objects.select_related('merchant', 'merchant__user'),
                id=listing_id,
                deleted_at__isnull=True,
            )
            if merchant and merchant.id != listing.merchant_id:
                raise ValueError("listing_id does not match the order merchant.")
            merchant = listing.merchant

        if merchant_id:
            requested_merchant = get_object_or_404(
                Merchant.objects.select_related('user'),
                id=merchant_id,
                deleted_at__isnull=True,
            )
            if merchant and merchant.id != requested_merchant.id:
                raise ValueError("merchant_id does not match the listing or order merchant.")
            merchant = requested_merchant

        if not merchant:
            raise ValueError("A valid merchant could not be resolved.")
        if merchant.user_id == request.user.id:
            raise ValueError("You cannot start a conversation with your own merchant profile.")
        if merchant.status != 'ACTIVE':
            raise ValueError("This merchant is not available for chat.")

        return merchant, listing, order_intent

    def _create_message_notification(self, conversation, message):
        recipient = conversation.seller if message.sender_id == conversation.buyer_id else conversation.buyer
        merchant = conversation.listing.merchant if conversation.listing_id else None
        if not merchant and hasattr(conversation.seller, 'merchant_profile'):
            merchant = conversation.seller.merchant_profile

        snippet = message.message[:120] if message.message else 'Sent an attachment'
        sender_name = message.sender.name or message.sender.email
        store_name = None
        if merchant:
            store_name = merchant.display_name or merchant.business_name

        NotificationService.create_notification(
            user=recipient,
            notification_type=NotificationType.CHAT_MESSAGE,
            title=f'New message from {sender_name}',
            message=snippet,
            merchant_id=merchant.id if merchant else None,
            listing_id=conversation.listing_id,
            metadata={
                'conversation_id': str(conversation.id),
                'message_id': str(message.id),
                'sender_id': str(message.sender_id),
                'sender_name': sender_name,
                'sender_profile_image': message.sender.profile_image,
                'merchant_id': str(merchant.id) if merchant else None,
                'merchant_store_name': store_name,
                'merchant_profile_picture': (merchant.logo or merchant.cover_image) if merchant else None,
                'listing_title': conversation.listing.title if conversation.listing_id else None,
                'order_intent_id': str(conversation.order_intent_id) if conversation.order_intent_id else None,
            },
        )

    @action(detail=False, methods=['post'], url_path='start')
    def start(self, request):
        """
        Buyer starts or resumes a conversation with a merchant.

        Body accepts merchant_id, listing_id, or order_intent_id plus
        message/attachment. The first message is queued for notification
        delivery to the merchant.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            merchant, listing, order_intent = self._resolve_chat_target(request, serializer)
        except ValueError as exc:
            return Response({'success': False, 'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            conversation = (
                Conversation.objects
                .filter(
                    buyer=request.user,
                    seller=merchant.user,
                    listing=listing,
                    order_intent=order_intent,
                    status='ACTIVE',
                )
                .first()
            )
            created = False
            if conversation is None:
                conversation = Conversation.objects.create(
                    buyer=request.user,
                    seller=merchant.user,
                    listing=listing,
                    order_intent=order_intent,
                )
                created = True

            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                message=serializer.validated_data.get('message', '').strip(),
                attachment=serializer.validated_data.get('attachment') or None,
            )
            conversation.last_message_at = message.sent_at
            conversation.save(update_fields=['last_message_at', 'updated_at'])
            transaction.on_commit(lambda: self._create_message_notification(conversation, message))

        analytics.conversation_started(request.user.id, conversation, message)
        analytics.message_sent(request.user.id, conversation, message)

        read_serializer = ConversationSerializer(conversation, context=self.get_serializer_context())
        message_serializer = MessageSerializer(message, context=self.get_serializer_context())
        return Response({
            'success': True,
            'created': created,
            'conversation': read_serializer.data,
            'message': message_serializer.data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk=None):
        """List messages or send a new message in a conversation."""
        conversation = self.get_object()

        if request.method == 'POST':
            if conversation.status != 'ACTIVE':
                return Response(
                    {'success': False, 'error': 'This conversation is not active.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = SendMessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                message = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    message=serializer.validated_data.get('message', ''),
                    attachment=serializer.validated_data.get('attachment') or None,
                )
                conversation.last_message_at = message.sent_at
                conversation.save(update_fields=['last_message_at', 'updated_at'])
                transaction.on_commit(lambda: self._create_message_notification(conversation, message))

            analytics.message_sent(request.user.id, conversation, message)
            read_serializer = MessageSerializer(message, context=self.get_serializer_context())
            return Response({'success': True, 'message': read_serializer.data}, status=status.HTTP_201_CREATED)

        queryset = conversation.messages.select_related('sender').order_by('sent_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MessageSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)
        serializer = MessageSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Mark all messages from the other participant as read."""
        conversation = self.get_object()
        updated = conversation.messages.filter(
            is_read=False,
        ).exclude(sender=request.user).update(
            is_read=True,
            read_at=timezone.now(),
        )
        analytics.messages_marked_read(request.user.id, conversation, updated)
        return Response({'success': True, 'marked_read': updated})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """Total unread chat messages for the authenticated user."""
        count = Message.objects.filter(
            models.Q(conversation__buyer=request.user) | models.Q(conversation__seller=request.user),
            is_read=False,
        ).exclude(sender=request.user).count()
        return Response({'unread_count': count})


class MessageViewSet(mixins.CreateModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation = get_object_or_404(
            Conversation.objects.filter(
                models.Q(buyer=self.request.user) | models.Q(seller=self.request.user)
            ),
            id=self.kwargs['conversation_pk'],
        )
        return conversation.messages.select_related('sender').order_by('sent_at')

    def perform_create(self, serializer):
        conversation = get_object_or_404(
            Conversation.objects.filter(
                models.Q(buyer=self.request.user) | models.Q(seller=self.request.user)
            ),
            id=self.kwargs['conversation_pk'],
        )
        message = serializer.save(sender=self.request.user, conversation=conversation)
        conversation.last_message_at = message.sent_at
        conversation.save(update_fields=['last_message_at', 'updated_at'])
        ConversationViewSet()._create_message_notification(conversation, message)
        analytics.message_sent(self.request.user.id, conversation, message)



class ListingReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ListingReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ListingReview.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MerchantReviewViewSet(viewsets.ModelViewSet):
    serializer_class = MerchantReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MerchantReview.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReportViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class MerchantScoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MerchantScore.objects.all()
    serializer_class = MerchantScoreSerializer
    permission_classes = [IsAuthenticated]  # Or public if needed


# Admin-only logs
class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminUser]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]


class ApiUsageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ApiUsage.objects.all()
    serializer_class = ApiUsageSerializer
    permission_classes = [IsAdminUser]


class UserIntentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user intent

    list: Get user's current intent
    create: Set or update user's intent
    retrieve: Get user's intent by ID
    update: Update user's intent
    destroy: Delete user's intent
    """

    serializer_class = UserIntentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only the current user's intent"""
        return UserIntent.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """Get current user's intent"""
        try:
            intent = UserIntent.objects.get(user=request.user)
            serializer = self.get_serializer(intent)
            return Response({
                'success': True,
                'intent': serializer.data
            }, status=status.HTTP_200_OK)
        except UserIntent.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No intent set for this user',
                'intent': None
            }, status=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        """Create or update user's intent"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        intent = serializer.save()

        analytics.marketplace_intent_set(request.user.id, intent.intent)

        return Response({
            'success': True,
            'message': 'Intent saved successfully',
            'intent': serializer.data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Update user's intent"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'success': True,
            'message': 'Intent updated successfully',
            'intent': serializer.data
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Delete user's intent"""
        instance = self.get_object()
        self.perform_destroy(instance)

        # Update onboarding status
        try:
            onboarding = OnboardingStatus.objects.get(user=request.user)
            onboarding.intent_completed = False
            onboarding.check_completion()
        except OnboardingStatus.DoesNotExist:
            pass

        return Response({
            'success': True,
            'message': 'Intent deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def my_intent(self, request):
        """Get current user's intent - convenient endpoint"""
        return self.list(request)


class OnboardingStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing onboarding status

    list: Get user's onboarding status
    retrieve: Get onboarding status by ID
    """

    serializer_class = OnboardingStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only the current user's onboarding status"""
        return OnboardingStatus.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """Get current user's onboarding status"""
        onboarding, created = OnboardingStatus.objects.get_or_create(
            user=request.user
        )
        serializer = self.get_serializer(onboarding)
        return Response({
            'success': True,
            'onboarding_status': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def complete_step(self, request):
        """Mark a specific onboarding step as complete"""
        step = request.data.get('step')
        valid_steps = ['intent', 'categories', 'profile']

        if step not in valid_steps:
            return Response({
                'success': False,
                'message': f'Invalid step. Must be one of: {", ".join(valid_steps)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        onboarding, _ = OnboardingStatus.objects.get_or_create(user=request.user)

        if step == 'intent':
            onboarding.intent_completed = True
        elif step == 'categories':
            onboarding.categories_completed = True
        elif step == 'profile':
            onboarding.profile_completed = True

        onboarding.check_completion()

        analytics.onboarding_step_completed(
            request.user.id, step=step, all_complete=onboarding.is_onboarding_complete
        )

        serializer = self.get_serializer(onboarding)
        return Response({
            'success': True,
            'message': f'{step.capitalize()} step completed',
            'onboarding_status': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def my_status(self, request):
        """Get current user's onboarding status - convenient endpoint"""
        return self.list(request)


class PushTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing push tokens.

    list: Get all active push tokens for the authenticated user
    create: Create or update a push token
    retrieve: Get a specific push token by ID
    update: Update a push token
    partial_update: Partially update a push token
    destroy: Deactivate a push token (soft delete)
    """

    serializer_class = PushTokenSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Return only the authenticated user's tokens"""
        return PushToken.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return PushTokenCreateSerializer
        elif self.action == 'update_usage':
            return PushTokenUpdateUsageSerializer
        return PushTokenSerializer

    def list(self, request, *args, **kwargs):
        """
        Get all active push tokens for the authenticated user.

        GET /api/push-tokens/
        """
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'success': True,
            'tokens': serializer.data,
            'count': queryset.count()
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """
        Get or create a push token for the authenticated user.

        POST /api/push-tokens/
        {
            "token": "ExponentPushToken[AQ5CCJA9AMg9mCUx6X_wOH]",
            "device_id": "unique-device-identifier",
            "platform": "ios"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_value = serializer.validated_data['token']
        device_id = serializer.validated_data.get('device_id', '')
        platform = serializer.validated_data.get('platform', '')

        # Try to get existing token
        if device_id:
            # If device_id provided, look for existing token for this user+device
            push_token, created = PushToken.objects.get_or_create(
                user=request.user,
                device_id=device_id,
                defaults={
                    'token': token_value,
                    'platform': platform,
                    'is_active': True,
                    'last_used': timezone.now()
                }
            )

            if not created:
                # Update existing token if it changed
                if push_token.token != token_value:
                    push_token.token = token_value
                    push_token.platform = platform
                    push_token.is_active = True
                push_token.last_used = timezone.now()
                push_token.save()
        else:
            # No device_id provided, check if token already exists for this user
            try:
                push_token = PushToken.objects.get(user=request.user, token=token_value)
                push_token.last_used = timezone.now()
                push_token.is_active = True
                if platform:
                    push_token.platform = platform
                push_token.save()
                created = False
            except PushToken.DoesNotExist:
                push_token = PushToken.objects.create(
                    user=request.user,
                    token=token_value,
                    device_id=device_id,
                    platform=platform,
                    is_active=True,
                    last_used=timezone.now()
                )
                created = True

        response_serializer = PushTokenSerializer(push_token)
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return Response({
            'success': True,
            'token': response_serializer.data,
            'created': created,
            'message': 'Token created successfully' if created else 'Token updated successfully'
        }, status=response_status)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific push token.

        GET /api/push-tokens/{id}/
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response({
            'success': True,
            'token': serializer.data
        }, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """
        Update a push token and refresh last_used timestamp.

        PUT /api/push-tokens/{id}/
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Update last_used timestamp
        instance.last_used = timezone.now()
        self.perform_update(serializer)

        return Response({
            'success': True,
            'message': 'Token updated successfully',
            'token': serializer.data
        }, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a push token.

        PATCH /api/push-tokens/{id}/
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Deactivate a push token (soft delete).

        DELETE /api/push-tokens/{id}/
        """
        instance = self.get_object()
        instance.is_active = False
        instance.save()

        return Response({
            'success': True,
            'message': 'Token deactivated successfully'
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get all active tokens (alias for list).

        GET /api/push-tokens/active/
        """
        return self.list(request)

    @action(detail=False, methods=['delete'])
    def deactivate_by_value(self, request):
        """
        Deactivate a push token by token value.

        DELETE /api/push-tokens/deactivate-by-value/
        {
            "token": "ExponentPushToken[AQ5CCJA9AMg9mCUx6X_wOH]"
        }
        """
        token_value = request.data.get('token')
        if not token_value:
            return Response({
                'success': False,
                'error': 'Token value required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            push_token = PushToken.objects.get(
                token=token_value,
                user=request.user
            )
            push_token.is_active = False
            push_token.save()

            return Response({
                'success': True,
                'message': 'Token deactivated successfully'
            }, status=status.HTTP_200_OK)

        except PushToken.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Token not found'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def update_usage(self, request):
        """
        Update last_used timestamp for a token.

        POST /api/push-tokens/update-usage/
        {
            "token": "ExponentPushToken[AQ5CCJA9AMg9mCUx6X_wOH]"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_value = serializer.validated_data['token']

        try:
            push_token = PushToken.objects.get(
                token=token_value,
                user=request.user,
                is_active=True
            )
            push_token.last_used = timezone.now()
            push_token.save()

            return Response({
                'success': True,
                'message': 'Token usage updated successfully',
                'last_used': push_token.last_used
            }, status=status.HTTP_200_OK)

        except PushToken.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Active token not found'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def bulk_deactivate(self, request):
        """
        Deactivate multiple tokens at once.

        POST /api/push-tokens/bulk-deactivate/
        {
            "token_ids": [1, 2, 3]
        }
        OR
        {
            "tokens": ["ExponentPushToken[...]", "ExponentPushToken[...]"]
        }
        """
        token_ids = request.data.get('token_ids', [])
        tokens = request.data.get('tokens', [])

        if not token_ids and not tokens:
            return Response({
                'success': False,
                'error': 'Either token_ids or tokens array required'
            }, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0

        if token_ids:
            updated_count = PushToken.objects.filter(
                id__in=token_ids,
                user=request.user
            ).update(is_active=False)

        if tokens:
            updated_count += PushToken.objects.filter(
                token__in=tokens,
                user=request.user
            ).update(is_active=False)

        return Response({
            'success': True,
            'message': f'{updated_count} tokens deactivated successfully',
            'deactivated_count': updated_count
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'])
    def deactivate_all(self, request):
        """
        Deactivate all tokens for the authenticated user.

        DELETE /api/push-tokens/deactivate-all/
        """
        updated_count = PushToken.objects.filter(
            user=request.user,
            is_active=True
        ).update(is_active=False)

        return Response({
            'success': True,
            'message': f'All tokens deactivated successfully',
            'deactivated_count': updated_count
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reactivate(self, request, id=None):
        """
        Reactivate a previously deactivated token.

        POST /api/push-tokens/{id}/reactivate/
        """
        instance = self.get_object()
        instance.is_active = True
        instance.last_used = timezone.now()
        instance.save()

        serializer = self.get_serializer(instance)

        return Response({
            'success': True,
            'message': 'Token reactivated successfully',
            'token': serializer.data
        }, status=status.HTTP_200_OK)





class CommentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ListingCommentViewSet(viewsets.ModelViewSet):
    """
    Endpoints for listing comments.

    When accessed via /listings/<listing_id>/comments/:
      GET    → paginated top-level comments for that listing
      POST   → post a new comment (or reply when `parent` is supplied)

    When accessed via /listing-comments/<id>/:
      GET    → retrieve a single comment
      PATCH  → edit own comment
      DELETE → soft-delete own comment

    Extra actions:
      GET  /listings/<listing_id>/comments/total/     → total comment count
      GET  /listing-comments/<id>/replies/            → paginated replies for a comment
    """

    permission_classes = [IsAuthenticated]
    pagination_class = CommentPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return ListingCommentCreateSerializer
        if self.action in ('update', 'partial_update'):
            return ListingCommentUpdateSerializer
        if self.action == 'replies':
            return ListingCommentReplySerializer
        return ListingCommentSerializer

    def get_queryset(self):
        listing_id = self.kwargs.get('listing_id')
        if listing_id:
            # Listing-scoped: return only top-level, non-deleted comments
            return (
                ListingComment.objects
                .filter(listing_id=listing_id, parent__isnull=True, is_deleted=False)
                .select_related('user')
                .prefetch_related('replies')
            )
        # Router-scoped (detail endpoints): all non-deleted comments
        return ListingComment.objects.filter(is_deleted=False).select_related('user')

    def perform_create(self, serializer):
        listing_id = self.kwargs.get('listing_id')
        if listing_id:
            listing = get_object_or_404(
                Listing, id=listing_id, status='ACTIVE', deleted_at__isnull=True
            )
            serializer.save(user=self.request.user, listing=listing)
        else:
            serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        read_serializer = ListingCommentSerializer(
            serializer.instance, context=self.get_serializer_context()
        )
        return Response(
            {'success': True, 'comment': read_serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user_id != request.user.id:
            return Response(
                {'error': 'You can only edit your own comments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        read_serializer = ListingCommentSerializer(
            serializer.instance, context=self.get_serializer_context()
        )
        return Response({'success': True, 'comment': read_serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user_id != request.user.id:
            return Response(
                {'error': 'You can only delete your own comments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])
        return Response({'success': True, 'message': 'Comment deleted.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='total')
    def total(self, request, listing_id=None):
        """
        Return the total number of (non-deleted) comments for a listing.
        Accessible at:
          GET /listings/<listing_id>/comments/total/
          GET /listing-comments/total/?listing=<listing_id>
        """
        lid = listing_id or request.query_params.get('listing')
        if not lid:
            return Response(
                {'error': 'A listing ID is required (URL segment or ?listing= param).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        listing = get_object_or_404(Listing, id=lid)
        total = ListingComment.objects.filter(listing=listing, is_deleted=False).count()
        return Response({'listing_id': str(listing.id), 'total_comments': total})

    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None, listing_id=None):
        """
        Return paginated replies for a specific comment.
        GET /listing-comments/<id>/replies/
        """
        comment = self.get_object()
        qs = (
            ListingComment.objects
            .filter(parent=comment, is_deleted=False)
            .select_related('user')
            .order_by('created_at')
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ListingCommentReplySerializer(
                page, many=True, context=self.get_serializer_context()
            )
            return self.get_paginated_response(serializer.data)
        serializer = ListingCommentReplySerializer(
            qs, many=True, context=self.get_serializer_context()
        )
        return Response(serializer.data)


class SearchPagination(PageNumberPagination):
    """Custom pagination for search results"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class EnhancedSearchView(APIView):
    """
    Enhanced search with relevance scoring across merchants and listings.
    Returns active and verified results only.

    Query Parameters:
    - q: search query (required)
    - type: filter by type ('merchant' or 'listing', optional)
    - category: filter listings by category ID (optional)
    - min_price: minimum price for listings (optional)
    - max_price: maximum price for listings (optional)
    - location: filter by location ID (optional)
    - sort: sort order ('relevance', 'newest', 'price_asc', 'price_desc', 'rating')
    - page: page number (default: 1)
    - page_size: results per page (default: 20, max: 100)

    Example: /api/search/?q=coffee&type=listing&category=uuid&sort=relevance&page=1
    """

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        search_type = request.query_params.get('type', '').lower()
        category_id = request.query_params.get('category')
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        location_id = request.query_params.get('location')
        sort_by = request.query_params.get('sort', 'relevance')

        if not query:
            return Response(
                {'error': 'Search query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate search type
        if search_type and search_type not in ['merchant', 'listing']:
            return Response(
                {'error': 'Invalid type. Must be "merchant" or "listing"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate sort parameter
        valid_sorts = ['relevance', 'newest', 'price_asc', 'price_desc', 'rating']
        if sort_by not in valid_sorts:
            return Response(
                {'error': f'Invalid sort. Must be one of: {", ".join(valid_sorts)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Collect results
        results = []

        # Search merchants
        if not search_type or search_type == 'merchant':
            merchant_results = self._search_merchants(query, location_id)
            results.extend(merchant_results)

        # Search listings
        if not search_type or search_type == 'listing':
            listing_results = self._search_listings(
                query,
                category_id,
                min_price,
                max_price,
                location_id
            )
            results.extend(listing_results)

        # Sort results
        results = self._sort_results(results, sort_by)

        if request.user.is_authenticated:
            analytics.search_performed(
                request.user.id,
                query=query,
                results_count=len(results),
                search_type=search_type or 'all',
                filters={
                    'category': category_id,
                    'min_price': min_price,
                    'max_price': max_price,
                    'sort': sort_by,
                },
            )

        # Paginate
        paginator = SearchPagination()
        paginated_results = paginator.paginate_queryset(results, request)

        # Add search metadata
        response_data = {
            'query': query,
            'filters': {
                'type': search_type or 'all',
                'category': category_id,
                'location': location_id,
                'price_range': {
                    'min': min_price,
                    'max': max_price
                } if min_price or max_price else None,
            },
            'sort': sort_by,
        }

        return paginator.get_paginated_response({
            'metadata': response_data,
            'results': paginated_results
        })

    def _search_merchants(self, query, location_id=None):
        """Search for active and verified merchants with relevance scoring"""
        # Build query
        q_filter = Q(
            Q(display_name__icontains=query) |
            Q(business_name__icontains=query) |
            Q(description__icontains=query)
        )

        # Base filters
        merchants = Merchant.objects.filter(
            q_filter,
            status='ACTIVE',
            verified=True,
            deleted_at__isnull=True
        )

        # Location filter
        if location_id:
            merchants = merchants.filter(location_id=location_id)

        # Add relevance scoring
        merchants = merchants.annotate(
            relevance_score=Case(
                # Exact match in display name gets highest score
                When(display_name__iexact=query, then=Value(100)),
                # Display name starts with query
                When(display_name__istartswith=query, then=Value(80)),
                # Business name exact match
                When(business_name__iexact=query, then=Value(90)),
                # Business name starts with query
                When(business_name__istartswith=query, then=Value(70)),
                # Display name contains query
                When(display_name__icontains=query, then=Value(60)),
                # Business name contains query
                When(business_name__icontains=query, then=Value(50)),
                # Description contains query
                When(description__icontains=query, then=Value(30)),
                default=Value(10),
                output_field=IntegerField(),
            )
        ).select_related('location', 'user')

        results = []
        for merchant in merchants:
            results.append({
                'type': 'merchant',
                'id': str(merchant.id),
                'title': merchant.display_name,
                'business_name': merchant.business_name,
                'description': self._truncate_text(merchant.description, 200),
                'logo': merchant.logo,
                'cover_image': merchant.cover_image,
                'rating': float(merchant.rating),
                'total_reviews': merchant.total_reviews,
                'verified': merchant.verified,
                'featured': merchant.featured,
                'location': {
                    'id': str(merchant.location.id) if merchant.location else None,
                    'name': merchant.location.area if merchant.location else None,
                } if merchant.location else None,
                'created_at': merchant.created_at.isoformat(),
                'relevance_score': merchant.relevance_score,
            })

        return results

    def _search_listings(self, query, category_id=None, min_price=None,
                         max_price=None, location_id=None):
        """Search for active and verified listings with relevance scoring"""
        # Build query
        q_filter = Q(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__name__icontains=query)
        )

        # Base filters
        listings = Listing.objects.filter(
            q_filter,
            status='ACTIVE',
            is_verified=True,
            deleted_at__isnull=True
        )

        # Category filter
        if category_id:
            listings = listings.filter(category_id=category_id)

        # Price filters
        if min_price:
            try:
                min_price = float(min_price)
                listings = listings.filter(
                    Q(price__gte=min_price) |
                    Q(price_min__gte=min_price)
                )
            except (ValueError, TypeError):
                pass

        if max_price:
            try:
                max_price = float(max_price)
                listings = listings.filter(
                    Q(price__lte=max_price) |
                    Q(price_max__lte=max_price)
                )
            except (ValueError, TypeError):
                pass

        # Location filter (through merchant)
        if location_id:
            listings = listings.filter(merchant__location_id=location_id)

        # Add relevance scoring
        listings = listings.annotate(
            relevance_score=Case(
                # Exact title match
                When(title__iexact=query, then=Value(100)),
                # Title starts with query
                When(title__istartswith=query, then=Value(80)),
                # Title contains query
                When(title__icontains=query, then=Value(60)),
                # Description contains query
                When(description__icontains=query, then=Value(40)),
                # Tag matches
                When(tags__name__icontains=query, then=Value(50)),
                default=Value(10),
                output_field=IntegerField(),
            )
        ).select_related(
            'merchant',
            'category',
            'merchant__location'
        ).prefetch_related('tags').distinct()

        results = []
        for listing in listings:
            # Get tags
            tags = [{'id': str(tag.id), 'name': tag.name} for tag in listing.tags.all()]

            results.append({
                'type': 'listing',
                'id': str(listing.id),
                'title': listing.title,
                'description': self._truncate_text(listing.description, 200),
                'listing_type': listing.listing_type,
                'price_type': listing.price_type,
                'price': float(listing.price) if listing.price else None,
                'price_min': float(listing.price_min) if listing.price_min else None,
                'price_max': float(listing.price_max) if listing.price_max else None,
                'currency': listing.currency,
                'is_price_negotiable': listing.is_price_negotiable,
                'primary_image': listing.primary_image,
                'is_featured': listing.is_featured,
                'views_count': listing.views_count,
                'category': {
                    'id': str(listing.category.id),
                    'name': listing.category.name,
                } if listing.category else None,
                'tags': tags,
                'merchant': {
                    'id': str(listing.merchant.id),
                    'display_name': listing.merchant.display_name,
                    'logo': listing.merchant.logo,
                    'verified': listing.merchant.verified,
                    'rating': float(listing.merchant.rating),
                } if listing.merchant else None,
                'location': {
                    'id': str(listing.merchant.location.id) if listing.merchant.location else None,
                    'name': listing.merchant.location.area if listing.merchant.location else None,
                } if listing.merchant and listing.merchant.location else None,
                'created_at': listing.created_at.isoformat(),
                'relevance_score': listing.relevance_score,
            })

        return results

    def _sort_results(self, results, sort_by):
        """Sort results based on the specified criteria"""
        if sort_by == 'relevance':
            # Sort by relevance score (desc), then featured status, then rating
            results.sort(
                key=lambda x: (
                    -x.get('relevance_score', 0),
                    -int(x.get('is_featured', False) or x.get('featured', False)),
                    -x.get('rating', 0)
                )
            )
        elif sort_by == 'newest':
            results.sort(key=lambda x: x['created_at'], reverse=True)
        elif sort_by == 'rating':
            # Only applicable to merchants and listings with merchant ratings
            results.sort(
                key=lambda x: (
                    -x.get('rating', 0) if x['type'] == 'merchant'
                    else -x.get('merchant', {}).get('rating', 0)
                )
            )
        elif sort_by == 'price_asc':
            # Only listings have prices
            listings = [r for r in results if r['type'] == 'listing']
            merchants = [r for r in results if r['type'] == 'merchant']
            listings.sort(key=lambda x: x.get('price') or x.get('price_min') or float('inf'))
            results = listings + merchants
        elif sort_by == 'price_desc':
            listings = [r for r in results if r['type'] == 'listing']
            merchants = [r for r in results if r['type'] == 'merchant']
            listings.sort(
                key=lambda x: x.get('price') or x.get('price_max') or 0,
                reverse=True
            )
            results = listings + merchants

        return results

    def _truncate_text(self, text, max_length):
        """Truncate text to specified length with ellipsis"""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(' ', 1)[0] + '...'
