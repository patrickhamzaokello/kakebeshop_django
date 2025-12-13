# kakebe_apps/listings/views.py

from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import Listing, ListingTag, ListingImage, ListingBusinessHour
from .serializers import (
    ListingSerializer, ListingTagSerializer,
    ListingImageSerializer, ListingBusinessHourSerializer
)


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]  # Adjust as needed

    def perform_create(self, serializer):
        serializer.save(merchant=self.request.user.name)  # Assuming user has a related Merchant

    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        listing = get_object_or_404(Listing, pk=pk)
        listing.views_count += 1
        listing.save()
        return Response({'views_count': listing.views_count})

    @action(detail=True, methods=['post'])
    def increment_contacts(self, request, pk=None):
        listing = get_object_or_404(Listing, pk=pk)
        listing.contact_count += 1
        listing.save()
        return Response({'contact_count': listing.contact_count})


class ListingTagViewSet(viewsets.ModelViewSet):
    queryset = ListingTag.objects.all()
    serializer_class = ListingTagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ListingImageViewSet(viewsets.ModelViewSet):
    queryset = ListingImage.objects.all()
    serializer_class = ListingImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save()


class ListingBusinessHourViewSet(viewsets.ModelViewSet):
    queryset = ListingBusinessHour.objects.all()
    serializer_class = ListingBusinessHourSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]



