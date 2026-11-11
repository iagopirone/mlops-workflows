"""Integrate object detection with the artifact workflow."""

import numpy as np

from mlops_workflows.artifacts.detection.detection_content import (
    DetectionContent,
)
from mlops_workflows.artifacts.detection.detection_reference import (
    DetectionReference,
)
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.components.interface import Component
from mlops_workflows.components.object_detection.object_detector import ObjectDetector


class ObjectDetectionComponent(Component):
    """Execute object detection using image artifacts."""

    def __init__(
        self,
        detector: ObjectDetector,
        output_reference: DetectionReference,
    ):
        self.detector = detector
        self.output_reference = output_reference

    def prepare(
        self,
        input_artifacts: list[ArtifactReference],
    ) -> np.ndarray:
        """Load an image from its artifact reference."""
        if len(input_artifacts) != 1 or not isinstance(
            input_artifacts[0], ImageReference
        ):
            raise ValueError("Expected exactly one ImageReference.")

        content = input_artifacts[0].materialize()

        return content.data

    def execute(
        self,
        prepared_data: object,
    ) -> list[ArtifactReference]:
        """Detect objects and save the results as an artifact."""
        if not isinstance(prepared_data, np.ndarray):
            raise TypeError("Expected a NumPy image array.")

        detections = self.detector.detect(prepared_data)

        content = DetectionContent(data=detections)
        content.dematerialize(self.output_reference)

        return [self.output_reference]
