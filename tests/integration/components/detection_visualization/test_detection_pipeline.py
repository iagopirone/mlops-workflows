"""Integration test for the object detection pipeline."""

import numpy as np

from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.components.detection_visualization.detection_visualization_component import (
    DetectionVisualizationComponent,
)
from mlops_workflows.components.object_detection.object_detection_component import (
    ObjectDetectionComponent,
)
from mlops_workflows.components.object_detection.object_detector import ObjectDetector


class FakeDetector(ObjectDetector):
    """Return predefined detections without running a model."""

    def detect(self, image: np.ndarray) -> list[Detection]:
        return [
            Detection(
                cls="cat",
                conf=0.9,
                box=[10.0, 10.0, 40.0, 40.0],
            )
        ]


def test_detection_to_visualization_pipeline(tmp_path):
    """Pass detection artifacts between two components."""
    image_reference = ImageReference(
        name="original",
        location=str(tmp_path / "original.png"),
    )

    detection_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )

    annotated_reference = ImageReference(
        name="annotated",
        location=str(tmp_path / "annotated.png"),
    )

    image = np.zeros((64, 64, 3), dtype=np.uint8)
    ImageContent(data=image).dematerialize(image_reference)

    detection_component = ObjectDetectionComponent(
        detector=FakeDetector(),
        output_reference=detection_reference,
    )

    prepared_image = detection_component.prepare([image_reference])
    detection_outputs = detection_component.execute(prepared_image)

    visualization_component = DetectionVisualizationComponent(
        output_reference=annotated_reference,
    )

    prepared_data = visualization_component.prepare(
        [image_reference, detection_outputs[0]]
    )
    visualization_outputs = visualization_component.execute(prepared_data)

    annotated = annotated_reference.materialize().data
    original = image_reference.materialize().data

    assert detection_outputs == [detection_reference]
    assert visualization_outputs == [annotated_reference]
    assert len(detection_reference.materialize().data) == 1
    assert annotated[10, 10].tolist() == [0, 255, 0]
    assert np.array_equal(original, image)
