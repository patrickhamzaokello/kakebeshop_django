from django.urls import path
from .views import (
    PresignUploadView,
    ConfirmUploadView,
    AttachImagesToObjectView,
    ReorderImagesView,
    CleanupAbandonedUploadsView,
    MyDraftImagesView,
)

urlpatterns = [
    path('presign/', PresignUploadView.as_view(), name='presign-upload'),
    path('confirm/', ConfirmUploadView.as_view(), name='confirm-upload'),
    path('attach/', AttachImagesToObjectView.as_view(), name='attach-images'),
    path('reorder/', ReorderImagesView.as_view(), name='reorder-images'),
    path('cleanup/', CleanupAbandonedUploadsView.as_view(), name='cleanup-uploads'),
    path('drafts/', MyDraftImagesView.as_view(), name='my-draft-images'),
]