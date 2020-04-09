from rest_framework import serializers
from django_documents_tools.api.serializers import (
    ChangeSerializerBase, SnapshotSerializerBase,
    DocumentedModelLinkSerializer)

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


class CustomChangeSerializer(ChangeSerializerBase):
    custom_field = serializers.SerializerMethodField()

    @staticmethod
    def get_custom_field(obj):
        return 'Extra'

    class Meta:
        fields = ChangeSerializerBase.Meta.fields + ('custom_field',)


class CustomSnapshotSerializer(SnapshotSerializerBase):
    custom_field = serializers.SerializerMethodField()

    @staticmethod
    def get_custom_field(obj):
        return 'Extra'

    class Meta:
        fields = SnapshotSerializerBase.Meta.fields + ('custom_field',)


class CustomDocumentedModelLinkSerializer(DocumentedModelLinkSerializer):
    custom_field = serializers.SerializerMethodField()

    @staticmethod
    def get_custom_field(obj):
        return 'Extra'

    class Meta:
        fields = DocumentedModelLinkSerializer.Meta.fields + ('custom_field',)


class UnknownBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('id', 'title', 'author', 'summary', 'isbn', 'is_published')
