# SPDX-License-Identifier: MIT

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from django.core.cache import cache
from django.db.models import Count

from cvat.apps.engine.models import JobType, LabeledImage, LabeledShape, LabeledTrack, Task

# Breakdown keys besides the shape types (rectangle, polygon, mask, ...)
TRACK = "track"
TAG = "tag"

# Entries never go stale (see _cached_counts), the TTL only stops old ones piling up.
CACHE_TTL_SECONDS = 3600


@dataclass(frozen=True)
class LabelCount:
    id: int
    name: str
    color: str
    count: int
    by_type: dict[str, int] = field(default_factory=dict)


def _count_by_label(task: Task) -> dict[int, dict[str, int]]:
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

    return {label_id: dict(counts) for label_id, counts in by_label.items()}


def _cached_counts(task: Task) -> dict[int, dict[str, int]]:
    # Every annotation write ends with task.touch(), so updated_date changes whenever the
    # counts can. Putting it in the key means an entry can't be read after the data
    # changed, with no invalidation code and no matter which process did the write.
    key = f"test:label-counts:{task.id}:{task.updated_date.isoformat()}"
    return cache.get_or_set(key, lambda: _count_by_label(task), CACHE_TTL_SECONDS)


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
    by_label = _cached_counts(task)

    # Labels are read fresh rather than cached: renaming or recoloring a label doesn't
    # touch the task, and for project tasks the labels belong to the project.
    labels = task.get_labels().values("id", "name", "color")
    return sorted(
        (
            LabelCount(
                **label,
                count=sum(by_label.get(label["id"], {}).values()),
                by_type=by_label.get(label["id"], {}),
            )
            for label in labels
        ),
        key=lambda item: (-item.count, item.name),
    )
