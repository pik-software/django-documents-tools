import os


def get_change_attachment_path(instance, file_name):
    model_name = instance._meta.model_name  # noqa: protected-access
    return os.path.join(model_name, file_name)
