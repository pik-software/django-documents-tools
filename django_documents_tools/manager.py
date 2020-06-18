from __future__ import unicode_literals

import logging
from datetime import timedelta, datetime
from itertools import chain

from django.db import models
from django.db.models import Q
from django.utils import timezone

from .exceptions import (
    ObservableInstanceRequiredError,
    SnapshotDuplicateExistsError, ChangesAreNotCreatedYetError)
from .signals import change_applied

LOGGER = logging.getLogger(__name__)


def _get_min_date_border(border_1, border_2):
    if border_1 and border_2:
        return min(border_1, border_2)
    elif border_1:
        return border_1
    elif border_2:
        return border_2
    else:
        return None


def _get_max_date_border(border_1, border_2):
    if border_1 and border_2:
        return max(border_1, border_2)
    elif border_1:
        return border_1
    elif border_2:
        return border_2
    else:
        return None


def _get_first_and_last_date_borders(query_set, field_name):
    first_date = query_set.values(field_name).first()
    last_date = query_set.values(field_name).last()
    if first_date:
        first_date = first_date[field_name].date()
    if last_date:
        last_date = last_date[field_name].date()
    else:
        last_date = first_date
    return first_date, last_date


def _update_snapshot_via_previous(prev_snapshot, snapshot):
    d_fields = snapshot.document_fields_from_changes
    prev_d_fields = prev_snapshot.document_fields_from_changes
    prev_d_fields = prev_d_fields | set(prev_snapshot.document_fields)
    prev_d_fields -= d_fields
    state = snapshot.state
    prev_snap_st = prev_snapshot.state
    for d_field in prev_d_fields:
        state[d_field] = prev_snap_st.get(d_field)
    changed = setattrs(snapshot, **state)
    if changed:
        updated_fields = set(snapshot.document_fields) | set(changed)
        snapshot.document_fields = list(updated_fields)
        snapshot.save()


class ChangeDescriptor:
    def __init__(self, model):
        self.model = model

    def __get__(self, instance, owner):
        if instance is None:
            return ChangeManager(self.model)
        return ChangeManager(self.model, instance)


def setattrs(obj, **attrs):
    changed = {}
    for attr, new_value in attrs.items():
        old_value = getattr(obj, attr)
        if old_value != new_value:
            changed[attr] = old_value
            setattr(obj, attr, new_value)
    return changed


class SnapshotCalculator:

    def __init__(
            self, history_date, snapshots_qs,
            changes_qs, rel_to_documented_obj):
        self.history_date = history_date
        self._snapshots_qs = snapshots_qs
        self._changes_qs = changes_qs
        self._change_model = changes_qs.model
        self._rel_to_documented_obj = rel_to_documented_obj

    def _update_changes(self, snapshot, changes):
        for change in changes:
            change.snapshot = snapshot
            self._change_model.objects.filter(
                pk=change.pk).update(snapshot=snapshot)

    def _calculate_snapshot(self, changes, snapshot_state):
        snapshot_state = snapshot_state.copy()
        snapshot = self._snapshots_qs.first()
        if snapshot and not changes:
            snapshot.deleted = timezone.now()
            snapshot.save()
            return snapshot

        snapshot_state.update(self._rel_to_documented_obj)
        if snapshot:
            snapshot_state['deleted'] = None
            setattrs(snapshot, **snapshot_state)
        else:
            snapshot = self._snapshots_qs.model(
                history_date=self.history_date, **snapshot_state)
        return snapshot

    def _get_initial_snapshot_state(self):
        query_set = (self._snapshots_qs.model.objects.filter(
            history_date__lt=self.history_date,
            deleted__isnull=True,
            **self._rel_to_documented_obj)
            .order_by('history_date'))
        snapshot = query_set.last()
        if snapshot:
            return snapshot.state
        return {}

    def calculate_snapshot(self):
        changes = []
        snapshot_state = self._get_initial_snapshot_state()
        changes_qs = self._changes_qs.filter(deleted__isnull=True)
        for change in changes_qs:
            snapshot_state.update(change.get_snapshot_changes())
            changes.append(change)

        snapshot = self._calculate_snapshot(changes, snapshot_state)
        snapshot.document_fields = list(snapshot_state.keys())
        snapshot.save()
        self._update_changes(snapshot, changes)
        return snapshot


class SnapshotsSlicer:

    def __init__(
            self, rel_to_documented_obj, unit_size_in_days, changes_qs,
            snapshots_qs, allowed_latest_date=None,
            changes_order_field='document_date',
            snapshots_order_field='history_date'):
        self._rel_to_documented_obj = rel_to_documented_obj
        self._unit_size_in_days = unit_size_in_days
        self._initial_snapshots_qs = snapshots_qs
        self._initial_changes_qs = changes_qs
        self._allowed_latest_date = allowed_latest_date
        self._changes_order_field = changes_order_field
        self._snapshots_order_field = snapshots_order_field
        self._snapshots = []

    def _get_date_borders(self, first_doc_date, last_doc_date):
        begin_border = first_doc_date
        allowed_latest_date = self._allowed_latest_date or last_doc_date
        if first_doc_date != allowed_latest_date:
            end_border = begin_border + timedelta(days=self._unit_size_in_days)
        else:
            end_border = begin_border

        all_doc_dates = self._get_all_date_borders(
            begin_border, allowed_latest_date)
        while begin_border <= allowed_latest_date:
            for doc_date in all_doc_dates:
                if begin_border <= doc_date.date() <= end_border:
                    yield begin_border, end_border
                    break
            begin_border = end_border
            end_border = begin_border + timedelta(days=self._unit_size_in_days)

    def _get_all_date_borders(self, begin_border, end_border):
        changes_qs = self._initial_changes_qs.order_by(
            self._changes_order_field)
        changes_qs = changes_qs.filter(
            document_is_draft=False, document_date__date__gte=begin_border,
            document_date__date__lte=end_border)
        snapshots_qs = self._initial_snapshots_qs.order_by(
            self._snapshots_order_field)
        snapshots_qs = snapshots_qs.filter(
            history_date__date__gte=begin_border,
            history_date__date__lte=end_border)
        snap_dates = snapshots_qs.values_list('history_date', flat=True)
        changes_dates = changes_qs.values_list('document_date', flat=True)
        return set(chain(snap_dates, changes_dates))

    def _get_snapshots_qs(self, begin_border, end_border):
        if begin_border == end_border:
            return self._initial_snapshots_qs.filter(
                history_date__date=begin_border)
        else:
            return self._initial_snapshots_qs.filter(
                history_date__gte=begin_border, history_date__lt=end_border)

    def _get_changes_qs(self, begin_border, end_border):
        query_set = self._initial_changes_qs.filter(document_is_draft=False)
        if begin_border == end_border:
            query_set = query_set.filter(document_date__date=begin_border)
        else:
            query_set = query_set.filter(
                document_date__gte=begin_border, document_date__lt=end_border)
        return query_set.order_by(self._changes_order_field)

    def _is_calculation_required(self, begin_border, end_border):
        snapshots_qs = self._get_snapshots_qs(begin_border, end_border)
        if snapshots_qs.count() > 1:
            raise SnapshotDuplicateExistsError(
                'You have to delete all duplicates before continue')

        snapshot_updated = snapshots_qs.order_by(
            'updated').values('updated').last()
        changes_qs = self._get_changes_qs(begin_border, end_border)
        if snapshot_updated:
            snapshot_updated = snapshot_updated['updated']
            update_condition = (
                Q(updated__gt=snapshot_updated)
                | Q(deleted__gt=snapshot_updated))
            if changes_qs.filter(update_condition).exists():
                return True
            elif (changes_qs.count() == 0
                  and snapshots_qs.filter(deleted__isnull=True).exists()):
                return True
            else:
                return False
        elif changes_qs.exists():
            return True
        else:
            return False

    def _calculate_snapshots(self):
        changes_qs = self._initial_changes_qs.order_by(
            self._changes_order_field)
        snapshots_qs = self._initial_snapshots_qs.order_by(
            self._snapshots_order_field)
        changes_borders = _get_first_and_last_date_borders(
            changes_qs, field_name='document_date')
        snapshots_borders = _get_first_and_last_date_borders(
            snapshots_qs, field_name='history_date')
        first_date = _get_min_date_border(
            changes_borders[0], snapshots_borders[0])
        last_date = _get_max_date_border(
            changes_borders[1], snapshots_borders[1])

        if first_date is None and last_date is None:
            return

        date_borders = self._get_date_borders(first_date, last_date)
        for begin_border, end_border in date_borders:
            snapshots_qs = self._get_snapshots_qs(begin_border, end_border)
            if self._is_calculation_required(begin_border, end_border):
                changes_qs = self._get_changes_qs(begin_border, end_border)
                snapshot_calculator = SnapshotCalculator(
                    history_date=begin_border, snapshots_qs=snapshots_qs,
                    changes_qs=changes_qs,
                    rel_to_documented_obj=self._rel_to_documented_obj)
                snapshot = snapshot_calculator.calculate_snapshot()
                if snapshot and not snapshot.deleted:
                    self._snapshots.append(snapshot)
            else:
                snapshot = snapshots_qs.filter(deleted__isnull=True).first()
                if snapshot and self._snapshots:
                    prev_snap = self._snapshots[-1]
                    if prev_snap.updated > snapshot.updated:
                        _update_snapshot_via_previous(prev_snap, snapshot)
                if snapshot:
                    self._snapshots.append(snapshot)

    @property
    def latest_snapshot(self):
        self._calculate_snapshots()
        if self._snapshots:
            return self._snapshots[-1]
        return None


class ChangeManager(models.Manager):

    def __init__(self, model, instance=None):
        super().__init__()
        self.model = model
        self.instance = instance

    def _get_lookup(self):
        return {self.model._documented_model_field: self.instance.pk} # noqa protected-access

    def apply_to_object(self, date=None):
        if not self.instance:
            raise ObservableInstanceRequiredError()
        if isinstance(date, datetime):
            raise TypeError('You need to provide a date instance')

        snapshot_model = self.instance.snapshots.model
        unit_size_in_days = snapshot_model.unit_size_in_days
        changes_qs = self.get_queryset()
        if changes_qs.count() == 0:
            raise ChangesAreNotCreatedYetError(
                'There were not changes to calculate snapshots')

        snapshots_qs = snapshot_model.objects.filter(**self._get_lookup())
        rel_to_documented_obj = {
            f'{self.model._documented_model_field}_id': self.instance.pk} # noqa: protected-access
        snapshots_slicer = SnapshotsSlicer(
            rel_to_documented_obj=rel_to_documented_obj,
            unit_size_in_days=unit_size_in_days, changes_qs=changes_qs,
            snapshots_qs=snapshots_qs, allowed_latest_date=date)

        snapshot = snapshots_slicer.latest_snapshot

        if snapshot:
            changed = setattrs(self.instance, **snapshot.state)
            change = snapshot.changes.first()
            change_applied.send(
                sender=self.instance.changes.model,
                documented_instance=self.instance,
                change=change, updated_fields=changed)

        return self.instance

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.instance:
            return queryset.filter(**self._get_lookup())
        return queryset


class SnapshotDescriptor:
    def __init__(self, model):
        self.model = model

    def __get__(self, instance, owner):
        if instance is None:
            return SnapshotManager(self.model)
        return SnapshotManager(self.model, instance)


class SnapshotManager(models.Manager):
    def __init__(self, model, instance=None):
        super().__init__()
        self.model = model
        self.instance = instance

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.instance:
            lookup = {f'change__{self.model._documented_model_field}':  # noqa protected-access
                          self.instance.pk}
            return queryset.filter(**lookup)
        return queryset
