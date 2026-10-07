# SPDX-License-Identifier: MIT

from rest_framework import routers

from .views import TaskLabelCountsViewSet

router = routers.SimpleRouter(trailing_slash=False)
router.register("test/tasks", TaskLabelCountsViewSet, basename="test-tasks")

urlpatterns = router.urls
