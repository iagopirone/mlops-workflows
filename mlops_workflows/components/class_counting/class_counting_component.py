"""Count detections by class."""

from collections import Counter

from mlops_workflows.artifacts.class_count.class_count import ClassCount
from mlops_workflows.artifacts.class_count.class_count_content import (
    ClassCountContent,
)
from mlops_workflows.artifacts.class_count.class_count_reference import (
    ClassCountReference,
)
from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_content import DetectionContent
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.components.interface import Component


class ClassCountingComponent(Component):
    """Count the received detections grouped by their ``cls`` field.

    ``classes=None`` counts every class found, in order of first appearance.
    A list counts only those classes, in the configured order, listing absent
    ones with zero and recording the other detected classes as excluded; an
    empty list counts nothing. Detections are counted as received: no
    confidence filter and no change to class names.
    """

    def __init__(
        self,
        classes: list[str] | None,
        output_reference: ClassCountReference,
    ):
        if classes is not None:
            if not isinstance(classes, list) or not all(
                isinstance(name, str) for name in classes
            ):
                raise TypeError("Expected None or a list of class names.")
            if len(set(classes)) != len(classes):
                raise ValueError("The configured classes must be unique.")
            classes = list(classes)

        self.classes = classes
        self.output_reference = output_reference

    def prepare(
        self,
        input_artifacts: list[ArtifactReference],
    ) -> DetectionContent:
        """Load the detection artifact."""
        if len(input_artifacts) != 1 or not isinstance(
            input_artifacts[0], DetectionReference
        ):
            raise ValueError("Expected exactly one DetectionReference.")

        return input_artifacts[0].materialize()

    def execute(
        self,
        prepared_data: object,
    ) -> list[ArtifactReference]:
        """Count the detections and save the counts."""
        if not isinstance(prepared_data, DetectionContent):
            raise TypeError("Expected a DetectionContent.")

        class_count = self._count(prepared_data.data)

        ClassCountContent(data=class_count).dematerialize(self.output_reference)

        return [self.output_reference]

    def _count(self, detections: list[Detection]) -> ClassCount:
        """Build the counts for the configured domain."""
        detected = dict(Counter(detection.cls for detection in detections))

        if self.classes is None:
            counts = detected
            excluded = {}
        else:
            counts = {name: detected.get(name, 0) for name in self.classes}
            excluded = {
                name: count for name, count in detected.items() if name not in counts
            }

        return ClassCount(
            classes=None if self.classes is None else list(self.classes),
            counts=counts,
            total=sum(counts.values()),
            excluded=excluded,
            detection_count=len(detections),
        )
