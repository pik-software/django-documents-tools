from datetime import datetime, timedelta
from typing import Iterable

from celery import app, Task

from django_documents_tools.models import BaseDocumented


class StartTimeTask(Task):  # noqa: abstract-method
    def apply_async(self, args=None, kwargs=None, *_args, **_kwargs):  # noqa: pylint=arguments-differ
        kwargs = {'start_time': datetime.now().isoformat(), **(kwargs or {})}
        return super().apply_async(args, kwargs, *_args, **_kwargs)


@app.shared_task(base=StartTimeTask)
def apply_postponed_documents(
        models: Iterable[BaseDocumented], start_time: str):
    today = datetime.fromisoformat(start_time).date()
    start_today = datetime.combine(today, datetime.min.time())
    end_today = start_today + timedelta(days=1)
    for model in models:
        documents_qs = model.changes.filter(
            document_date__range=[start_today, end_today])
        for document in documents_qs:
            if document.building.changes.apply_to_object():
                document.building.save()
