"""Test blood cell detector behavior without running an ONNX model."""

from unittest.mock import Mock

import numpy as np
import pytest
from pydantic import ValidationError

from mlops_workflows.components.cell_detector import (
    CellDetector,
    CellDetectorConfig,
)


@pytest.fixture
def detector(tmp_path, monkeypatch):
    """Create a detector with a simulated ONNX session."""
    model_path = tmp_path / "model.onnx"
    model_path.write_bytes(b"test model")

    session = Mock()
    session.get_inputs.return_value = [Mock(name="input")]
    session.get_inputs.return_value[0].name = "images"

    monkeypatch.setattr(
        "mlops_workflows.components.cell_detector.ort.InferenceSession",
        Mock(return_value=session),
    )

    config = CellDetectorConfig(model_path=str(model_path))
    return CellDetector(config)


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_config_rejects_invalid_confidence(confidence):
    with pytest.raises(ValidationError):
        CellDetectorConfig(
            model_path="model.onnx",
            confidence_threshold=confidence,
        )


def test_detector_rejects_missing_model(tmp_path):
    config = CellDetectorConfig(
        model_path=str(tmp_path / "missing.onnx"),
    )

    with pytest.raises(FileNotFoundError, match="Model file not found"):
        CellDetector(config)


def test_preprocess_returns_expected_shape_and_type(detector):
    image = np.zeros((480, 640, 3), dtype=np.uint8)

    batch, scale, padding_x, padding_y = detector._preprocess(image)

    assert batch.shape == (1, 3, 640, 640)
    assert batch.dtype == np.float32
    assert batch.flags.c_contiguous
    assert scale == 1.0
    assert padding_x == 0
    assert padding_y == 80


def test_preprocess_converts_bgr_to_normalized_rgb(detector):
    image = np.zeros((640, 640, 3), dtype=np.uint8)
    image[:, :] = [0, 0, 255]

    batch, _, _, _ = detector._preprocess(image)

    np.testing.assert_array_equal(
        batch[0, :, 320, 320],
        [1.0, 0.0, 0.0],
    )


def test_preprocess_adds_gray_padding(detector):
    image = np.zeros((480, 640, 3), dtype=np.uint8)

    batch, _, _, _ = detector._preprocess(image)

    np.testing.assert_allclose(
        batch[0, :, 0, 0],
        [114 / 255, 114 / 255, 114 / 255],
    )


def test_preprocess_resizes_preserving_proportions(detector):
    image = np.zeros((240, 320, 3), dtype=np.uint8)

    batch, scale, padding_x, padding_y = detector._preprocess(image)

    assert batch.shape == (1, 3, 640, 640)
    assert scale == 2.0
    assert padding_x == 0
    assert padding_y == 80


def test_preprocess_rejects_non_array_input(detector):
    with pytest.raises(TypeError, match="NumPy array"):
        detector._preprocess("not an image")


@pytest.mark.parametrize(
    "image",
    [
        np.zeros((0, 0, 3), dtype=np.uint8),
        np.zeros((10, 10), dtype=np.uint8),
        np.zeros((10, 10, 4), dtype=np.uint8),
        np.zeros((10, 10, 3), dtype=np.float32),
    ],
)
def test_preprocess_rejects_invalid_images(detector, image):
    with pytest.raises(ValueError, match="nonempty uint8 BGR image"):
        detector._preprocess(image)


def test_nms_removes_overlapping_box_with_lower_confidence(detector):
    boxes = np.array(
        [
            [10, 10, 110, 110],
            [15, 15, 115, 115],
            [200, 200, 250, 250],
        ],
        dtype=np.float32,
    )
    scores = np.array([0.95, 0.80, 0.90], dtype=np.float32)

    selected = detector._nms(boxes, scores)

    assert selected == [0, 2]


def test_nms_accepts_empty_predictions(detector):
    boxes = np.empty((0, 4), dtype=np.float32)
    scores = np.empty(0, dtype=np.float32)

    selected = detector._nms(boxes, scores)

    assert selected == []


def test_detect_returns_a_validated_detection(detector):
    image = np.zeros((640, 640, 3), dtype=np.uint8)

    # Center x, center y, width, height, RBC, WBC, Platelets.
    prediction = np.array(
        [100, 150, 40, 60, 0.90, 0.05, 0.05],
        dtype=np.float32,
    )
    detector.session.run.return_value = [prediction.reshape(1, 7, 1)]

    detections = detector.detect(image)

    assert len(detections) == 1
    assert detections[0].cls == "RBC"
    assert detections[0].conf == pytest.approx(0.90)
    assert detections[0].box == pytest.approx([80, 120, 120, 180])


def test_detect_discards_predictions_with_low_confidence(detector):
    image = np.zeros((640, 640, 3), dtype=np.uint8)
    prediction = np.array(
        [100, 150, 40, 60, 0.10, 0.20, 0.15],
        dtype=np.float32,
    )
    detector.session.run.return_value = [prediction.reshape(1, 7, 1)]

    detections = detector.detect(image)

    assert detections == []


def test_detect_restores_original_image_coordinates(detector):
    image = np.zeros((240, 320, 3), dtype=np.uint8)

    # The image is enlarged by 2 and receives 80 pixels of top padding.
    prediction = np.array(
        [200, 280, 80, 120, 0.05, 0.90, 0.05],
        dtype=np.float32,
    )
    detector.session.run.return_value = [prediction.reshape(1, 7, 1)]

    detections = detector.detect(image)

    assert len(detections) == 1
    assert detections[0].cls == "WBC"
    assert detections[0].box == pytest.approx([80, 70, 120, 130])


def test_detect_clips_boxes_to_image_boundaries(detector):
    image = np.zeros((640, 640, 3), dtype=np.uint8)
    prediction = np.array(
        [320, 320, 800, 800, 0.05, 0.05, 0.90],
        dtype=np.float32,
    )
    detector.session.run.return_value = [prediction.reshape(1, 7, 1)]

    detections = detector.detect(image)

    assert len(detections) == 1
    assert detections[0].cls == "Platelets"
    assert detections[0].box == pytest.approx([0, 0, 640, 640])


def test_detect_discards_boxes_outside_the_image(detector):
    image = np.zeros((640, 640, 3), dtype=np.uint8)
    prediction = np.array(
        [-100, -100, 20, 20, 0.90, 0.05, 0.05],
        dtype=np.float32,
    )
    detector.session.run.return_value = [prediction.reshape(1, 7, 1)]

    detections = detector.detect(image)

    assert detections == []
