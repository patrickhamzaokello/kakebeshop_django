# kakebe_apps/engagement/views.py (interactions app)

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import (
    Favorite, SavedSearch, Conversation, Message, Notification,
    ListingReview, MerchantReview, Report, MerchantScore,
    ActivityLog, AuditLog, ApiUsage
)
from .serializers import (
    FavoriteSerializer, SavedSearchSerializer, ConversationSerializer,
    MessageSerializer, NotificationSerializer, ListingReviewSerializer,
    MerchantReviewSerializer, ReportSerializer, MerchantScoreSerializer,
    ActivityLogSerializer, AuditLogSerializer, ApiUsageSerializer
)
from kakebe_apps.listings.models import Listing


class FavoriteViewSet(viewsets.ModelViewSet):
    """
    Manage user favorites/wishlist
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    # Add tags for Swagger organization
    swagger_tags = ['Engagement - Favorites']

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        tags=['Engagement - Favorites'],
        method='post',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'listing': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_UUID,
                    description='UUID of the listing'
                )
            },
            required=['listing']
        ),
        responses={
            200: openapi.Response('Favorite removed'),
            201: openapi.Response('Favorite added')
        }
    )
    @action(detail=False, methods=['post'])
    def toggle(self, request):
        listing_id = request.data.get('listing')
        listing = get_object_or_404(Listing, id=listing_id)

        obj, created = Favorite.objects.get_or_create(
            user=request.user,
            listing=listing
        )
        if not created:
            obj.delete()
            return Response({'status': 'removed'})
        return Response({'status': 'added'}, status=status.HTTP_201_CREATED)


class SavedSearchViewSet(viewsets.ModelViewSet):
    """
    Manage saved searches for users
    """
    serializer_class = SavedSearchSerializer
    permission_classes = [IsAuthenticated]
    swagger_tags = ['Engagement - Saved Searches']

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View conversations between buyers and sellers
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    lookup_value_regex = '[0-9a-f-]{36}'
    swagger_tags = ['Engagement - Messaging']

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            models.Q(buyer=user) | models.Q(seller=user)
        ).order_by('-last_message_at')


class MessageViewSet(mixins.CreateModelMixin,
                     mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    """
    Send and view messages in conversations
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    swagger_tags = ['Engagement - Messaging']

    @swagger_auto_schema(
        tags=['Engagement - Messaging'],
        manual_parameters=[
            openapi.Parameter(
                'conversation_id',
                openapi.IN_PATH,
                description="UUID of the conversation",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=['Engagement - Messaging'],
        manual_parameters=[
            openapi.Parameter(
                'conversation_id',
                openapi.IN_PATH,
                description="UUID of the conversation",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_id')
        user = self.request.user

        conversation = get_object_or_404(
            Conversation.objects.filter(
                models.Q(buyer=user) | models.Q(seller=user)
            ),
            id=conversation_id
        )

        return conversation.messages.all()

    def perform_create(self, serializer):
        conversation_id = self.kwargs.get('conversation_id')
        user = self.request.user

        conversation = get_object_or_404(
            Conversation.objects.filter(
                models.Q(buyer=user) | models.Q(seller=user)
            ),
            id=conversation_id
        )

        serializer.save(sender=user, conversation=conversation)
        conversation.last_message_at = timezone.now()
        conversation.save()


class NotificationViewSet(viewsets.ModelViewSet):
    """
    Manage user notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    lookup_value_regex = '[0-9a-f-]{36}'
    swagger_tags = ['Engagement - Notifications']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        tags=['Engagement - Notifications'],
        method='post',
        responses={200: openapi.Response('All notifications marked as read')}
    )
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all read'})

    @swagger_auto_schema(
        tags=['Engagement - Notifications'],
        method='post',
        responses={200: openapi.Response('Notification marked as read')}
    )
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'read'})


class ListingReviewViewSet(viewsets.ModelViewSet):
    """
    Create and manage listing reviews
    """
    serializer_class = ListingReviewSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    lookup_value_regex = '[0-9a-f-]{36}'
    swagger_tags = ['Engagement - Reviews']

    def get_queryset(self):
        return ListingReview.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MerchantReviewViewSet(viewsets.ModelViewSet):
    """
    Create and manage merchant reviews
    """
    serializer_class = MerchantReviewSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    lookup_value_regex = '[0-9a-f-]{36}'
    swagger_tags = ['Engagement - Reviews']

    def get_queryset(self):
        return MerchantReview.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReportViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Report content for moderation
    """
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]
    swagger_tags = ['Engagement - Reports']

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class MerchantScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View merchant reputation scores
    """
    queryset = MerchantScore.objects.all()
    serializer_class = MerchantScoreSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    lookup_value_regex = '[0-9a-f-]{36}'
    swagger_tags = ['Engagement - Scores']


# Admin-only logs
class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View activity logs (Admin only)
    """
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'pk'
    lookup_value_regex = '[0-9a-f-]{36}'
    swagger_tags = ['Admin - Logs']


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View audit logs (Admin only)
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'pk'
    lookup_value_regex = '[0-9a-f-]{36}'
    swagger_tags = ['Admin - Logs']


class ApiUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View API usage statistics (Admin only)
    """
    queryset = ApiUsage.objects.all()
    serializer_class = ApiUsageSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'pk'
    lookup_value_regex = '[0-9a-f-]{36}'
    swagger_tags = ['Admin - Logs']