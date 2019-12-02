from collections import ChainMap

from django.conf import settings as django_settings
from django.test.signals import setting_changed
from django.utils.module_loading import import_string
from rest_framework import serializers, viewsets


SETTINGS_NAME = 'DOCUMENTS_TOOLS'


def _reload_settings(*args, **kwargs):
    setting = kwargs['setting']
    if setting == SETTINGS_NAME:
        tools_settings.reload_user_settings()


def _get_user_settings():
    return getattr(django_settings, SETTINGS_NAME, {})


class ToolsSettings(ChainMap): # noqa: too-many-ancestors

    DEFAULT_VALUE = object()
    DEFAULT_SETTINGS = {
        'BASE_SERIALIZER': serializers.ModelSerializer,
        'BASE_VIEW_SET': viewsets.ModelViewSet,
        'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': False}

    def __init__(self):
        user_settings = _get_user_settings()
        super().__init__(user_settings, self.DEFAULT_SETTINGS.copy())

    def __getattr__(self, name):
        value = self.get(name, self.DEFAULT_VALUE)
        if value is self.DEFAULT_VALUE:
            raise AttributeError(
                f"Tools settings object has no attribute '{name}'")
        elif isinstance(value, str):
            value = import_string(value)
        return value

    def reload_user_settings(self):
        self.maps[0] = _get_user_settings()


tools_settings = ToolsSettings() # noqa: invalid-name
setting_changed.connect(_reload_settings)
