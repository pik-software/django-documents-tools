from typing import List, Tuple, Union

from django.apps import apps
from django.db import migrations
from django.db.migrations.state import StateApps
from django.db.models.signals import post_migrate
from django.dispatch import receiver, Signal


def _rename_field(model, old_name, new_name):
    for change in model.objects.filter(
            document_fields__contains=[old_name]):
        change.document_fields = [
            new_name if field == old_name else field
            for field in change.document_fields]
        change.save(update_fields=['document_fields'])


def _remove_field(model, name):
    for change in model.objects.filter(document_fields__contains=[name]):
        change.document_fields = [
            field for field in change.document_fields if field != name]
        change.save(update_fields=['document_fields'])


def _process_operation(fake_apps, app, operation):
    is_rename = isinstance(operation, migrations.RenameField)
    is_remove = isinstance(operation, migrations.RemoveField)
    action = is_remove or is_rename
    if not action:
        return

    try:
        model = apps.get_model(app, operation.model_name)
    except LookupError:
        model = None
    model = getattr(getattr(model, 'changes', None), 'model', None)
    if not model:
        return
    model = fake_apps.get_model(app, model._meta.model_name)  # noqa: protected-access
    if not model:
        return

    if is_rename:
        _rename_field(model, operation.old_name, operation.new_name)
    if is_remove:
        _remove_field(model, operation.name)


@receiver(post_migrate)
def process_migrate(
        apps: Union[StateApps, Tuple]=(), # noqa: redefined-outer-name
        plan: Union[List[Tuple[migrations.Migration, bool]], Tuple] = (), **kwargs):
    for migration, is_reverse in plan:
        if is_reverse:
            continue
        for operation in migration.operations:
            _process_operation(apps, migration.app_label, operation)


change_applied = Signal(  # noqa: pylint=invalid-name
    providing_args=['documented_instance', 'change', 'updated_fields'])
