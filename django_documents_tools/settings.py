from collections import ChainMap

from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework import serializers, viewsets


DEFAULT_SETTINGS = {
    'BASE_SERIALIZER': serializers.ModelSerializer,
    'BASE_VIEW_SET': viewsets.ModelViewSet,
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': False
}


class ToolsSettings(ChainMap): # noqa: too-many-ancestors

    DEFAULT = object()

    def __getattr__(self, name):
        value = self.get(name, self.DEFAULT)
        if value is self.DEFAULT:
            raise AttributeError(
                f"Tools settings object has no attribute '{name}'")
        elif isinstance(value, str):
            value = import_string(value)
        return value


user_settings = getattr(settings, 'DOCUMENTS_TOOLS', {}) # noqa: invalid-name
tools_settings = ToolsSettings(user_settings, DEFAULT_SETTINGS) # noqa: invalid-name
