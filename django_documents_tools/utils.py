import os
from collections import Counter

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.deconstruct import deconstructible

from django_documents_tools.exceptions import (
    BusinessEntityCreationIsNotAllowedError)
from django_documents_tools.manager import setattrs
from django_documents_tools.settings import tools_settings


def get_change_attachment_file_path(instance, file_name):
    app_label = instance._meta.app_label  # noqa: protected-access
    model_name = instance._meta.model_name  # noqa: protected-access
    return os.path.join(app_label, model_name, file_name)


def check_subclass(base, original):
    if not issubclass(base, original):
        raise Exception(
            f'{base.__name__} must be subclass of {original.__name__}')


def validate_change_attrs(model, change, attrs):
    documented_model_field = model._documented_model_field  # noqa: protected-access
    documented_model = model._meta.get_field(  # noqa: protected-access
        documented_model_field).remote_field.model

    if change and getattr(change, documented_model_field):
        documented_instance = getattr(change, documented_model_field)
        kwargs = change.get_changes()
        document_fields = attrs.get('document_fields')
        if change.snapshot and document_fields:
            changes = {}
            for field_name in document_fields:
                if field_name in attrs.keys():
                    changes[field_name] = attrs[field_name]
            kwargs = {**change.snapshot.state, **changes}

        setattrs(documented_instance, **kwargs)
        documented_instance.full_clean()
        documented_instance.refresh_from_db()
    else:
        change = model(**attrs)
        documented_instance = getattr(change, documented_model_field)
        kwargs = change.get_changes()
        if documented_instance:
            setattrs(documented_instance, **kwargs)
            documented_instance.full_clean()
            documented_instance.refresh_from_db()
        elif tools_settings.CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED:
            new_documented = documented_model(**kwargs)
            new_documented.full_clean()


@deconstructible
class LimitedChoicesValidator:

    def __init__(self, allowed_fields):
        self.allowed_fields = allowed_fields

    def __call__(self, value):
        for field in value:
            if field not in self.allowed_fields:
                raise ValidationError(f'Unknown field `{field}`.')

        for field, count in Counter(value).most_common():
            if count > 1:
                raise ValidationError(f'Found duplicate field `{field}`.')

        return True


def apply_change_receiver(sender, **kwargs):
    change = kwargs['instance']

    if not change.document_is_draft:
        new_documented = getattr(change, change._documented_model_field)  # noqa: pylint==protected-access
        creation = tools_settings.CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED
        if new_documented is None and creation:
            new_documented = change.apply_new()
            setattr(change, change._documented_model_field, new_documented)  # noqa: pylint==protected-access
            change.save(update_fields=[change._documented_model_field])  # noqa: pylint==protected-access

        elif new_documented is None and not creation:
            raise BusinessEntityCreationIsNotAllowedError()

        applicable_date = timezone.now().date()
        new_documented.changes.apply_to_object(date=applicable_date)
        new_documented.save(apply_documents=False)
        change.refresh_from_db()
