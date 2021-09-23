import django

if django.VERSION < (3, 2, 0):
    default_app_config = 'django_documents_tools.apps.DjangoDocumentsToolsConfig'  # noqa: pylint=invalid-name
