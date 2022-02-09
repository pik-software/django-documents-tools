from datetime import datetime, timedelta
from typing import Iterable

from celery import app, Task
from django.apps import apps


class StartTimeTask(Task):  # noqa: abstract-method
    def apply_async(self, args=None, kwargs=None, *_args, **_kwargs):  # noqa: pylint=arguments-differ
        kwargs = {'start_time': datetime.now().isoformat(), **(kwargs or {})}
        return super().apply_async(args, kwargs, *_args, **_kwargs)


@app.shared_task(base=StartTimeTask)
def apply_postponed_documents(
        model_names: Iterable[str], start_time: str):
    today = datetime.fromisoformat(start_time).date()
    start_today = datetime.combine(today, datetime.min.time())
    end_today = start_today + timedelta(days=1)
    for model_str in model_names:
        app_label, model_name = model_str.split('.')
        model = apps.get_model(app_label=app_label, model_name=model_name)
        documents_qs = model.changes.filter(
            document_date__range=[start_today, end_today])
        for document in documents_qs:
            if document.building.changes.apply_to_object():
                document.building.save()
