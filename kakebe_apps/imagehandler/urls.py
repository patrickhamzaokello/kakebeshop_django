from django.urls import path
from .views import PresignUploadView, ConfirmUploadView

urlpatterns = [
    path("uploads/presign/", PresignUploadView.as_view()),
    path("uploads/confirm/", ConfirmUploadView.as_view()),
]
