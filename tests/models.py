from uuid import uuid4

from django.db import models

from django_documents_tools.models import (
    BaseDocumented, Changes, BaseChange, BaseSnapshot)


class BaseChangeModel(BaseChange):
    uid = models.UUIDField(default=uuid4, primary_key=True)

    class Meta:
        abstract = True


class BaseBaseSnapshotModel(BaseSnapshot):
    uid = models.UUIDField(default=uuid4, primary_key=True)

    class Meta:
        abstract = True


class Documented(BaseDocumented):
    uid = models.UUIDField(default=uuid4, primary_key=True)

    changes = Changes(
        inherit=True,
        excluded_fields=('deleted',),
        change_opts={
            'bases': (BaseChangeModel,)},
        snapshot_opts={
            'bases': (BaseBaseSnapshotModel,),
            'unit_size_in_days': 1})

    class Meta:
        abstract = True


class Address(models.Model):

    uid = models.UUIDField(default=uuid4, primary_key=True)
    country = models.CharField(max_length=128)
    city = models.CharField(max_length=128)
    street = models.CharField(max_length=256)
    house = models.CharField(max_length=64)
    zip_code = models.CharField(max_length=64)

    def __str__(self):
        return f'{self.country}, {self.city}, {self.street}, {self.house}'


class Author(models.Model):

    uid = models.UUIDField(default=uuid4, primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    date_of_death = models.DateField('Died', null=True, blank=True)
    address = models.OneToOneField(Address, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.last_name}, {self.first_name}'


class Book(Documented):

    uid = models.UUIDField(default=uuid4, primary_key=True)
    title = models.CharField(max_length=200)
    author = models.ForeignKey('Author', on_delete=models.SET_NULL, null=True)
    summary = models.TextField(max_length=1000, blank=True)
    isbn = models.CharField('ISBN', max_length=13, blank=True)
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return self.title
