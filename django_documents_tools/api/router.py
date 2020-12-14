from rest_framework.routers import DefaultRouter

from .viewsets import (
    get_change_viewset, get_snapshot_viewset, get_change_attachment_viewset)


def _get_viewset_name(viewset):
    return viewset.serializer_class.Meta.model._meta.model_name  # noqa: protected-access


class DocumentedRouter(DefaultRouter):

    def register_viewsets(self, orig_viewset):
        change_viewset = get_change_viewset(orig_viewset)
        if change_viewset:
            name = _get_viewset_name(change_viewset)
            super().register(f'{name}-list', change_viewset, name)

            snapshot_viewset = get_snapshot_viewset(
                change_viewset, orig_viewset)
            if snapshot_viewset:
                name = _get_viewset_name(snapshot_viewset)  # noqa: protected-access
                super().register(f'{name}-list', snapshot_viewset, name)

            change_attachment_viewset = get_change_attachment_viewset(
                change_viewset)
            if change_attachment_viewset:
                name = _get_viewset_name(change_attachment_viewset)  # noqa: protected-access
                super().register(
                    f'{name}-list', change_attachment_viewset, name)

    def register(self, prefix, viewset, basename=None):
        if getattr(viewset, 'allow_changes', True):
            self.register_viewsets(viewset)
        super().register(prefix, viewset, basename)
