# SPDX-License-Identifier: MIT

from django.contrib.auth.models import Group
from rest_framework import status

from cvat.apps.engine.models import (
    Job,
    JobType,
    Label,
    LabeledImage,
    LabeledShape,
    LabeledTrack,
    Segment,
    ShapeType,
    Task,
)
from cvat.apps.engine.tests.utils import ApiTestBase, ForceLogin
from cvat.apps.iam.models import User


def add_job(task: Task, job_type: JobType = JobType.ANNOTATION) -> Job:
    segment = Segment.objects.create(task=task, start_frame=0, stop_frame=9)
    return Job.objects.create(segment=segment, type=job_type)


def add_shape(job: Job, label: Label, **kwargs) -> LabeledShape:
    return LabeledShape.objects.create(
        job=job, label=label, frame=0, type=ShapeType.RECTANGLE, points=[0, 0, 1, 1], **kwargs
    )


class TaskLabelCountsTestCase(ApiTestBase):
    @classmethod
    def setUpTestData(cls):
        user_group, _ = Group.objects.get_or_create(name="user")
        cls.owner = User.objects.create_user(username="owner", password="owner")
        cls.outsider = User.objects.create_user(username="outsider", password="outsider")
        for user in (cls.owner, cls.outsider):
            user.groups.add(user_group)

        cls.task = Task.objects.create(name="counts", owner=cls.owner)
        cls.car = Label.objects.create(task=cls.task, name="car", color="#ff0000")
        cls.person = Label.objects.create(task=cls.task, name="person", color="#00ff00")
        cls.unused = Label.objects.create(task=cls.task, name="unused", color="#0000ff")
        cls.job = add_job(cls.task)

    def _get_counts(self, user, task_id=None):
        with ForceLogin(user, self.client):
            return self.client.get(f"/api/test/tasks/{task_id or self.task.id}/label-counts")

    def _counts_by_name(self, response):
        return {label["name"]: label["count"] for label in response.json()["labels"]}

    def test_counts_shapes_per_label_and_keeps_empty_labels(self):
        for _ in range(3):
            add_shape(self.job, self.car)
        add_shape(self.job, self.person)

        response = self._get_counts(self.owner)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.json()["total"], 4)
        self.assertEqual(
            [(label["name"], label["count"]) for label in response.json()["labels"]],
            [("car", 3), ("person", 1), ("unused", 0)],
        )

    def test_counts_a_track_and_a_tag_once_each(self):
        LabeledTrack.objects.create(job=self.job, label=self.car, frame=0)
        LabeledImage.objects.create(job=self.job, label=self.person, frame=0)

        counts = self._counts_by_name(self._get_counts(self.owner))

        self.assertEqual(counts["car"], 1)
        self.assertEqual(counts["person"], 1)

    def test_ignores_ground_truth_jobs(self):
        add_shape(self.job, self.car)
        add_shape(add_job(self.task, JobType.GROUND_TRUTH), self.car)

        counts = self._counts_by_name(self._get_counts(self.owner))

        self.assertEqual(counts["car"], 1)

    def test_counts_a_skeleton_once_not_per_point(self):
        skeleton = Label.objects.create(task=self.task, name="body", type="skeleton")
        point = Label.objects.create(task=self.task, name="head", type="points", parent=skeleton)
        parent = add_shape(self.job, skeleton)
        add_shape(self.job, point, parent=parent)
        add_shape(self.job, point, parent=parent)

        counts = self._counts_by_name(self._get_counts(self.owner))

        self.assertEqual(counts["body"], 1)
        self.assertNotIn("head", counts)

    def test_refuses_anonymous_request(self):
        response = self.client.get(f"/api/test/tasks/{self.task.id}/label-counts")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refuses_user_without_access_to_task(self):
        response = self._get_counts(self.outsider)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_task_is_not_found(self):
        response = self._get_counts(self.owner, task_id=self.task.id + 1000)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
