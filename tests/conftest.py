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
    return book_change_model.snapshot.field.related_model


@pytest.fixture
def book_change_attachment_model(book_change_model):
    return book_change_model.attachment.field.related_model


@pytest.fixture
def api_user():
    from django.contrib.auth import get_user_model
    user_model = get_user_model()
    user = user_model(username='test', email='test@test.ru', is_active=True)
    user.set_password('test_password')
    user.save()
    return user


@pytest.fixture
def api_client(api_user):
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_login(api_user)
    return client


def add_user_model_permissions(user, model, *actions):
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission

    ctype = ContentType.objects.get_for_model(model)
    user.user_permissions.add(*(
        Permission.objects.get(codename=f'{action}_{model._meta.model_name}',  # noqa: protected-access
                               content_type=ctype)
        for action in actions
    ))


def add_permissions_to_user(user, permission_codes):
    from django.contrib.auth.models import Permission

    for permission_code in permission_codes:
        permission = Permission.objects.get(codename=permission_code)
        user.user_permissions.add(permission)
