"""Test blood cell detection with a real image and ONNX model."""

import os
from pathlib import Path

import pytest

from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.components.cell_detector import (
    CellDetector,
    CellDetectorConfig,
)
from mlops_workflows.components.detection import Detection


@pytest.fixture
def detection_files():
    """Locate the model and blood cell image provided for integration."""
    model_path = os.environ.get("CELL_MODEL_PATH")
    image_path = os.environ.get("CELL_IMAGE_PATH")

    if not model_path or not image_path:
        pytest.skip("Set CELL_MODEL_PATH and CELL_IMAGE_PATH.")

    for file_path in (model_path, image_path):
        if not Path(file_path).is_file():
            raise FileNotFoundError(f"Integration file not found: {file_path}")

    return model_path, image_path


def test_detect_blood_cells_from_image_artifact(detection_files):
    model_path, image_path = detection_files

    reference = ImageReference(
        name="blood_image",
        location=image_path,
    )
    detector = CellDetector(CellDetectorConfig(model_path=model_path))

    content = reference.materialize()
    detections = detector.detect(content.data)

    height, width = content.data.shape[:2]

    assert detections, "Expected detections in the blood cell test image."

    for detection in detections:
        assert isinstance(detection, Detection)
        assert detection.cls in {"RBC", "WBC", "Platelets"}
        assert detector.config.confidence_threshold < detection.conf <= 1.0

        x_min, y_min, x_max, y_max = detection.box

        assert 0 <= x_min < x_max <= width
        assert 0 <= y_min < y_max <= height
