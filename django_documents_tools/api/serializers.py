from rest_framework import serializers
from django.db import models
from django.utils.module_loading import import_string

from django_documents_tools.utils import (
    check_subclass, validate_change_attrs, LimitedChoicesValidator)
from ..settings import tools_settings


NON_REQUIRED_KWARGS = {'required': False, 'allow_null': True}
STANDARD_READONLY_FIELDS = ('guid', 'type', 'version', 'created', 'updated', )


class BaseChangeSerializer(serializers.ModelSerializer):
    document_link = serializers.URLField(default='', allow_blank=True)

    def validate(self, attrs):
        # Ensure that new documented obj will be in correct state.
        validated_attrs = super().validate(attrs)
        validate_change_attrs(self.Meta.model, self.instance, validated_attrs)
        return validated_attrs

    class Meta:
        model = None
        fields = (
            *STANDARD_READONLY_FIELDS,
            'document_name', 'document_date', 'document_link',
            'document_is_draft', 'document_fields', 'attachment', 'snapshot')


class BaseSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = None
        fields = (
            *STANDARD_READONLY_FIELDS, 'document_fields', 'history_date')


class BaseDocumentedModelLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = None
        fields = (*STANDARD_READONLY_FIELDS, )


class BaseChangeAttachmentLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = None
        fields = (*STANDARD_READONLY_FIELDS, )


class BaseSnapshotLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = None
        fields = (*STANDARD_READONLY_FIELDS, )


class BaseChangeAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = None
        fields = (*STANDARD_READONLY_FIELDS, 'file')


def clone_serializer_field(field, **kwargs):
    return type(field)(*field._args, **{**field._kwargs, **kwargs})  # noqa: protected-access


def get_change_serializer_class(model, serializer_class, allowed_fields=None):  # noqa: to-many-locals
    """ Generating target model based change serializer

        1. Creating target model fk serializer field
        2. Copying explicitly defined fields with args={required=False}
        3. Copying implicitly defined fields with extra_kwargs={required:False}
    """

    if model._base_serializer:  # noqa: protected-access
        base_change_serializer = import_string(model._base_serializer)  # noqa: protected-access
    else:
        base_change_serializer = import_string(
            tools_settings.BASE_CHANGE_SERIALIZER)
    check_subclass(base_change_serializer, BaseChangeSerializer)

    opts = model._meta  # noqa: protected-access
    change_attachment_model = model.attachment.field.related_model
    documented_field = model._documented_model_field  # noqa: protected-access
    documented_model = serializer_class.Meta.model
    snapshot_model = model.snapshot.field.related_model

    fields = (base_change_serializer.Meta.fields + model._all_documented_fields  # noqa: protected-access
              + (documented_field, ))

    document_fields = serializers.ListField(
        allow_empty=False, required=True,
        validators=[LimitedChoicesValidator(model._all_documented_fields)])  # noqa: protected-access

    attrs = {}
    attrs['document_fields'] = document_fields
    implicit_fields_extra_kwargs = {}
    allowed_fields = allowed_fields or model._all_documented_fields # noqa: protected-access
    for name in allowed_fields:  # noqa: protected-access
        # NullBoolean already accepts `null` and fails on `required` arg
        if isinstance(opts.get_field(name), models.NullBooleanField):
            continue

        field = serializer_class._declared_fields.get(name)  # noqa: protected-access
        if field:
            attrs[name] = clone_serializer_field(field, **NON_REQUIRED_KWARGS)
        else:
            implicit_fields_extra_kwargs[name] = NON_REQUIRED_KWARGS

    base_serializer_extra_kwargs = getattr(
        base_change_serializer.Meta, 'extra_kwargs', {})
    attrs[documented_field] = get_documented_model_serializer(
        documented_model)(**NON_REQUIRED_KWARGS)
    attrs['attachment'] = get_change_attachment_link_serializer(
        change_attachment_model)(**NON_REQUIRED_KWARGS)
    attrs['snapshot'] = get_snapshot_link_serializer(snapshot_model)(
        read_only=True)
    attrs['Meta'] = type(
        'Meta', (base_change_serializer.Meta,),
        {'model': model, 'fields': fields, 'read_only_fields': [],
         'extra_kwargs': {
            **implicit_fields_extra_kwargs,
            **base_serializer_extra_kwargs}})

    name = f'{opts.object_name}Serializer'
    return type(name, (base_change_serializer,), attrs)


def get_documented_model_serializer(model):
    base = import_string(
        tools_settings.BASE_DOCUMENTED_MODEL_LINK_SERIALIZER)
    check_subclass(base, BaseDocumentedModelLinkSerializer)

    attrs = {
        'Meta': type(
            'Meta', (base.Meta,),
            {'model': model, 'ref_name': model._meta.object_name})}  # noqa: protected-access
    name = f'LinkTo{model._meta.object_name}Serializer'  # noqa: protected-access
    return type(name, (base,), attrs)


def get_snapshot_serializer(model, change_serializer):
    if model._base_serializer:  # noqa: protected-access
        base_snapshot_serializer = import_string(model._base_serializer)  # noqa: protected-access
    else:
        base_snapshot_serializer = import_string(
            tools_settings.BASE_SNAPSHOT_SERIALIZER)
    check_subclass(base_snapshot_serializer, BaseSnapshotSerializer)

    change_model = change_serializer.Meta.model
    documented_model_field = change_model._documented_model_field  # noqa: protected-access
    documented_model = getattr(
        model, change_model._documented_model_field).field.related_model  # noqa: protected-access
    fields = (base_snapshot_serializer.Meta.fields + change_model._all_documented_fields  # noqa: protected-access
              + (documented_model_field, ))

    attrs = {
        'Meta': type('Meta', (base_snapshot_serializer.Meta,),
                     {'model': model, 'fields': fields})}
    attrs[documented_model_field] = get_documented_model_serializer(
        documented_model)(**NON_REQUIRED_KWARGS)

    name = f'{model._meta.object_name}Serializer'  # noqa: protected-access
    bases = (base_snapshot_serializer, change_serializer)
    return type(name, bases, attrs)


def get_snapshot_link_serializer(model):
    base = import_string(tools_settings.BASE_SNAPSHOT_LINK_SERIALIZER)
    check_subclass(base, BaseSnapshotLinkSerializer)

    meta_opts = {'model': model, 'fields': base.Meta.fields}
    meta = type('Meta', (base.Meta,), meta_opts)
    name = f'{model._meta.object_name}LinkSerializer'  # noqa: protected-access
    return type(name, (base,), {'Meta': meta})


def get_change_attachment_link_serializer(model):
    base = import_string(tools_settings.BASE_CHANGE_ATTACHMENT_LINK_SERIALIZER)
    check_subclass(base, BaseChangeAttachmentLinkSerializer)

    meta_opts = {'model': model, 'fields': base.Meta.fields}
    meta = type('Meta', (base.Meta,), meta_opts)
    name = f'{model._meta.object_name}LinkSerializer'  # noqa: protected-access
    return type(name, (base, ), {'Meta': meta})


def get_change_attachment_serializer(model):
    if model._base_serializer:  # noqa: protected-access
        base_change_attachment_serializer = import_string(
            model._base_serializer)  # noqa: protected-access
    else:
        base_change_attachment_serializer = import_string(
            tools_settings.BASE_CHANGE_ATTACHMENT_SERIALIZER)
    check_subclass(
        base_change_attachment_serializer, BaseChangeAttachmentSerializer)

    fields = base_change_attachment_serializer.Meta.fields
    meta_opts = {'model': model, 'fields': fields}
    meta = type('Meta', (base_change_attachment_serializer.Meta,), meta_opts)
    attrs = {'Meta': meta}
    name = f'{model._meta.object_name}Serializer'  # noqa: protected-access
    return type(name, (base_change_attachment_serializer, ), attrs)
