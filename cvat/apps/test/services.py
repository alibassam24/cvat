# SPDX-License-Identifier: MIT

from collections import Counter
from dataclasses import dataclass

from django.db.models import Count

from cvat.apps.engine.models import JobType, LabeledImage, LabeledShape, LabeledTrack, Task


@dataclass(frozen=True)
class LabelCount:
    id: int
    name: str
    color: str
    count: int


def count_annotations_by_label(task: Task) -> list[LabelCount]:
    """
    Number of annotations per top-level label in the task, most frequent first.

    One annotation is one shape, one track (however many frames it spans) or one tag.
    Only regular annotation jobs are counted: ground truth and consensus replica jobs
    hold copies of the same objects and would inflate the numbers. Skeleton elements
    are stored as child rows of their skeleton, so only parents are counted.
    Labels without annotations are included with a zero count.
    """
    counts = Counter()
    for model in (LabeledShape, LabeledTrack, LabeledImage):
        rows = (
            model.objects.filter(job__segment__task_id=task.id, job__type=JobType.ANNOTATION)
            .values("label_id")
            .annotate(n=Count("id"))
        )
        if model is not LabeledImage:
            rows = rows.filter(parent__isnull=True)

        for row in rows:
            counts[row["label_id"]] += row["n"]

    labels = task.get_labels().values("id", "name", "color")
    return sorted(
        (LabelCount(**label, count=counts[label["id"]]) for label in labels),
        key=lambda item: (-item.count, item.name),
    )
