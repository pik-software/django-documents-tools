import os

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


def validate_change_attrs(model, attrs):
    documented_model_field = model._documented_model_field  # noqa: protected-access
    documented_model = model._meta.get_field(  # noqa: protected-access
        documented_model_field).remote_field.model
    change = model(**attrs)
    kwargs = change.get_changes()

    if documented_model_field in attrs:
        documented_instance = attrs[documented_model_field]
        snapshot = documented_instance.snapshots.filter(
            history_date__gte=attrs['document_date']).first()

        if snapshot:
            kwargs = {**snapshot.state, **kwargs}

        setattrs(documented_instance, **kwargs)
        documented_instance.full_clean()
    elif tools_settings.CREATE_BUSINESS_ENTITY_AFTER_CHANGE_CREATED:
        new_documented = documented_model(**kwargs)
        new_documented.full_clean()
