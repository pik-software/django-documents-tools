import pytest
from django.test import override_settings
from rest_framework.fields import CharField

from django_documents_tools.api.serializers import (
    clone_serializer_field, get_change_serializer_class,
    get_snapshot_serializer, get_documented_model_serializer,
    BaseChangeSerializer, BaseSnapshotSerializer,
    BaseDocumentedModelLinkSerializer)
from .serializers import (
    BookSerializer, CustomChangeSerializer, CustomSnapshotSerializer,
    CustomDocumentedModelLinkSerializer)
from .models import Book


UNKNOWN_SERIALIZER_PATH = 'tests.serializers.UnknownBookSerializer'


@pytest.fixture
def book_change_model():
    return Book.changes.model


@pytest.fixture
def book_snapshot_model(book_change_model):
    return book_change_model._meta.get_field('snapshot').related_model  # noqa: protected-access


def test_field_clone():
    src_field = CharField(required=False)
    dst_field = clone_serializer_field(src_field, required=True)
    assert dst_field.required


class TestGetChangeSerializerClass:
    setting_name = 'BASE_CHANGE_SERIALIZER'
    custom_serializer_path = 'tests.serializers.CustomChangeSerializer'
    expected_error_msg = (
        'UnknownBookSerializer must be subclass of BaseChangeSerializer')

    @staticmethod
    def test_get_default(book_change_model):
        book_change_serializer = get_change_serializer_class(
            book_change_model, BookSerializer)

        assert issubclass(book_change_serializer, BaseChangeSerializer)
        assert book_change_serializer.Meta.fields == (
            '_uid', '_type', '_version', 'created', 'updated', 'document_name',
            'document_date', 'document_link', 'document_is_draft',
            'document_fields', 'title', 'author', 'summary', 'isbn',
            'is_published', 'book')

    def test_get_custom(self, book_change_model):
        custom_settings = {
            self.setting_name: self.custom_serializer_path
        }

        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            book_change_serializer = get_change_serializer_class(
                book_change_model, BookSerializer)

        assert issubclass(book_change_serializer, CustomChangeSerializer)
        assert book_change_serializer.Meta.fields == (
            '_uid', '_type', '_version', 'created', 'updated', 'document_name',
            'document_date', 'document_link', 'document_is_draft',
            'document_fields', 'custom_field', 'title', 'author', 'summary',
            'isbn', 'is_published', 'book')

    def test_get_unknown(self, book_change_model):
        custom_settings = {
            self.setting_name: UNKNOWN_SERIALIZER_PATH
        }

        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            with pytest.raises(Exception) as exc_info:
                get_change_serializer_class(book_change_model, BookSerializer)
            assert exc_info.value.args[0] == self.expected_error_msg


class TestGetSnapshotSerializerClass:
    setting_name = 'BASE_SNAPSHOT_SERIALIZER'
    custom_serializer_path = 'tests.serializers.CustomSnapshotSerializer'
    expected_error_msg = (
        'UnknownBookSerializer must be subclass of BaseSnapshotSerializer')

    @staticmethod
    def test_get_default(book_change_model, book_snapshot_model):
        book_change_serializer = get_change_serializer_class(
            book_change_model, BookSerializer)
        book_snapshot_serializer = get_snapshot_serializer(
            book_snapshot_model, book_change_serializer)

        assert issubclass(book_snapshot_serializer, BaseSnapshotSerializer)
        assert book_snapshot_serializer.Meta.fields == (
            '_uid', '_type', '_version', 'created', 'updated',
            'document_fields', 'history_date', 'title', 'author', 'summary',
            'isbn', 'is_published', 'book')

    def test_get_custom(self, book_change_model, book_snapshot_model):
        book_change_serializer = get_change_serializer_class(
            book_change_model, BookSerializer)
        custom_settings = {
            self.setting_name: self.custom_serializer_path
        }

        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            book_snapshot_serializer = get_snapshot_serializer(
                book_snapshot_model, book_change_serializer)

        assert issubclass(book_snapshot_serializer, CustomSnapshotSerializer)
        assert book_snapshot_serializer.Meta.fields == (
            '_uid', '_type', '_version', 'created', 'updated',
            'document_fields', 'history_date', 'custom_field', 'title',
            'author', 'summary', 'isbn', 'is_published', 'book')

    def test_get_unknown(self, book_change_model, book_snapshot_model):
        book_change_serializer = get_change_serializer_class(
            book_change_model, BookSerializer)
        custom_settings = {
            self.setting_name: UNKNOWN_SERIALIZER_PATH
        }

        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            with pytest.raises(Exception) as exc_info:
                get_snapshot_serializer(
                    book_snapshot_model, book_change_serializer)
            assert exc_info.value.args[0] == self.expected_error_msg


class TestGetDocumentedModelLinkSerializerClass:
    setting_name = 'BASE_DOCUMENTED_MODEL_LINK_SERIALIZER'
    custom_serializer_path = (
        'tests.serializers.CustomDocumentedModelLinkSerializer')
    expected_error_msg = (
        'UnknownBookSerializer must be subclass of '
        'BaseDocumentedModelLinkSerializer')

    @staticmethod
    def test_get_default():
        book_link_serializer = get_documented_model_serializer(Book)
        assert issubclass(
            book_link_serializer, BaseDocumentedModelLinkSerializer)
        assert book_link_serializer.Meta.fields == (
            '_uid', '_type', '_version', 'created', 'updated')

    def test_get_custom(self):
        custom_settings = {
            self.setting_name: self.custom_serializer_path
        }

        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            book_link_serializer = get_documented_model_serializer(Book)

        assert issubclass(
            book_link_serializer, CustomDocumentedModelLinkSerializer)
        assert book_link_serializer.Meta.fields == (
            '_uid', '_type', '_version', 'created', 'updated', 'custom_field')

    def test_get_unknown(self, book_change_model):
        custom_settings = {
            self.setting_name: UNKNOWN_SERIALIZER_PATH
        }

        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            with pytest.raises(Exception) as exc_info:
                get_documented_model_serializer(Book)
        assert exc_info.value.args[0] == self.expected_error_msg
