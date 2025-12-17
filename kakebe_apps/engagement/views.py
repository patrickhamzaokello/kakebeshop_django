# kakebe_apps/interactions/views.py

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models

from .models import (
    SavedSearch, Conversation, Message, Notification,
    ListingReview, MerchantReview, Report, MerchantScore,
    ActivityLog, AuditLog, ApiUsage, OnboardingStatus, UserIntent, PushToken
)
from .serializers import (
    SavedSearchSerializer, ConversationSerializer,
    MessageSerializer, NotificationSerializer, ListingReviewSerializer,
    MerchantReviewSerializer, ReportSerializer, MerchantScoreSerializer,
    ActivityLogSerializer, AuditLogSerializer, ApiUsageSerializer, OnboardingStatusSerializer, UserIntentSerializer,
    PushTokenSerializer, PushTokenCreateSerializer, PushTokenUpdateUsageSerializer
)



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
        return Conversation.objects.filter(
            models.Q(buyer=user) | models.Q(seller=user)
        ).order_by('-last_message_at')


class MessageViewSet(mixins.CreateModelMixin,
                    mixins.ListModelMixin,
                    viewsets.GenericViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation = get_object_or_404(Conversation, id=self.kwargs['conversation_id'],
                                         buyer=self.request.user) | get_object_or_404(Conversation, id=self.kwargs['conversation_id'],
                                                                                     seller=self.request.user)
        return conversation.messages.all()

    def perform_create(self, serializer):
        conversation = get_object_or_404(Conversation, id=self.kwargs['conversation_id'])
        serializer.save(sender=self.request.user, conversation=conversation)
        conversation.last_message_at = timezone.now()
        conversation.save()


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all read'})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'read'})


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
