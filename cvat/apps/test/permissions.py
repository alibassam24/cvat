# SPDX-License-Identifier: MIT

from cvat.apps.engine.models import Task
from cvat.apps.engine.permissions import TaskPermission


class LabelCountsPermission:
    """
    Counts are part of the task, so there is no separate policy for them: anyone
    allowed to view the task can see its counts. Delegating to the existing task
    "view" rule keeps owners, assignees and organization roles working exactly as
    they do on the task page.
    """

    @classmethod
    def create(cls, request, view, obj: Task, iam_context):
        return [TaskPermission.create_scope_view(request, obj, iam_context)]
