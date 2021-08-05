import copy
import logging
import importlib
from typing import List

from django.apps import apps
from django.utils import timezone
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.db.models.signals import class_prepared, post_save
from django.utils.translation import ugettext, ugettext_lazy as _
from model_utils import FieldTracker

from .fields import FIELDS_PROCESSORS
from .manager import ChangeDescriptor, SnapshotDescriptor
from .exceptions import ChangesAreNotCreatedYetError
from .utils import (
    get_change_attachment_file_path, LimitedChoicesValidator,
    apply_change_receiver)


LOGGER = logging.getLogger(__name__)


class Dated(models.Model):

    created = models.DateTimeField(
        editable=False, auto_now_add=True, db_index=True,
        verbose_name=_('created'))
    updated = models.DateTimeField(
        editable=False, auto_now=True, db_index=True,
        verbose_name=_('updated'))
    deleted = models.DateTimeField(
        editable=False, null=True, blank=True, db_index=True,
        verbose_name=_('deleted'))

    class Meta:
        abstract = True


class BaseDocumented(Dated):

    changes = None

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None,  # noqa: arguments-differ
             update_fields=None, apply_documents=True):
        if self.deleted:
            deletion_time = timezone.now()
            self.snapshots.filter(
                deleted__isnull=True).update(
                deleted=deletion_time, updated=deletion_time)
            self.changes.filter(
                deleted__isnull=True).update(
                deleted=deletion_time, updated=deletion_time)

        if apply_documents:
            try:
                self.changes.apply_to_object(timezone.now().date())
            except ChangesAreNotCreatedYetError:
                LOGGER.info('Changes are not created yet')

        super().save(force_insert, force_update, using, update_fields)


class BaseChange(Dated):

    _help_text = _(
        'Изменение - некоторый текстовый или материальный объект, являющийся, '
        'с точки зрения "бизнеса", интерфейсом ввода данных в сервис. '
        'Как правило, документы моделируются через создание объектов типа '
        'логическая история бизнес-сущности')

    _all_documented_fields: List[str] = None
    _documented_model_field: str = None
    _snapshot_model_field: str = None
    tracker: FieldTracker = None

    snapshot = None
    attachment = None
    document_name = models.CharField(_('Название изменения'), max_length=255)
    document_date = models.DateTimeField(_('Дата применения'), db_index=True)
    document_link = models.URLField(
        _('Ссылка на документ'), default='', blank=True)
    document_is_draft = models.BooleanField(_('Черновик'), default=True)
    document_fields = None

    def __str__(self):
        return f'{self.pk} - {self.document_name}'

    @property
    def snapshot_or_none(self):
        try:
            return self.snapshot
        except type(self).snapshot.RelatedObjectDoesNotExist:
            return None

    class Meta:
        abstract = True

    def get_documented_fields(self):
        return [
            field for field in self.document_fields
            if field in self._all_documented_fields
        ]

    def get_snapshot_changes(self):
        return {
            field: getattr(self, field)
            for field in self.get_documented_fields()
        }

    def get_changes(self):
        return self.get_snapshot_changes()

    def apply_new(self):
        documented_model = self._meta.get_field(
            self._documented_model_field).remote_field.model
        kwargs = self.get_changes()
        new_documented = documented_model(**kwargs)
        new_documented.save(apply_documents=False)
        return new_documented

    def save(self, *args, **kwargs):  # noqa: pylint==arguments-differ
        super().save(*args, **kwargs)

        # We are using `post_save` signal for document processing.
        # See `finalize` method in `Changes` for more info.


class BaseChangeAttachment(Dated):
    _help_text = _(
        'Вложение к документу - модель для хранения пользовательского файла, '
        'прикрепленного к документу')

    file = models.FileField(
        verbose_name=_('вложение'), upload_to=get_change_attachment_file_path)

    class Meta:
        abstract = True


class BaseSnapshot(Dated):

    _help_text = _(
        'Снапшот - состояние бизнес-объекта на определенный момент времени. '
        'Можно сказать, что снапшот является совокупностью всех логических '
        'изменений бизнес-объекта на минимальную единицу времени. '
        'На один момент времени может существовать только один снапшот. '
        'Снапшоты вычисляются на основе логической истории')

    EXCLUDED_STATE_FIELDS = (
        'guid', 'deleted', 'created', 'updated', 'version', 'history_date',
        'document_fields')

    changes = None
    document_fields = ArrayField(
        models.CharField(_('Заполненные атрибуты'), max_length=255),
        default=list)
    history_date = models.DateTimeField(
        _('Дата состояния объекта'), db_index=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.pk} - {self.history_date}'

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

    @property
    def document_fields_from_changes(self):
        result = set()

        for change in self.changes.all():
            result.update(change.get_documented_fields())

        return result


class Changes:

    DEFAULT_CHANGE_ATTACHMENT_OPTIONS = {
        'bases': (BaseChangeAttachment,),
        'base_viewset': None,
        'base_serializer': None,
        'filterset': None,
        'model_name': None,
        'table_name': None,
        'verbose_name': None,
        'verbose_name_template': (
            '{model._meta.verbose_name} change attachment'),
        'verbose_name_plural': None,
        'verbose_name_plural_template': (
            '{model._meta.verbose_name} change attachments'),
    }

    DEFAULT_CHANGE_OPTS = {
        'bases': (BaseChange,),
        'base_viewset': None,
        'base_serializer': None,
        'filterset': None,
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
        'base_serializer': None,
        'base_viewset': None,
        'filterset': None,
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
    change_attachment_model = None
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
            snapshot_opts=None,
            change_attachment_opts=None,
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
        self.change_attachment_opts = {
            **self.DEFAULT_CHANGE_ATTACHMENT_OPTIONS,
            **(change_attachment_opts or {})
        }

        unit_size = self.snapshot_opts.get('unit_size_in_days')
        if not isinstance(unit_size, int) or unit_size < 0:
            raise ValueError(
                'You have to provide a valid value for unit_size_in_days')

        if not bool(self.excluded_fields) ^ bool(self.included_fields):
            raise ValueError(
                'You have to provide either `excluded_fields` or '
                '`included_fields`')

    def contribute_to_class(self, cls, name):
        self.module = cls.__module__
        self.cls = cls
        class_prepared.connect(self.finalize, weak=False)

    def finalize(self, sender, **kwargs):
        inherited = False
        if self.cls is not sender:  # set in concrete
            inherited = self.inherit and issubclass(sender, self.cls)
            if not inherited:
                return  # set in abstract

        self.change_attachment_model = self.create_change_attachment_model(
            sender, inherited)
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

        setattr(
            module, self.change_attachment_model.__name__,
            self.change_attachment_model)

        post_save.connect(apply_change_receiver, sender=self.change_model)

    def create_change_model(self, model, inherited):
        """
        Create a change model to associate with the model provided.
        """

        attrs = {
            '__module__': self.get_module(model, inherited),
            '_documented_excluded_fields': self.excluded_fields,
            '_base_viewset': self.change_opts['base_viewset'],
            '_filterset': self.change_opts['filterset'],
            '_base_serializer': self.change_opts['base_serializer'],
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
                'document_name', 'document_date', 'document_link',
                'document_is_draft', 'document_fields', 'attachment',
                primary_field_name, *documented_fields),
            '{app_label}.add_{model_name}': (
                'document_name', 'document_date', 'document_link',
                'document_is_draft', 'document_fields', 'attachment',
                primary_field_name, *documented_fields)}
        attachment_title = (
            self.change_attachment_model._meta.verbose_name.title())  # noqa: protected-access
        attrs['snapshot'] = models.ForeignKey(
            self.snapshot_model, on_delete=models.DO_NOTHING,
            related_name='changes', null=True, blank=True,
            verbose_name=self.snapshot_model._meta.verbose_name.title())  # noqa: protected-access
        attrs['attachment'] = models.OneToOneField(
            self.change_attachment_model, on_delete=models.SET_NULL,
            related_name='change', null=True, blank=True,
            verbose_name=attachment_title)  # noqa: protected-access
        attrs['document_fields'] = ArrayField(
            models.CharField(_('Атрибуты'), max_length=255), default=list,
            validators=[LimitedChoicesValidator(sorted(documented_fields))])
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

    def create_change_attachment_model(self, model, inherited):
        """
        Create change attachment model
        """

        opts = model._meta  # noqa protected-access
        attrs = {
            '__module__': self.get_module(model, inherited),
            '_base_viewset': self.change_attachment_opts['base_viewset'],
            '_base_serializer': self.change_attachment_opts['base_serializer'],
            '_filterset': self.change_attachment_opts['filterset'],
        }
        attrs['permitted_fields'] = {
            '{app_label}.change_{model_name}': ('file',)
        }
        base_meta_opts = {
            'ordering': ('-created',),
            'db_table': self.change_attachment_opts.get('table_name')
        }

        if self.change_attachment_opts['model_name']:
            name = self.change_attachment_opts['model_name']
        else:
            name = f'{opts.object_name}ChangeAttachment'

        meta_opts = self.get_meta_options(
            model, base_meta_opts, self.change_attachment_opts)
        attrs['Meta'] = type('Meta', (), meta_opts)

        return type(name, self.change_attachment_opts['bases'], attrs)

    def create_snapshot_model(self, model, inherited):
        """
        Create an documented object snapshot model
        """
        attrs = {
            '__module__': self.get_module(model, inherited),
            'unit_size_in_days': self.snapshot_opts['unit_size_in_days'],
            '_base_viewset': self.snapshot_opts['base_viewset'],
            '_base_serializer': self.snapshot_opts['base_serializer'],
            '_filterset': self.snapshot_opts['filterset'],
        }

        src_fields = self.get_fields(model)
        fields = self.copy_fields(src_fields)
        documented_fields = tuple(field.name for field in src_fields)
        attrs['permitted_fields'] = {
            '{app_label}.change_{model_name}': (*documented_fields,),
            '{app_label}.add_{model_name}': (*documented_fields,)}
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
            if field.primary_key or not field.editable:
                continue

            if self.included_fields and field.name in self.included_fields:
                fields.append(field)
            elif (self.excluded_fields
                  and field.name not in self.excluded_fields):
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
