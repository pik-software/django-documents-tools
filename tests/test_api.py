import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework import status

from tests.conftest import add_user_model_permissions, add_permissions_to_user
from tests.test_models import _create_book_change, BookChange


def get_iso_date_or_none(date_obj):
    if date_obj:
        return date_obj.isoformat()
    return None


def get_author_response(author):
    return {
        'uid': str(author.uid),
        'first_name': author.first_name,
        'last_name': author.last_name,
        'date_of_birth': get_iso_date_or_none(author.date_of_birth),
        'date_of_death': get_iso_date_or_none(author.date_of_death)}


def get_book_response(book):
    return {
        '_uid': str(book.uid),
        '_type': book._meta.model_name,  # noqa: protected-access
        '_version': None,
        'created': get_iso_date_or_none(book.created),
        'updated': get_iso_date_or_none(book.updated)}


def get_book_change_response(book_change):
    return {
        '_uid': str(book_change.uid),
        '_type': book_change._meta.model_name,  # noqa: protected-access
        '_version': None,
        'created': get_iso_date_or_none(book_change.created),
        'updated': get_iso_date_or_none(book_change.updated),
        'deleted': get_iso_date_or_none(book_change.deleted),
        'document_name': book_change.document_name,
        'document_date': get_iso_date_or_none(book_change.document_date),
        'document_link': '',
        'document_is_draft': book_change.document_is_draft,
        'document_fields': book_change.document_fields,
        'attachment': book_change.attachment,
        'title': book_change.title,
        'author': get_author_response(book_change.author),
        'summary': book_change.summary,
        'isbn': book_change.isbn,
        'is_published': book_change.is_published,
        'book': get_book_response(book_change.book)
    }


@pytest.mark.django_db
class TestBookChange:
    API_URL = '/api/v1/bookchange-list/'
    API_INSTANCE_URL = API_URL + '{}/'

    @override_settings(ROOT_URLCONF='tests.urls', DOCUMENTS_TOOLS={
        'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
    def test_update_with_permission(self, api_user, api_client):
        add_user_model_permissions(api_user, BookChange, 'view', 'change')
        add_permissions_to_user(
            api_user, ['can_change_deleted'])
        book_change = _create_book_change(document_is_draft=False)
        document_fields = book_change.get_documented_fields()
        data = {
            'deleted': timezone.now(),
            'document_fields': document_fields}

        response = api_client.patch(
            self.API_INSTANCE_URL.format(book_change.uid), data,
            format='json')
        book_change.refresh_from_db()

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == get_book_change_response(book_change)

    @override_settings(ROOT_URLCONF='tests.urls', DOCUMENTS_TOOLS={
        'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
    def test_update_without_permission(self, api_user, api_client):
        error_message = 'У вас нет прав для редактирования этого поля.'

        add_user_model_permissions(api_user, BookChange, 'view', 'change')
        book_change = _create_book_change(document_is_draft=False)
        document_fields = book_change.get_documented_fields()
        data = {
            'deleted': timezone.now(),
            'document_fields': document_fields}

        response = api_client.patch(
            self.API_INSTANCE_URL.format(book_change.uid), data,
            format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert error_message in response.data['deleted'][0]
