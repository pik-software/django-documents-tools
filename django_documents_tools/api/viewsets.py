from rest_framework.viewsets import ModelViewSet
from django.utils.module_loading import import_string

from django_documents_tools.utils import check_subclass
from .filters import (
    get_change_filter, get_snapshot_filter, get_change_attachment_filter)
from .serializers import (
    get_change_serializer_class, get_snapshot_serializer,
    get_change_attachment_serializer)
from ..settings import tools_settings


class BaseDocumentedViewSet(ModelViewSet):
    allow_history = False

    lookup_field = 'uid'
    lookup_url_kwarg = 'guid'
    serializer_class = None
    filter_class = None
    select_related_fields = ()

    def get_queryset(self):
        queryset = self.serializer_class.Meta.model.objects.all()
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        return queryset


class BaseChangeViewSet(BaseDocumentedViewSet):
    allow_history = True

    ordering = ('document_date', )
    search_fields = ('document_name', )


class BaseSnapshotViewSet(BaseDocumentedViewSet):
    ordering = ('history_date',)
    search_fields = ('changes__document_name',)


class BaseChangeAttachmentViewSet(BaseDocumentedViewSet):
    allow_history = True
    select_related_fields = ('change',)


def get_change_viewset(documented_viewset):
    if not getattr(documented_viewset, '_allowed_changes', True):
        return None
    documented_serializer = documented_viewset.serializer_class
    documented_model = documented_serializer.Meta.model
    document_manager = getattr(documented_model, 'changes', None)
    if document_manager is None:
        return None
    model = document_manager.model

    if model._base_viewset:  # noqa: protected-access
        base_change_viewset = import_string(model._base_viewset)  # noqa: protected-access
    else:
        base_change_viewset = import_string(tools_settings.BASE_CHANGE_VIEWSET)

    check_subclass(base_change_viewset, BaseChangeViewSet)

    document_serializer = get_change_serializer_class(
        model, documented_viewset.serializer_class)

    document_filter = get_change_filter(model, documented_viewset)

    select_related_fields = (
        model._documented_model_field, # noqa: protected-access
        *documented_viewset.select_related_fields)

    attrs = {'serializer_class': document_serializer,
             'filter_class': document_filter,
             'select_related_fields': select_related_fields,
             '__doc__': base_change_viewset.__doc__}
    name = f'{model._meta.object_name}ViewSet'  # noqa: protected-access
    return type(name, (base_change_viewset,), attrs)


def get_snapshot_viewset(change_viewset, documented_viewset):
    change_serializer = change_viewset.serializer_class
    change_model = change_serializer.Meta.model
    snapshot_model = change_model._meta.get_field('snapshot').related_model  # noqa: protected-access

    if snapshot_model._base_viewset:  # noqa: protected-access
        base_snapshot_viewset = import_string(snapshot_model._base_viewset)  # noqa: protected-access
    else:
        base_snapshot_viewset = import_string(
            tools_settings.BASE_SNAPSHOT_VIEWSET)

    check_subclass(base_snapshot_viewset, BaseSnapshotViewSet)

    snapshot_serializer = get_snapshot_serializer(
        snapshot_model, change_serializer)
    snapshot_filter = get_snapshot_filter(snapshot_model, documented_viewset)

    attrs = {'serializer_class': snapshot_serializer,
             'filter_class': snapshot_filter,
             'select_related_fields': change_viewset.select_related_fields,
             '__doc__': base_snapshot_viewset.__doc__}

    name = f'{snapshot_model._meta.object_name}ViewSet'  # noqa: protected-access
    return type(name, (base_snapshot_viewset, ), attrs)


def get_change_attachment_viewset(change_viewset):
    change_model = change_viewset.serializer_class.Meta.model
    change_filter = change_viewset.filter_class
    change_attachment_model = (
        change_model._meta.get_field('attachment').related_model)  # noqa: protected-access

    change_attachment_serializer = get_change_attachment_serializer(
        change_attachment_model)

    if change_attachment_model._base_viewset:  # noqa: protected-access
        base_change_attachment_viewset = import_string(
            change_attachment_model._base_viewset)  # noqa: protected-access
    else:
        base_change_attachment_viewset = import_string(
            tools_settings.BASE_CHANGE_ATTACHMENT_VIEWSET)

    check_subclass(base_change_attachment_viewset, BaseChangeAttachmentViewSet)

    change_attachment_filter = get_change_attachment_filter(
        change_attachment_model, change_filter)
    attrs = {
        'serializer_class': change_attachment_serializer,
        'filter_class': change_attachment_filter,
        '__doc__': base_change_attachment_viewset.__doc__
    }

    name = f'{change_attachment_model._meta.object_name}ViewSet'  # noqa: protected-access
    return type(name, (base_change_attachment_viewset,), attrs)
