from django.contrib.postgres.fields import ArrayField
from rest_framework.fields import DateTimeField
from rest_framework_filters import (
    FilterSet, RelatedFilter, IsoDateTimeFilter, BaseCSVFilter, AutoFilter)


UID_LOOKUPS = ('exact', 'gt', 'gte', 'lt', 'lte', 'in', 'isnull')
STRING_LOOKUPS = (
    'exact', 'iexact', 'in', 'startswith', 'endswith', 'contains', 'contains',
    'isnull')
DATE_LOOKUPS = ('exact', 'gt', 'gte', 'lt', 'lte', 'in')
BOOLEAN_LOOKUPS = ('exact', 'isnull')
ARRAY_LOOKUPS = ['contains', 'contained_by', 'overlap', 'len', 'isnull']


class ArrayFilter(BaseCSVFilter, AutoFilter):
    DEFAULT_LOOKUPS = ARRAY_LOOKUPS

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('lookups', self.DEFAULT_LOOKUPS)
        super().__init__(*args, **kwargs)


class ChangeFilterBase(FilterSet):
    uid = AutoFilter(lookups=UID_LOOKUPS)
    updated = AutoFilter(lookups=DATE_LOOKUPS)
    document_date = AutoFilter(lookups=DATE_LOOKUPS)
    document_name = AutoFilter(lookups=STRING_LOOKUPS)
    document_link = AutoFilter(lookups=STRING_LOOKUPS)
    document_is_draft = AutoFilter(lookups=BOOLEAN_LOOKUPS)
    document_fields = ArrayFilter()

    class Meta:
        model = None
        fields = {}
        filter_overrides = {
            DateTimeField: {'filter_class': IsoDateTimeFilter},
            ArrayField: {'filter_class': ArrayFilter}}


class SnapshotFilterBase(FilterSet):
    uid = AutoFilter(lookups=UID_LOOKUPS)
    updated = AutoFilter(lookups=DATE_LOOKUPS)
    history_date = AutoFilter(lookups=DATE_LOOKUPS)

    class Meta:
        model = None
        fields = {}
        filter_overrides = {
            DateTimeField: {'filter_class': IsoDateTimeFilter},
            ArrayField: {'filter_class': ArrayFilter}}


def get_change_filter(model, orig_viewset):
    documented_model = orig_viewset.serializer_class.Meta.model
    documented_field = model._documented_model_field  # noqa: protected-access
    documented_filter = RelatedFilter(
        orig_viewset.filter_class, name=documented_field,
        queryset=documented_model.objects.all())
    meta = type(f'Meta', (ChangeFilterBase.Meta,), {'model': model})

    attrs = {documented_field: documented_filter, 'Meta': meta}
    name = f'{model._meta.object_name}Filter'  # noqa: protected-access
    return type(name, (ChangeFilterBase,), attrs)


def get_snapshot_filter(model, change_viewset):
    change_filter = change_viewset.filter_class
    change_sub_filter = RelatedFilter(
        change_filter, name='changes',
        queryset=change_filter.Meta.model.objects.all())

    meta = type(f'Meta', (SnapshotFilterBase.Meta, ), {'model': model})
    attrs = {'changes': change_sub_filter, 'Meta': meta}
    name = f'{model._meta.object_name}Filter'  # noqa: protected-access
    return type(name, (SnapshotFilterBase, ), attrs)
