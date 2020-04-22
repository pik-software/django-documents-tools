import os


def get_change_attachment_file_path(instance, file_name):
    app_label = instance._meta.app_label  # noqa: protected-access
    model_name = instance._meta.model_name  # noqa: protected-access
    return os.path.join(app_label, model_name, file_name)


def check_subclass(base, original):
    if not issubclass(base, original):
        raise Exception(
            f'{base.__name__} must be subclass of {original.__name__}')