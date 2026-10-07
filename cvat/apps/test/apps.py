# SPDX-License-Identifier: MIT

from django.apps import AppConfig


# Not named TestConfig on purpose: pytest would try to collect a class with that name.
class AnnotationAnalyticsConfig(AppConfig):
    name = "cvat.apps.test"
    verbose_name = "Annotation analytics"
