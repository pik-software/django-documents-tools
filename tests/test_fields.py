from unittest.mock import Mock

from django.db.models import BooleanField, NullBooleanField, AutoField
from lib.documents import fields


def test_boolean():
    field = fields.copy_boolean(BooleanField())
    assert field.__class__ == NullBooleanField


def test_primary():
    field = AutoField(name='testname', primary_key=True)
    field.model = Mock(**{'_meta.model_name': 'testmodel'})
    field.attname = 'testattname'
    field = fields.copy_other(field)
    assert field.name == 'testmodel'
    assert not field.unique
    assert not field.primary_key
    assert field.db_index
    assert field.blank
    assert field.null


def test_unique():
    field = AutoField(name='testname', unique=True)
    field.model = Mock(**{'_meta.model_name': 'testmodel'})
    field.attname = 'testattname'
    field = fields.copy_other(field)
    assert field.name == 'testattname'
    assert not field.unique
    assert field.db_index
