# SPDX-License-Identifier: MIT

from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from cvat.apps.engine.models import Task

from .permissions import LabelCountsPermission
from .serializers import TaskLabelCountsSerializer
from .services import count_annotations_by_label


@extend_schema(tags=["test"])
class TaskLabelCountsViewSet(viewsets.GenericViewSet):
    queryset = Task.objects.select_related("project", "organization")
    lookup_value_regex = r"\d+"
    iam_permission_class = LabelCountsPermission
    iam_supports_organization_params = False
    # Detail-only endpoint, the list filters CVAT adds by default don't apply.
    filter_backends = []

    @extend_schema(
        summary="Count annotations per label in a task",
        responses=TaskLabelCountsSerializer,
    )
    @action(detail=True, methods=["GET"], url_path="label-counts")
    def label_counts(self, request, pk):
        task = self.get_object()
        labels = count_annotations_by_label(task)
        serializer = TaskLabelCountsSerializer(
            {
                "task_id": task.id,
                "total": sum(label.count for label in labels),
                "labels": labels,
            }
        )
        return Response(serializer.data)
