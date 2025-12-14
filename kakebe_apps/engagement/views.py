# kakebe_apps/interactions/views.py

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models

from .models import (
    Favorite, SavedSearch, Conversation, Message, Notification,
    ListingReview, MerchantReview, Report, MerchantScore,
    ActivityLog, AuditLog, ApiUsage, OnboardingStatus, UserIntent
)
from .serializers import (
    FavoriteSerializer, SavedSearchSerializer, ConversationSerializer,
    MessageSerializer, NotificationSerializer, ListingReviewSerializer,
    MerchantReviewSerializer, ReportSerializer, MerchantScoreSerializer,
    ActivityLogSerializer, AuditLogSerializer, ApiUsageSerializer, OnboardingStatusSerializer, UserIntentSerializer
)
from ..listings.models import Listing


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    @action(detail=False)
    def toggle(self, request):
        listing_id = request.data.get('listing')
        listing = get_object_or_404(Listing, id=listing_id)

        obj, created = Favorite.objects.get_or_create(user=request.user, listing=listing)
        if not created:
            obj.delete()
            return Response({'status': 'removed'})
        return Response({'status': 'added'})


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