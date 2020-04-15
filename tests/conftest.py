import pytest

import django
from django.conf import settings


def pytest_configure(config):
    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.contrib.gis.db.backends.postgis',
                'NAME': 'repo',
                'USER': 'postgres',
                'HOST': '127.0.0.1',
                'PORT': '5432'
            }
        },
        SITE_ID=1,
        SECRET_KEY='not very secret in tests',
        USE_I18N=True,
        USE_L10N=True,
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
                'OPTIONS': {
                    "debug": True,  # We want template errors to raise
                }
            },
        ],
        MIDDLEWARE=(
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ),
        INSTALLED_APPS=(
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',

            'django_documents_tools',
            'tests'
        ),
        PASSWORD_HASHERS=(
            'django.contrib.auth.hashers.MD5PasswordHasher',
        )
    )
    django.setup()


@pytest.fixture
def book_change_model():
    from tests.models import Book

    return Book.changes.model


@pytest.fixture
def book_snapshot_model(book_change_model):
    return book_change_model._meta.get_field('snapshot').related_model  # noqa: protected-access


@pytest.fixture
def book_change_attachment_model(book_change_model):
    return book_change_model._meta.get_field('attachments').related_model  # noqa: protected-access
