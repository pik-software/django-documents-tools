import copy
import importlib
from typing import List

from django.conf import settings
from django.db import models
from django.apps import apps
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import ugettext, ugettext_lazy as _
from model_utils import FieldTracker

from lib.documents.exceptions import BusinessEntityCreationIsNotAllowedError
from lib.documents.fields import FIELDS_PROCESSORS
from lib.documents.manager import ChangeDescriptor, SnapshotDescriptor


class BaseChange(models.Model):
    _all_documented_fields: List[str] = None
    _documented_model_field: str = None
    _snapshot_model_field: str = None
    tracker: FieldTracker = None

    snapshot = None
    document_name = models.CharField(_('Название изменения'), max_length=255)
    document_date = models.DateTimeField(_('Дата применения'), db_index=True)
    document_link = models.URLField(
        _('Ссылка на документ'), default='', blank=True)
    document_is_draft = models.BooleanField(_('Черновик'), default=True)
    document_fields = ArrayField(
        models.CharField(_('Атрибуты'), max_length=255), default=list)
    deleted = models.DateTimeField(
        editable=False, null=True, blank=True, verbose_name=_('deleted'))

    def __str__(self):
        return f'{self.uid} - {self.document_name}'

    @property
    def snapshot_or_none(self):
        try:
            return self.snapshot
        except type(self).snapshot.RelatedObjectDoesNotExist:
            return None

    class Meta:
        abstract = True

    def get_snapshot_changes(self):
        return {field: getattr(self, field)
                for field in self.document_fields
                if field in self._all_documented_fields}

    def get_changes(self):
        return self.get_snapshot_changes()

    def apply_new(self):
        documented_model = self._meta.get_field(
            self._documented_model_field).remote_field.model
        kwargs = self.get_changes()
        new_documented = documented_model(**kwargs)
        new_documented.save()
        return new_documented

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(force_insert, force_update, using, update_fields)

        if not self.document_is_draft:
            new_documented = getattr(self, self._documented_model_field)
            creation = settings.CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED
            if new_documented is None and creation:
                new_documented = self.apply_new()
                setattr(self, self._documented_model_field, new_documented)
                super().save(update_fields=[self._documented_model_field])

            elif new_documented is None and not creation:
                raise BusinessEntityCreationIsNotAllowedError()

            applicable_date = timezone.now().date()
            new_documented.changes.apply_to_object(date=applicable_date)
            new_documented.save()
            self.refresh_from_db()


class BaseSnapshot(models.Model):

    EXCLUDED_STATE_FIELDS = (
        'uid', 'deleted', 'created', 'updated', 'version', 'history_date',
        'document_fields')

    document_fields = ArrayField(
        models.CharField(_('Заполненные атрибуты'), max_length=255),
        default=list)
    history_date = models.DateTimeField(
        _('Дата состояния объекта'), db_index=True)
    deleted = models.DateTimeField(
        editable=False, null=True, blank=True, verbose_name=_('deleted'))

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.uid} - {self.history_date}'

    @property
    def state(self):
        state = {}
        excluded_fields = (
            f'{self.changes.model._documented_model_field}_id',  # noqa: protected-access
            *self.EXCLUDED_STATE_FIELDS)
        for field in self._meta.get_fields():
            field_name = field.name
            if (field_name not in excluded_fields
                    and not field_name.startswith('_')
                    and field_name in self.document_fields):
                state[field_name] = getattr(self, field_name)
        return state

    def is_empty(self):
        return all(v is None for v in self.state.values())

    def clear_attrs(self):
        for field_name in self.state:
            setattr(self, field_name, None)


class Changes:

    DEFAULT_CHANGE_OPTS = {
        'bases': (BaseChange,),
        'manager_name': 'changes',
        'model_name': None,
        'table_name': None,
        'verbose_name': None,
        'verbose_name_template':  '{model._meta.verbose_name} change',
        'verbose_name_plural': None,
        'verbose_name_plural_template': '{model._meta.verbose_name} changes',
    }

    DEFAULT_SNAPSHOT_OPTS = {
        'bases': (BaseSnapshot,),
        'unit_size_in_days': None,
        'manager_name': 'snapshots',
        'model_name': None,
        'table_name': None,
        'verbose_name': None,
        'verbose_name_template':  '{model._meta.verbose_name} snapshot',
        'verbose_name_plural': None,
        'verbose_name_plural_template': '{model._meta.verbose_name} snapshot',
    }
    change_model = None
    snapshot_model = None
    module = None
    cls = None

    def __init__(
            self,
            inherit=False,
            included_fields=None,
            excluded_fields=None,
            fields_processors=None,
            app=None,
            change_opts=None,
            snapshot_opts=None
    ):
        self.fields_processors = fields_processors or FIELDS_PROCESSORS
        self.inherit = inherit
        self.app = app
        self.excluded_fields = excluded_fields or []
        self.included_fields = included_fields or []

        self.change_opts = {
            **self.DEFAULT_CHANGE_OPTS, **(change_opts or {})}
        self.snapshot_opts = {
            **self.DEFAULT_SNAPSHOT_OPTS, **(snapshot_opts or {})}

        unit_size = self.snapshot_opts.get('unit_size_in_days')
        if not isinstance(unit_size, int) or unit_size < 0:
            raise ValueError(
                'You have to provide a valid value for unit_size_in_days')

    def contribute_to_class(self, cls, name):
        self.module = cls.__module__
        self.cls = cls
        models.signals.class_prepared.connect(self.finalize, weak=False)

    def finalize(self, sender, **kwargs):
        inherited = False
        if self.cls is not sender:  # set in concrete
            inherited = self.inherit and issubclass(sender, self.cls)
            if not inherited:
                return  # set in abstract

        self.snapshot_model = self.create_snapshot_model(sender, inherited)
        self.change_model = self.create_change_model(sender, inherited)

        module = importlib.import_module(self.module)
        if inherited:
            # Make sure change model is in same module as concrete model
            module = importlib.import_module(self.change_model.__module__)

        setattr(module, self.change_model.__name__, self.change_model)
        descriptor = ChangeDescriptor(self.change_model)
        setattr(sender, self.change_opts['manager_name'], descriptor)
        sender._meta.change_manager_attribute = self.change_opts[  # noqa: protected-access
            'manager_name']

        setattr(module, self.snapshot_model.__name__, self.snapshot_model)
        descriptor = SnapshotDescriptor(self.snapshot_model)
        setattr(sender, self.snapshot_opts['manager_name'], descriptor)
        sender._meta.snapshot_manager_attribute = self.snapshot_opts[  # noqa: protected-access
            'manager_name']

    def create_change_model(self, model, inherited):
        """
        Create a change model to associate with the model provided.
        """

        attrs = {
            '__module__': self.get_module(model, inherited),
            '_documented_excluded_fields': self.excluded_fields,
        }
        opts = model._meta   # noqa protected-access

        primary_field_name = opts.model_name
        attrs['_documented_model_field'] = primary_field_name
        primary_field = next(
            field for field in opts.fields if field.primary_key)
        attrs['tracker'] = FieldTracker((primary_field_name, 'deleted'))

        src_fields = self.get_fields(model)
        attrs.update(self.copy_fields([primary_field, *src_fields]))
        documented_fields = tuple(field.name for field in src_fields)
        attrs['_all_documented_fields'] = documented_fields
        attrs['permitted_fields'] = {
            '{app_label}.change_{model_name}': (
                'change_name', 'document_date', 'document_link',
                'document_is_draft', 'documented_fields',
                primary_field_name, *documented_fields)}
        attrs['snapshot'] = models.ForeignKey(
            self.snapshot_model, on_delete=models.DO_NOTHING,
            related_name='changes', null=True, blank=True,
            verbose_name=self.snapshot_model._meta.verbose_name.title())  # noqa: protected-access
        base_meta = {
            'ordering': ('-document_date',),
            'get_latest_by': 'document_date'}
        attrs.update(Meta=type("Meta", (), self.get_meta_options(
            model, base_meta, self.change_opts)))
        if self.change_opts['table_name'] is not None:
            attrs["Meta"].db_table = self.change_opts['table_name']
        name = (
            self.change_opts['model_name']
            if self.change_opts['model_name'] is not None
            else '%sChange' % opts.object_name)
        return type(str(name), self.change_opts['bases'], attrs)

    def create_snapshot_model(self, model, inherited):
        """
        Create an documented object snapshot model
        """
        attrs = {
            '__module__': self.get_module(model, inherited),
            'unit_size_in_days': self.snapshot_opts['unit_size_in_days']}

        src_fields = self.get_fields(model)
        fields = self.copy_fields(src_fields)
        documented_fields = tuple(field.name for field in src_fields)
        attrs['permitted_fields'] = {
            '{app_label}.change_{model_name}': (*documented_fields,)}
        attrs.update(fields)
        opts = model._meta   # noqa protected-access
        attrs[opts.model_name] = models.ForeignKey(
            model, on_delete=models.DO_NOTHING,
            related_name='snapshots', null=True, blank=True,
            verbose_name=self.cls._meta.verbose_name.title())  # noqa: protected-access
        base_meta = {
            'ordering': ('-history_date',),
            'get_latest_by': 'history_date'}
        attrs.update(Meta=type('Meta', (), self.get_meta_options(
            model, base_meta, self.snapshot_opts)))
        if self.snapshot_opts['table_name'] is not None:
            attrs['Meta'].db_table = self.snapshot_opts['table_name']
        name = (
            self.snapshot_opts['model_name']
            if self.snapshot_opts['model_name'] is not None
            else '%sSnapshot' % model._meta.object_name)  # noqa: protected-access
        return type(str(name), self.snapshot_opts['bases'], attrs)

    def get_module(self, model, inherited):
        module = self.module
        app_module = '%s.models' % model._meta.app_label  # noqa: protected-access
        if inherited:
            return model.__module__
        if model.__module__ != self.module:
            return self.module
        if app_module != self.module:
            app = apps.app_configs[model._meta.app_label]  # noqa: protected-access
            return app.name
        return module

    def get_meta_options(self, model, meta_attrs, model_opts):
        """
        Returns a dictionary of fields that will be added to
        the Meta inner class of the historical record model.
        """

        meta_fields = {'abstract': None, **meta_attrs}

        if model_opts['verbose_name']:
            name = model_opts['verbose_name']
        else:
            template = model_opts['verbose_name_template']
            name = ugettext(template.format(model=model))

        if model_opts['verbose_name_plural']:
            name_plural = model_opts['verbose_name_plural']
        else:
            template = model_opts['verbose_name_plural_template']
            name_plural = ugettext(template.format(model=model))

        meta_fields['verbose_name'] = name
        meta_fields['verbose_name_plural'] = name_plural
        if self.app:
            meta_fields['app_label'] = self.app
        return meta_fields

    def get_fields(self, model):
        fields = []
        for field in model._meta.fields:  # noqa: protected-access
            is_documented = (
                not field.primary_key
                and (field.editable or field.name in self.included_fields)
                and field.name not in self.excluded_fields)
            if is_documented:
                fields.append(field)
        return fields

    def copy_fields(self, fields_included):
        """
        Creates copies of the model's original fields, returning
        a dictionary mapping field name to copied field object.
        """
        fields = {}
        for field in fields_included:
            field = copy.copy(field)
            field.remote_field = copy.copy(field.remote_field)
            if isinstance(field, models.BooleanField):
                field = self.fields_processors[models.BooleanField](field)
            if isinstance(field, models.OrderWrt):
                field = self.fields_processors[models.OrderWrt](field)
            if isinstance(field, models.ForeignKey):
                field = self.fields_processors[models.ForeignKey](field)
            else:
                field = self.fields_processors[None](field)
            field.blank = True
            field.null = True
            fields[field.name] = field
        return fields
