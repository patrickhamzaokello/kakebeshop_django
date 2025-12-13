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
    ActivityLog, AuditLog, ApiUsage
)
from .serializers import (
    FavoriteSerializer, SavedSearchSerializer, ConversationSerializer,
    MessageSerializer, NotificationSerializer, ListingReviewSerializer,
    MerchantReviewSerializer, ReportSerializer, MerchantScoreSerializer,
    ActivityLogSerializer, AuditLogSerializer, ApiUsageSerializer
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