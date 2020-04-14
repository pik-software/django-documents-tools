from rest_framework import serializers
from django_documents_tools.api.serializers import (
    BaseChangeSerializer, BaseSnapshotSerializer,
    BaseDocumentedModelLinkSerializer)

from .test_models import Book, Author


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = (
            'id', 'first_name', 'last_name', 'date_of_birth', 'date_of_death')


class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'summary', 'isbn', 'is_published')


class CustomChangeSerializer(BaseChangeSerializer):
    custom_field = serializers.SerializerMethodField()

    @staticmethod
    def get_custom_field(obj):
        return 'Extra'

    class Meta:
        fields = BaseChangeSerializer.Meta.fields + ('custom_field',)


class CustomSnapshotSerializer(BaseSnapshotSerializer):
    custom_field = serializers.SerializerMethodField()

    @staticmethod
    def get_custom_field(obj):
        return 'Extra'

    class Meta:
        fields = BaseSnapshotSerializer.Meta.fields + ('custom_field',)


class CustomDocumentedModelLinkSerializer(BaseDocumentedModelLinkSerializer):
    custom_field = serializers.SerializerMethodField()

    @staticmethod
    def get_custom_field(obj):
        return 'Extra'

    class Meta:
        fields = BaseDocumentedModelLinkSerializer.Meta.fields + (
            'custom_field',)


class UnknownBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'summary', 'isbn', 'is_published')
