from django.db import models
from rest_framework import serializers

from core.api.serializers import StandardizedModelSerializer


NON_REQUIRED_KWARGS = {'required': False, 'allow_null': True}


class ChangeSerializerBase(StandardizedModelSerializer):
    document_link = serializers.URLField(default="", allow_blank=True)
    document_fields = serializers.ListField(default=[])

    class Meta:
        model = None
        fields = (
            '_uid', '_type', '_version', 'created', 'updated', 'document_name',
            'document_date', 'document_link', 'document_is_draft',
            'document_fields')


class SnapshotSerializerBase(StandardizedModelSerializer):
    class Meta:
        model = None
        fields = (
            '_uid', '_type', '_version', 'created', 'updated',
            'document_fields', 'history_date')


def _clone_serializer_field(field, **kwargs):
    return type(field)(*field._args, **{**field._kwargs, **kwargs})  # noqa: protected-access


def get_change_serializer_class(model, serializer_class, allowed_fields=None):
    """ Generating target model based change serializer

        1. Creating target model fk serializer field
        2. Copying explicitly defined fields with args={required=False}
        3. Copying implicitly defined fields with extra_kwargs={required:False}
    """

    opts = model._meta  # noqa: protected-access
    documented_field = model._documented_model_field  # noqa: protected-access
    fields = (ChangeSerializerBase.Meta.fields + model._all_documented_fields  # noqa: protected-access
              + (documented_field, ))

    attrs = {}
    implicit_fields_extra_kwargs = {}
    allowed_fields = allowed_fields or model._all_documented_fields # noqa: protected-access
    for name in allowed_fields:  # noqa: protected-access
        # NullBoolean already accepts `null` and fails on `required` arg
        if isinstance(opts.get_field(name), models.NullBooleanField):
            continue

        field = serializer_class._declared_fields.get(name)  # noqa: protected-access
        if field:
            attrs[name] = _clone_serializer_field(field, **NON_REQUIRED_KWARGS)
        else:
            implicit_fields_extra_kwargs[name] = NON_REQUIRED_KWARGS

    attrs[documented_field] = serializer_class(**NON_REQUIRED_KWARGS)
    attrs['Meta'] = type(
        'Meta', (ChangeSerializerBase.Meta,),
        {'model': model, 'fields': fields, 'read_only_fields': [],
         'extra_kwargs': implicit_fields_extra_kwargs})

    name = f'{opts.object_name}Serializer'
    return type(name, (ChangeSerializerBase,), attrs)


def get_snapshot_serializer(model, change_serializer):
    change_model = change_serializer.Meta.model
    fields = (SnapshotSerializerBase.Meta.fields
              + change_model._all_documented_fields)  # noqa: protected-access

    attrs = {
        'Meta': type('Meta', (SnapshotSerializerBase.Meta,),
                     {'model': model, 'fields': fields})}

    name = f'{model._meta.object_name}Serializer'  # noqa: protected-access
    return type(name, (SnapshotSerializerBase, change_serializer), attrs)
