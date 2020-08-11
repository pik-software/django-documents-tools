## Django documents tools

#### Django documents tools is an BSD licensed library written in Python providing a toolset to work with documents snapshots and documented objects. This library has been tested with Python 3.7.x

### Quick start

1 Install the library

```bash
pip install django-documents-tools
```

2 Add `django_documents_tools` to your INSTALLED_APPS setting like this:

```python
INSTALLED_APPS = [
    ...,
    'django_documents_tools',
]
```

3 Configure the settings as you want

```python
DOCUMENTS_TOOLS = {
    'BASE_CHANGE_SERIALIZER': 'path_to_your_model_serializer',
    'BASE_CHANGE_VIEWSET': 'path_to_your_model_viewset',
    'BASE_SNAPSHOT_SERIALIZER': 'path_to_your_model_serializer',
    'BASE_SNAPSHOT_LINK_SERIALIZER': 'path_to_your_snapshot_link_serializer',
    'BASE_SNAPSHOT_VIEWSET': 'path_to_your_model_viewset',
    'BASE_DOCUMENTED_MODEL_LINK_SERIALIZER': 'path_to_your_model_serializer',
    'BASE_CHANGE_ATTACHMENT_SERIALIZER': 'path_to_your_model_serializer',
    'BASE_CHANGE_ATTACHMENT_VIEWSET': 'path_to_your_model_viewset',
    'BASE_CHANGE_LINK_SERIALIZER': 'path_to_your_model_serializer',
    'CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED': False
}
```

or just use the default values

4 The basic example how to define a documented object

```python
from django.db import models

from django_documents_tools.models import (
    BaseDocumented, Changes, BaseChange, BaseSnapshot)


class Documented(BaseDocumented):

    changes = Changes(
        inherit=True,
        excluded_fields=('deleted',),
        change_opts={
            'bases': (BaseChange,)},
        snapshot_opts={
            'bases': (BaseSnapshot,),
            'unit_size_in_days': 1})

    class Meta:
        abstract = True


class Author(models.Model):

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    date_of_death = models.DateField('Died', null=True, blank=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.last_name}, {self.first_name}'


class Book(Documented):

    title = models.CharField(max_length=200)
    author = models.ForeignKey('Author', on_delete=models.SET_NULL, null=True)
    summary = models.TextField(max_length=1000, blank=True)
    isbn = models.CharField('ISBN', max_length=13, blank=True)
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return self.title
```

## Using custom serializer classes in project

1. Define your custom serializer (must be subclass of corresponding base serializer).

```python

from rest_framework import serializers
from django_documents_tools.api.serializers import BaseChangeSerializer


class BaseCustomChangeSerializer(BaseChangeSerializer):

    my_custom_field = serializers.SerializerMethodField()

    def get_my_custom_field(self, change):
        return 'Extra data'

    class Meta(BaseChangeSerializer.Meta):
        fields = BaseChangeSerializer.Meta.fields + ('my_custom_field',)
```

2. Update documents tools settings.

```python

DOCUMENTS_SETTINGS = {
  'BASE_CHANGE_SERIALIZER': 'my_app.serializers.CustomChangeSerializerBase'}

```

3. Now you can easily add, remove and change fields in documented serializers.

## Using custom viewset classes in project

1. Define your custom viewset (must be subclass of corresponding base viewset).

```python

from django_documents_tools.api.viewsets import BaseChangeViewSet


class BaseCustomViewSet(BaseChangeViewSet):
    prefetch_related_fields = ('custom_fields',)
```

2. Update documents tools settings.

```python

DOCUMENTS_SETTINGS = {
  'BASE_CHANGE_VIEWSET': 'my_app.ser.CustomChangeViewSetBase'}

```

3. Now you can easily edit viewset attributes.

## Overriding project settings for specific model
You can use model specific viewset and serializer classes.
They also must be subclasses of corresponding base classes.

```python

from django_documents_tools.models import (
    BaseDocumented, Changes, BaseChange, BaseSnapshot, BaseChangeAttachment)


class Documented(BaseDocumented):

    changes = Changes(
        inherit=True,
        excluded_fields=('deleted',),
        change_opts={
            'bases': (BaseChange,),
            'base_serializer': 'path.to.change_serializer_class',
            'base_viewset': 'path.to.change_viewset_class',   
        },
        snapshot_opts={
            'bases': (BaseSnapshot,),
            'base_serializer': 'path.to.snapshot_serializer_class',
            'base_viewset': 'path.to.snapshot_viewset_class', 
            'unit_size_in_days': 1
        },
        change_attachment_opts={
            'bases': (BaseChangeAttachment,),
            'base_serializer': 'path.to.change_attachment_serializer_class',
            'base_viewset': 'path.to.change_attachment_viewset_class',
        },
    )

    class Meta:
        abstract = True

```

## Signals
This package provides several signals for use.

## `change_applied` - Send after successful change application.
Can be used for subscription for specific field updates.

Provided `kwargs`:

- `sender` - _Change_ model
- `documented_instance` - Documented model instance
- `change` - Change instance
- `updated_fields` - Dictionary field -> new value
