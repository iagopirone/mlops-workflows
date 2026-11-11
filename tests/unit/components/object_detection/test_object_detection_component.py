"""Test the object detection component."""

from types import SimpleNamespace

import numpy as np
import pytest

from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_reference import (
    DetectionReference,
)
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.components.object_detection.object_detection_component import (
    ObjectDetectionComponent,
)
from mlops_workflows.components.object_detection.object_detector import ObjectDetector


class FakeDetector(ObjectDetector):
    """Simulate object detection without loading a real model."""

    def __init__(self, detections: list[Detection]):
        self.detections = detections
        self.received_image = None

    def detect(self, image: np.ndarray) -> list[Detection]:
        """Return predefined detections."""
        self.received_image = image
        return self.detections


def test_prepare_loads_image_from_reference(tmp_path, monkeypatch):
    """Ensure prepare loads the image using its artifact reference."""
    image = np.zeros((100, 200, 3), dtype=np.uint8)

    reference = ImageReference(
        name="test_image",
        location=str(tmp_path / "image.jpg"),
    )

    monkeypatch.setattr(
        ImageReference,
        "materialize",
        lambda self: SimpleNamespace(data=image),
    )

    output_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )

    component = ObjectDetectionComponent(
        detector=FakeDetector([]),
        output_reference=output_reference,
    )

    prepared = component.prepare([reference])

    assert isinstance(prepared, np.ndarray)
    assert np.array_equal(prepared, image)


def test_execute_saves_detections_and_returns_reference(tmp_path):
    """Ensure execute saves detections and returns an artifact reference."""
    image = np.zeros((100, 200, 3), dtype=np.uint8)

    detections = [
        Detection(
            cls="person",
            conf=0.95,
            box=[10, 20, 100, 90],
        )
    ]

    detector = FakeDetector(detections)

    output_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )

    component = ObjectDetectionComponent(
        detector=detector,
        output_reference=output_reference,
    )

    result = component.execute(image)

    assert detector.received_image is image
    assert result == [output_reference]
    assert (tmp_path / "detections.json").is_file()

    restored = output_reference.materialize()

    assert restored.data == detections


def test_execute_handles_empty_detections(tmp_path):
    """Ensure an image without detections produces a valid artifact."""
    image = np.zeros((100, 200, 3), dtype=np.uint8)

    output_reference = DetectionReference(
        name="empty_detections",
        location=str(tmp_path / "empty.json"),
    )

    component = ObjectDetectionComponent(
        detector=FakeDetector([]),
        output_reference=output_reference,
    )

    result = component.execute(image)

    assert result == [output_reference]
    assert output_reference.materialize().data == []


def test_prepare_rejects_empty_artifact_list(tmp_path):
    """Ensure prepare requires exactly one input artifact."""
    output_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )

    component = ObjectDetectionComponent(
        detector=FakeDetector([]),
        output_reference=output_reference,
    )

    with pytest.raises(ValueError, match="exactly one ImageReference"):
        component.prepare([])


def test_prepare_rejects_wrong_artifact_type(tmp_path):
    """Ensure prepare rejects non-image artifacts."""
    reference = DetectionReference(
        name="other_detections",
        location=str(tmp_path / "other.json"),
    )

    output_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )

    component = ObjectDetectionComponent(
        detector=FakeDetector([]),
        output_reference=output_reference,
    )

    with pytest.raises(ValueError, match="exactly one ImageReference"):
        component.prepare([reference])


def test_execute_rejects_invalid_prepared_data(tmp_path):
    """Ensure execute rejects data that is not a NumPy array."""
    output_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )

    component = ObjectDetectionComponent(
        detector=FakeDetector([]),
        output_reference=output_reference,
    )

    with pytest.raises(TypeError, match="NumPy image array"):
        component.execute("invalid image")
