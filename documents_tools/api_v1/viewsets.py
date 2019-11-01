from .filters import get_change_filter, get_snapshot_filter
from .serializers import (
    get_change_serializer_class, get_snapshot_serializer,
    get_documented_model_serializer, NON_REQUIRED_KWARGS)
from ..settings import tools_settings


class ChangeViewSetBase(tools_settings.BASE_VIEW_SET):
    lookup_field = 'uid'
    lookup_url_kwarg = '_uid'
    ordering = ('document_date', )
    ordering_fields = ('document_date', 'updated', 'uid', )
    search_fields = ('document_name', )
    serializer_class = None
    filter_class = None
    select_related_fields = ()

    allow_history = True

    def get_queryset(self):
        queryset = self.serializer_class.Meta.model.objects.all()
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        return queryset


class SnapshotViewSetBase(ChangeViewSetBase):
    allow_history = False
    search_fields = ('changes__document_name',)
    ordering_fields = ('history_date', 'updated', 'uid',)
    ordering = ('history_date',)


def get_change_viewset(documented_viewset):
    if not getattr(documented_viewset, '_allowed_changes', True):
        return None
    documented_serializer = documented_viewset.serializer_class
    documented_model = documented_serializer.Meta.model
    document_manager = getattr(documented_model, 'changes', None)
    if document_manager is None:
        return None
    model = document_manager.model

    document_serializer = get_change_serializer_class(
        model, documented_viewset.serializer_class)

    document_filter = get_change_filter(model, documented_viewset)

    select_related_fields = (
        model._documented_model_field, # noqa: protected-access
        *documented_viewset.select_related_fields)

    attrs = {'serializer_class': document_serializer,
             'filter_class': document_filter,
             'select_related_fields': select_related_fields,
             '__doc__': ChangeViewSetBase.__doc__}

    bases = model.bases_viewsets + (ChangeViewSetBase,)
    name = f'{model._meta.object_name}ViewSet'  # noqa: protected-access
    return type(name, bases, attrs)


def get_snapshot_viewset(change_viewset, documented_viewset):
    change_serializer = change_viewset.serializer_class
    change_model = change_serializer.Meta.model
    snapshot_model = change_model._meta.get_field('snapshot').related_model  # noqa: protected-access
    documented_model = getattr(
        snapshot_model,
        change_model._documented_model_field).field.related_model  # noqa: protected-access
    snapshot_serializer = get_snapshot_serializer(
        snapshot_model, change_serializer)
    documented_model_name = documented_model._meta.model_name  # noqa: protected-access
    snapshot_serializer._declared_fields[documented_model_name] = (  # noqa: protected-access
        get_documented_model_serializer(
            documented_model)(**NON_REQUIRED_KWARGS))
    snapshot_filter = get_snapshot_filter(snapshot_model, change_viewset)

    attrs = {'serializer_class': snapshot_serializer,
             'filter_class': snapshot_filter,
             'select_related_fields': change_viewset.select_related_fields,
             '__doc__': SnapshotViewSetBase.__doc__}

    bases = snapshot_model.bases_viewsets + (SnapshotViewSetBase,)
    name = f'{snapshot_model._meta.object_name}ViewSet'  # noqa: protected-access
    return type(name, bases, attrs)
