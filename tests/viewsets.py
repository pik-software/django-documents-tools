from rest_framework.viewsets import ModelViewSet

from django_documents_tools.api.viewsets import (
    BaseChangeViewSet, BaseSnapshotViewSet, BaseChangeAttachmentViewSet)

from .models import Book
from .serializers import BookSerializer
from .filters import BookFilter


class BookViewSet(ModelViewSet):
    allow_history = False

    lookup_field = 'uid'
    lookup_url_kwarg = '_uid'
    serializer_class = BookSerializer
    filterset_class = BookFilter
    select_related_fields = ['author']
    queryset = Book.objects.all()


class CustomBookChangeViewSet(BaseChangeViewSet):
    # Custom viewset attribute
    prefetch_related_fields = ['test']


class CustomBookSnapshotViewSet(BaseSnapshotViewSet):
    # Custom viewset attribute
    prefetch_related_fields = ['test']


class CustomBookChangeAttachmentViewSet(BaseChangeAttachmentViewSet):
    # Custom viewset attribute
    prefetch_related_fields = ['test']


class UnknownBookViewSet(ModelViewSet):
    lookup_field = 'uid'
    lookup_url_kwarg = '_uid'
    serializer_class = BookSerializer
    filterset_class = BookFilter
    select_related_fields = ['author']
