from collections import ChainMap

from django.conf import settings as django_settings
from django.test.signals import setting_changed


SETTINGS_NAME = 'DOCUMENTS_TOOLS'
BASE_SNAPSHOT_SERIALIZER = (
    'django_documents_tools.api.serializers.BaseSnapshotSerializer')
BASE_SNAPSHOT_LINK_SERIALIZER = (
    'django_documents_tools.api.serializers.BaseSnapshotLinkSerializer')
BASE_SNAPSHOT_VIEWSET = (
    'django_documents_tools.api.viewsets.BaseSnapshotViewSet')
BASE_CHANGE_SERIALIZER = (
    'django_documents_tools.api.serializers.BaseChangeSerializer')
BASE_CHANGE_VIEWSET = 'django_documents_tools.api.viewsets.BaseChangeViewSet'
BASE_CHANGE_ATTACHMENT_SERIALIZER = (
    'django_documents_tools.api.serializers.BaseChangeAttachmentSerializer')
BASE_CHANGE_ATTACHMENT_VIEWSET = (
    'django_documents_tools.api.viewsets.BaseChangeAttachmentViewSet')
BASE_CHANGE_ATTACHMENT_LINK_SERIALIZER = (
    'django_documents_tools.api.serializers.'
    'BaseChangeAttachmentLinkSerializer')
BASE_DOCUMENTED_MODEL_LINK_SERIALIZER = (
    'django_documents_tools.api.serializers.BaseDocumentedModelLinkSerializer')


def _reload_settings(*args, **kwargs):
    setting = kwargs['setting']
    if setting == SETTINGS_NAME:
        tools_settings.reload_user_settings()


def _get_user_settings():
    return getattr(django_settings, SETTINGS_NAME, {})


class ToolsSettings(ChainMap): # noqa: too-many-ancestors

    DEFAULT_VALUE = object()
    DEFAULT_SETTINGS = {
        'BASE_SNAPSHOT_SERIALIZER': BASE_SNAPSHOT_SERIALIZER,
        'BASE_SNAPSHOT_LINK_SERIALIZER': BASE_SNAPSHOT_LINK_SERIALIZER,
        'BASE_SNAPSHOT_VIEWSET': BASE_SNAPSHOT_VIEWSET,
        'BASE_CHANGE_SERIALIZER': BASE_CHANGE_SERIALIZER,
        'BASE_CHANGE_VIEWSET': BASE_CHANGE_VIEWSET,
        'BASE_CHANGE_ATTACHMENT_SERIALIZER': BASE_CHANGE_ATTACHMENT_SERIALIZER,
        'BASE_CHANGE_ATTACHMENT_VIEWSET': BASE_CHANGE_ATTACHMENT_VIEWSET,
        'BASE_CHANGE_ATTACHMENT_LINK_SERIALIZER': (
            BASE_CHANGE_ATTACHMENT_LINK_SERIALIZER),
        'BASE_DOCUMENTED_MODEL_LINK_SERIALIZER': (
            BASE_DOCUMENTED_MODEL_LINK_SERIALIZER),
        'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': False
    }

    def __init__(self):
        user_settings = _get_user_settings()
        super().__init__(user_settings, self.DEFAULT_SETTINGS.copy())

    def __getattr__(self, name):
        value = self.get(name, self.DEFAULT_VALUE)
        if value is self.DEFAULT_VALUE:
            raise AttributeError(
                f"Tools settings object has no attribute '{name}'")
        return value

    def reload_user_settings(self):
        self.maps[0] = _get_user_settings()


tools_settings = ToolsSettings() # noqa: invalid-name
setting_changed.connect(_reload_settings)
