from datetime import timedelta

import pytest
from django.utils import timezone
from django.test import override_settings
from django_documents_tools.exceptions import (
    BusinessEntityCreationIsNotAllowedError)

from .models import Book, Address, Author


BookChange = Book.changes.model # noqa: invalid-name
BookSnapshot = (                # noqa: invalid-name
    BookChange.snapshot.field.remote_field.model)


def _create_author(first_name='first_name', last_name='last_name'):
    address = Address(
        country='Russia', city='Moscow', street='Lenina', house='23',
        zip_code='1232132')
    address.save()
    author = Author(
        first_name=first_name, last_name=last_name,
        date_of_birth=timezone.now() - timedelta(days=9999), address=address)
    author.save()
    return author


def _create_book_change(
        document_date=None, document_fields=None, document_is_draft=True,
        title='title', book=None, author=None):
    if document_date is None:
        document_date = timezone.now()
    if document_fields is None:
        document_fields = [
            'title', 'author', 'isbn', 'is_published', 'summary']

    author = author or _create_author()
    change = BookChange(
        document_fields=document_fields,
        document_date=document_date,
        document_is_draft=document_is_draft, book=book,
        title=title, author=author, summary='summary', isbn='isbn')
    change.save()
    return change


@pytest.mark.django_db
def test_create_draft_changes():
    change = _create_book_change()

    assert change.snapshot_or_none is None
    assert BookChange.objects.count() == 1
    assert Book.objects.count() == 0


@pytest.mark.django_db
@override_settings(DOCUMENTS_TOOLS={
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
def test_turn_off_change_draft_mode_without_doc_object():
    change = _create_book_change()

    assert change.document_is_draft
    assert Book.objects.count() == 0

    change.document_is_draft = False
    change.save()

    assert change.snapshot_or_none
    assert BookChange.objects.count() == 1
    assert Book.objects.count() == 1

    snapshot = change.snapshot_or_none
    book = Book.objects.get()

    assert change.title == book.title == snapshot.title
    assert change.author == book.author == snapshot.author


@pytest.mark.django_db
@override_settings(DOCUMENTS_TOOLS={
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
def test_turn_off_change_draft_mode_with_doc_object():
    change_1 = _create_book_change(document_is_draft=False)
    assert change_1.snapshot_or_none
    assert BookChange.objects.count() == 1
    assert Book.objects.count() == 1

    change_2 = _create_book_change(
        title='new_title', book=change_1.book)
    change_2.document_is_draft = False
    change_2.save()

    assert change_2.snapshot_or_none
    assert BookChange.objects.count() == 2
    assert Book.objects.count() == 1

    book = change_1.book
    book.refresh_from_db()
    assert change_2.title == book.title
    assert change_2.author == book.author


@pytest.mark.django_db
@override_settings(DOCUMENTS_TOOLS={
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
def test_alter_already_created_change():
    change = _create_book_change(document_is_draft=False)

    expected_title = 'new_title'
    expected_author = _create_author()
    change.title = expected_title
    change.author = expected_author
    change.save()

    book = Book.objects.get()
    snapshot = change.snapshot
    assert book.title == expected_title == snapshot.title
    assert book.author == expected_author == snapshot.author


@pytest.mark.django_db
def test_couple_of_changes_to_one_snapshot():
    document_date_1 = timezone.now() - timedelta(minutes=50)
    document_date_2 = document_date_1 + timedelta(minutes=5)
    book = Book(title='title', author=_create_author())
    book.save()
    change_1 = _create_book_change(
        document_date=document_date_1, book=book,
        document_is_draft=False)
    expected_author = _create_author()
    expected_title = 'expected_title'
    change_2 = _create_book_change(
        document_date=document_date_2, book=book,
        document_is_draft=False, title=expected_title, author=expected_author)

    change_1.refresh_from_db()
    assert change_1.snapshot_or_none
    assert change_1.snapshot_or_none == change_2.snapshot_or_none
    assert Book.objects.count() == 1
    assert BookChange.objects.count() == 2
    assert BookSnapshot.objects.filter(
        deleted__isnull=True).count() == 1

    book.refresh_from_db()
    assert change_2.title == book.title == expected_title
    assert change_2.author == book.author == expected_author


@pytest.mark.django_db
@override_settings(DOCUMENTS_TOOLS={
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
def test_delete_change():
    change = _create_book_change(document_is_draft=False)

    assert change.snapshot_or_none
    assert BookChange.objects.count() == 1
    assert Book.objects.count() == 1

    change.deleted = timezone.now()
    change.save()

    assert change.snapshot_or_none
    assert change.snapshot.deleted
    assert BookChange.objects.filter(
        deleted__isnull=False).count() == 1
    assert Book.objects.count() == 1


@pytest.mark.django_db
@override_settings(DOCUMENTS_TOOLS={
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
def test_delete_doc_object():
    change = _create_book_change(document_is_draft=False)

    assert change.snapshot_or_none
    assert BookChange.objects.count() == 1
    assert Book.objects.count() == 1

    book = change.book
    book.deleted = timezone.now()
    book.save()

    change.refresh_from_db()
    assert BookChange.objects.filter(
        deleted__isnull=False).count() == 1
    assert BookSnapshot.objects.filter(
        deleted__isnull=False).count() == 1
    assert Book.objects.filter(deleted__isnull=False).count() == 1


@pytest.mark.django_db
@override_settings(DOCUMENTS_TOOLS={
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
def test_recover_deleted_snapshot_after_move_change():
    old_time = timezone.now() - timedelta(days=5)
    old_change = _create_book_change(
        document_date=old_time, document_is_draft=False)
    expected_author = _create_author()
    expected_title = 'expected_title'
    moved_change = _create_book_change(
        document_is_draft=False, book=old_change.book,
        author=expected_author, title=expected_title)

    assert old_change.snapshot_or_none
    assert BookChange.objects.count() == 2
    assert Book.objects.count() == 1
    assert BookSnapshot.objects.count() == 2

    old_snapshot = old_change.snapshot
    deleted_snapshot = moved_change.snapshot
    old_change.deleted = timezone.now()
    old_change.save()
    moved_change.document_date = old_time
    moved_change.save()

    deleted_snapshot.refresh_from_db()
    assert BookSnapshot.objects.count() == 2
    assert moved_change.snapshot == old_snapshot
    assert moved_change.snapshot.deleted is None
    assert moved_change.snapshot.updated >= old_snapshot.updated
    assert deleted_snapshot.deleted

    old_snapshot.refresh_from_db()
    assert moved_change.title == old_snapshot.title == expected_title
    assert moved_change.author == old_snapshot.author == expected_author


@pytest.mark.skip(
    'it is not the usable case cause you can change snapshots only via changes'
    ' and business entity(via deletion of business entity)')
@pytest.mark.django_db
@override_settings(DOCUMENTS_TOOLS={
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
def test_clear_deleted_snapshot():
    change = _create_book_change(document_is_draft=False)

    assert change.snapshot_or_none
    assert BookChange.objects.count() == 1
    assert Book.objects.count() == 1

    snapshot = change.snapshot
    snapshot.deleted = timezone.now()
    snapshot.save()

    assert snapshot.value is None
    assert snapshot.name is None


@pytest.mark.django_db
@override_settings(DOCUMENTS_TOOLS={
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
def test_move_change_to_already_created_snapshot():
    old_time = timezone.now() - timedelta(days=5)
    old_change = _create_book_change(
        document_is_draft=False, document_date=old_time)

    assert old_change.snapshot_or_none
    assert BookChange.objects.count() == 1
    assert Book.objects.count() == 1

    old_snapshot = old_change.snapshot
    change = _create_book_change(
        document_is_draft=False, book=old_change.book,
        title='not_expected_title', author=_create_author())
    new_document_date = change.document_date + timedelta(minutes=1)
    old_change.document_date = new_document_date
    old_change.save()

    old_snapshot.refresh_from_db()
    change.refresh_from_db()
    assert old_snapshot.deleted
    assert BookSnapshot.objects.filter(
        deleted__isnull=True).count() == 1
    assert change.snapshot == old_change.snapshot

    book = change.book
    assert book.title == old_change.title
    assert book.author == old_change.author


@pytest.mark.django_db
@override_settings(DOCUMENTS_TOOLS={
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
def test_snapshots_not_touched_fields_stay_the_same_in_last_snapshot():
    expected_title = 'expected_title'
    document_fields = ['author']
    time_1 = timezone.now() - timedelta(days=5)
    change_1 = _create_book_change(
        document_is_draft=False, document_date=time_1, title=expected_title)
    book = change_1.book
    time_2 = timezone.now() - timedelta(days=3)
    _create_book_change(
        document_is_draft=False, document_date=time_2,
        book=book, document_fields=document_fields,
        title='just_another_title')
    time_3 = timezone.now() - timedelta(days=2)
    change_3 = _create_book_change(
        document_is_draft=False, document_date=time_3,
        book=book, document_fields=document_fields, title='and_another_title')

    book.refresh_from_db()
    assert book.title == expected_title
    assert change_3.snapshot.title == expected_title
    assert BookSnapshot.objects.count() == 3
    assert BookChange.objects.count() == 3


@pytest.mark.django_db
def test_create_change_without_business_entity_creation():
    old_tariff_change = _create_book_change(document_is_draft=True)

    assert BookChange.objects.filter(
        document_is_draft=True).count() == 1
    assert Book.objects.count() == 0

    old_tariff_change.document_is_draft = False
    with pytest.raises(BusinessEntityCreationIsNotAllowedError):
        old_tariff_change.save()


@pytest.mark.django_db
@override_settings(DOCUMENTS_TOOLS={
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': True})
def test_use_initial_snapshot_from_right_documented_object():
    expected_title = 'name_2'
    old_time = timezone.now() - timedelta(days=5)
    _create_book_change(
        document_is_draft=False, title='title_1',
        document_date=old_time)
    document_fields = ['author']
    book = Book(title=expected_title, author=_create_author())
    book.save()
    change_2 = _create_book_change(
        document_is_draft=False, book=book,
        document_fields=document_fields)

    assert BookChange.objects.count() == 2
    assert Book.objects.count() == 2

    BookSnapshot.objects.filter(book=book).all().delete()
    change_2.book.save()

    assert change_2.book.title == expected_title
    assert BookChange.objects.count() == 2
    assert Book.objects.count() == 2


@pytest.mark.django_db
def test_create_change_attachment(
        book_change_model, book_change_attachment_model):
    book = Book.objects.create(title='foo', author=_create_author())
    book_change_attachment = book_change_attachment_model.objects.create(
        file='test.pdf')
    book_change = book_change_model.objects.create(
        book=book, document_is_draft=False, document_date=timezone.now(),
        document_fields=['title', 'author'], title='bar',
        attachment=book_change_attachment)

    assert book_change.attachment == book_change_attachment
