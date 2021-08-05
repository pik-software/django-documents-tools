from unittest import mock

import pytest
from django.test import override_settings

from django_documents_tools.api.viewsets import (
    get_change_viewset, get_snapshot_viewset, get_change_attachment_viewset,
    BaseChangeViewSet, BaseSnapshotViewSet, BaseChangeAttachmentViewSet)
from tests.viewsets import (
    BookViewSet, CustomBookChangeViewSet, CustomBookSnapshotViewSet,
    CustomBookChangeAttachmentViewSet)


UNKNOWN_VIEWSET_PATH = 'tests.viewsets.UnknownBookViewSet'


class TestGetChangeViewSet:
    setting_name = 'BASE_CHANGE_VIEWSET'
    custom_viewset_path = 'tests.viewsets.CustomBookChangeViewSet'
    expected_error_msg = (
        'UnknownBookViewSet must be subclass of BaseChangeViewSet')

    @staticmethod
    def test_get_default():
        book_change_viewset = get_change_viewset(BookViewSet)

        assert issubclass(book_change_viewset, BaseChangeViewSet)
        assert book_change_viewset.allow_history is True
        assert book_change_viewset.select_related_fields == ('book', 'author')
        assert book_change_viewset.lookup_field == 'uid'
        assert book_change_viewset.lookup_url_kwarg == 'guid'

    def test_get_custom(self):
        custom_settings = {
            self.setting_name: self.custom_viewset_path
        }
        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            book_change_viewset = get_change_viewset(BookViewSet)

        assert issubclass(book_change_viewset, CustomBookChangeViewSet)
        assert book_change_viewset.allow_history is True
        assert book_change_viewset.select_related_fields == ('book', 'author')
        assert book_change_viewset.lookup_field == 'uid'
        assert book_change_viewset.lookup_url_kwarg == 'guid'
        assert book_change_viewset.prefetch_related_fields == ['test']

    def test_get_unknown(self):
        custom_settings = {
            self.setting_name: UNKNOWN_VIEWSET_PATH
        }

        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            with pytest.raises(Exception) as exc_info:
                get_change_viewset(BookViewSet)
            assert exc_info.value.args[0] == self.expected_error_msg

    def test_get_for_model(self, book_change_model):
        with mock.patch.object(
                book_change_model, '_base_viewset', self.custom_viewset_path):
            book_change_viewset = get_change_viewset(BookViewSet)

        assert issubclass(book_change_viewset, CustomBookChangeViewSet)
        assert book_change_viewset.allow_history is True
        assert book_change_viewset.select_related_fields == ('book', 'author')
        assert book_change_viewset.lookup_field == 'uid'
        assert book_change_viewset.lookup_url_kwarg == 'guid'
        assert book_change_viewset.prefetch_related_fields == ['test']


class TestGetSnapshotViewSet:
    setting_name = 'BASE_SNAPSHOT_VIEWSET'
    custom_viewset_path = 'tests.viewsets.CustomBookSnapshotViewSet'
    expected_error_msg = (
        'UnknownBookViewSet must be subclass of BaseSnapshotViewSet')

    @staticmethod
    def test_get_default():
        book_change_viewset = get_change_viewset(BookViewSet)
        book_snapshot_viewset = get_snapshot_viewset(
            book_change_viewset, BookViewSet)

        assert issubclass(book_snapshot_viewset, BaseSnapshotViewSet)
        assert book_snapshot_viewset.allow_history is False
        assert book_snapshot_viewset.select_related_fields == (
            'book', 'author')
        assert book_snapshot_viewset.lookup_field == 'uid'
        assert book_snapshot_viewset.lookup_url_kwarg == 'guid'

    def test_get_custom(self):
        custom_settings = {
            self.setting_name: self.custom_viewset_path
        }
        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            book_change_viewset = get_change_viewset(BookViewSet)
            book_snapshot_viewset = get_snapshot_viewset(
                book_change_viewset, BookViewSet)

        assert issubclass(book_snapshot_viewset, CustomBookSnapshotViewSet)
        assert book_snapshot_viewset.allow_history is False
        assert book_snapshot_viewset.select_related_fields == (
            'book', 'author')
        assert book_snapshot_viewset.lookup_field == 'uid'
        assert book_snapshot_viewset.lookup_url_kwarg == 'guid'
        assert book_snapshot_viewset.prefetch_related_fields == ['test']

    def test_get_unknown(self):
        custom_settings = {
            self.setting_name: UNKNOWN_VIEWSET_PATH
        }

        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            with pytest.raises(Exception) as exc_info:
                book_change_viewset = get_change_viewset(BookViewSet)
                get_snapshot_viewset(book_change_viewset, BookViewSet)
            assert exc_info.value.args[0] == self.expected_error_msg

    def test_get_for_model(self, book_snapshot_model):
        with mock.patch.object(
                book_snapshot_model, '_base_viewset',
                self.custom_viewset_path):
            book_change_viewset = get_change_viewset(BookViewSet)
            book_snapshot_viewset = get_snapshot_viewset(
                book_change_viewset, BookViewSet)

        assert issubclass(book_snapshot_viewset, CustomBookSnapshotViewSet)
        assert book_snapshot_viewset.allow_history is False
        assert book_snapshot_viewset.select_related_fields == (
            'book', 'author')
        assert book_snapshot_viewset.lookup_field == 'uid'
        assert book_snapshot_viewset.lookup_url_kwarg == 'guid'
        assert book_snapshot_viewset.prefetch_related_fields == ['test']


class TestGetChangeAttachmentViewSet:
    setting_name = 'BASE_CHANGE_ATTACHMENT_VIEWSET'
    custom_viewset_path = 'tests.viewsets.CustomBookChangeAttachmentViewSet'
    expected_error_msg = (
        'UnknownBookViewSet must be subclass of BaseChangeAttachmentViewSet')

    @staticmethod
    def test_get_default():
        book_change_viewset = get_change_viewset(BookViewSet)
        book_change_attachment_viewset = get_change_attachment_viewset(
            book_change_viewset)

        assert issubclass(
            book_change_attachment_viewset, BaseChangeAttachmentViewSet)
        assert book_change_attachment_viewset.allow_history is True
        assert book_change_attachment_viewset.select_related_fields == (
            'change',)
        assert book_change_attachment_viewset.lookup_field == 'uid'
        assert book_change_attachment_viewset.lookup_url_kwarg == 'guid'

    def test_get_custom(self):
        custom_settings = {
            self.setting_name: self.custom_viewset_path
        }
        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            book_change_viewset = get_change_viewset(BookViewSet)
            book_change_attachment_viewset = get_change_attachment_viewset(
                book_change_viewset)

        assert issubclass(
            book_change_attachment_viewset, CustomBookChangeAttachmentViewSet)
        assert book_change_attachment_viewset.allow_history is True
        assert book_change_attachment_viewset.select_related_fields == (
            'change',)
        assert book_change_attachment_viewset.lookup_field == 'uid'
        assert book_change_attachment_viewset.lookup_url_kwarg == 'guid'
        assert book_change_attachment_viewset.prefetch_related_fields == [
            'test']

    def test_get_unknown(self):
        custom_settings = {
            self.setting_name: UNKNOWN_VIEWSET_PATH
        }

        with override_settings(DOCUMENTS_TOOLS=custom_settings):
            with pytest.raises(Exception) as exc_info:
                book_change_viewset = get_change_viewset(BookViewSet)
                get_change_attachment_viewset(book_change_viewset)
            assert exc_info.value.args[0] == self.expected_error_msg

    def test_get_for_model(self, book_change_attachment_model):
        with mock.patch.object(
                book_change_attachment_model, '_base_viewset',
                self.custom_viewset_path):
            book_change_viewset = get_change_viewset(BookViewSet)
            book_change_attachment_viewset = get_change_attachment_viewset(
                book_change_viewset)

        assert issubclass(
            book_change_attachment_viewset, CustomBookChangeAttachmentViewSet)
        assert book_change_attachment_viewset.allow_history is True
        assert book_change_attachment_viewset.select_related_fields == (
            'change',)
        assert book_change_attachment_viewset.lookup_field == 'uid'
        assert book_change_attachment_viewset.lookup_url_kwarg == 'guid'
        assert book_change_attachment_viewset.prefetch_related_fields == [
            'test']
