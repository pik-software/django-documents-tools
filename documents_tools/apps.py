from django.apps import AppConfig as BaseAppConfig
from django.utils.translation import ugettext_lazy as _


class AppConfig(BaseAppConfig):
    name = 'documents-tools'
    verbose_name = _('documents-tools')

    def ready(self):
        from .import signals
        assert signals  # noqa unused import
