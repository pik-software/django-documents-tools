from django.apps import AppConfig


class DjangoDocumentsToolsConfig(AppConfig):
    name = 'django_documents_tools'

    def ready(self):
        from .import signals
        assert signals  # noqa unused import
