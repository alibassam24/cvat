# SPDX-License-Identifier: MIT

from functools import partial

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from cvat.apps.engine.models import Task

from .live_updates import publish_task_changed


@receiver(post_save, sender=Task, dispatch_uid="test.label_counts.task_saved")
def on_task_saved(sender, instance: Task, created: bool, **kwargs):
    # Every annotation write ends with task.touch(), which is a Task save.
    # Publish after commit so a client that re-reads the counts sees the new rows.
    # robust: if Redis is down the save has already succeeded and must not fail because
    # of a live update; the error is logged and clients still get the next change.
    if not created:
        transaction.on_commit(partial(publish_task_changed, instance.id), robust=True)
