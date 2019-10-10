from django.apps import AppConfig as BaseAppConfig
from django.utils.translation import ugettext_lazy as _


class AppConfig(BaseAppConfig):
    name = 'lib.documents'
    verbose_name = _('Documents')

    def ready(self):
        from .import signals
        assert signals  # noqa unused import
