# SPDX-License-Identifier: MIT

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from django.db.models import Count

from cvat.apps.engine.models import JobType, LabeledImage, LabeledShape, LabeledTrack, Task

# Breakdown keys besides the shape types (rectangle, polygon, mask, ...)
TRACK = "track"
TAG = "tag"


@dataclass(frozen=True)
class LabelCount:
    id: int
    name: str
    color: str
    count: int
    by_type: dict[str, int] = field(default_factory=dict)


def count_annotations_by_label(task: Task) -> list[LabelCount]:
    """
    Number of annotations per top-level label in the task, most frequent first,
    each with a breakdown by shape type (tracks and tags are their own types).

    One annotation is one shape, one track (however many frames it spans) or one tag.
    Only regular annotation jobs are counted: ground truth and consensus replica jobs
    hold copies of the same objects and would inflate the numbers. Skeleton elements
    are stored as child rows of their skeleton, so only parents are counted.
    Labels without annotations are included with a zero count.
    """
    in_task = {"job__segment__task_id": task.id, "job__type": JobType.ANNOTATION}
    by_label: defaultdict[int, Counter] = defaultdict(Counter)

    shapes = (
        LabeledShape.objects.filter(**in_task, parent__isnull=True)
        .values("label_id", "type")
        .annotate(n=Count("id"))
    )
    for row in shapes:
        by_label[row["label_id"]][row["type"]] += row["n"]

    for model, kind in ((LabeledTrack, TRACK), (LabeledImage, TAG)):
        rows = model.objects.filter(**in_task).values("label_id").annotate(n=Count("id"))
        if model is LabeledTrack:
            rows = rows.filter(parent__isnull=True)
        for row in rows:
            by_label[row["label_id"]][kind] += row["n"]

    labels = task.get_labels().values("id", "name", "color")
    return sorted(
        (
            LabelCount(
                **label,
                count=by_label[label["id"]].total(),
                by_type=dict(by_label[label["id"]]),
            )
            for label in labels
        ),
        key=lambda item: (-item.count, item.name),
    )
