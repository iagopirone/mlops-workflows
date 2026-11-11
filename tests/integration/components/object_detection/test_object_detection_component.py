"""Test object detection integration with image artifacts."""

import os
from pathlib import Path

import pytest

from mlops_workflows.artifacts.detection.detection_reference import (
    DetectionReference,
)
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.components.object_detection.detectors.yolo_detector import (
    YoloDetector,
    YoloDetectorConfig,
)
from mlops_workflows.components.object_detection.object_detection_component import (
    ObjectDetectionComponent,
)


def test_object_detection_component_with_real_model(tmp_path):
    """Run object detection through the complete artifact workflow."""
    model_path = os.environ.get("DETECTION_MODEL_PATH")
    image_path = os.environ.get("DETECTION_IMAGE_PATH")

    if not model_path or not image_path:
        pytest.skip("Detection model and image paths are not configured.")

    assert Path(model_path).is_file()
    assert Path(image_path).is_file()

    image_reference = ImageReference(
        name="input_image",
        location=image_path,
    )

    output_reference = DetectionReference(
        name="output_detections",
        location=str(tmp_path / "detections.json"),
    )

    detector = YoloDetector(YoloDetectorConfig(model_path=model_path))

    component = ObjectDetectionComponent(
        detector=detector,
        output_reference=output_reference,
    )

    prepared_data = component.prepare([image_reference])
    output_artifacts = component.execute(prepared_data)

    assert output_artifacts == [output_reference]
    assert Path(output_reference.location).is_file()

    restored = output_reference.materialize()

    assert len(restored.data) > 0

    height, width = prepared_data.shape[:2]

    for detection in restored.data:
        assert detection.cls in detector.class_names
        assert 0.0 <= detection.conf <= 1.0

        x_min, y_min, x_max, y_max = detection.box

        assert 0 <= x_min < x_max <= width
        assert 0 <= y_min < y_max <= height
