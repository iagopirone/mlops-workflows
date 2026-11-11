"""Test the generic YOLO detector."""

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from pydantic import ValidationError

from mlops_workflows.components.object_detection.detectors.yolo_detector import (
    YoloDetector,
    YoloDetectorConfig,
)


def test_nms_preserves_overlapping_boxes_of_different_classes():
    """Ensure NMS does not suppress detections from different classes."""
    detector = YoloDetector.__new__(YoloDetector)

    detector.config = YoloDetectorConfig(model_path="unused.onnx")
    detector.class_names = ("person", "bicycle")
    detector.input_height = 640
    detector.input_width = 640
    detector.input_name = "images"

    predictions = np.array(
        [
            [320, 320, 100, 100, 0.9, 0.1],
            [320, 320, 100, 100, 0.1, 0.8],
        ],
        dtype=np.float32,
    )

    output = predictions.T[np.newaxis, ...]

    detector.session = SimpleNamespace(
        run=lambda *_: [output],
    )

    image = np.zeros((640, 640, 3), dtype=np.uint8)

    detections = detector.detect(image)

    assert len(detections) == 2
    assert [d.cls for d in detections] == ["person", "bicycle"]


def test_detector_reads_class_names_from_metadata(tmp_path, monkeypatch):
    """Ensure class names are loaded from the model metadata."""
    model_path = tmp_path / "model.onnx"
    model_path.write_bytes(b"fake model")

    session = SimpleNamespace(
        get_inputs=lambda: [
            SimpleNamespace(
                name="images",
                shape=[1, 3, 640, 640],
            )
        ],
        get_modelmeta=lambda: SimpleNamespace(
            custom_metadata_map={
                "names": "{0: 'cat', 1: 'dog'}",
            },
        ),
    )

    monkeypatch.setattr(
        "mlops_workflows.components.object_detection.detectors.yolo_detector.ort.InferenceSession",
        lambda *args, **kwargs: session,
    )

    detector = YoloDetector(YoloDetectorConfig(model_path=str(model_path)))

    assert detector.class_names == ("cat", "dog")


def test_detector_accepts_custom_class_names(tmp_path, monkeypatch):
    """Ensure manually configured class names are accepted."""
    model_path = tmp_path / "model.onnx"
    model_path.write_bytes(b"fake model")

    session = SimpleNamespace(
        get_inputs=lambda: [
            SimpleNamespace(
                name="images",
                shape=[1, 3, 640, 640],
            )
        ],
    )

    monkeypatch.setattr(
        "mlops_workflows.components.object_detection.detectors.yolo_detector.ort.InferenceSession",
        lambda *args, **kwargs: session,
    )

    detector = YoloDetector(
        YoloDetectorConfig(
            model_path=str(model_path),
            class_names=["car", "bus", "truck"],
        )
    )

    assert detector.class_names == ("car", "bus", "truck")


def test_preprocess_uses_model_input_dimensions(tmp_path, monkeypatch):
    """Ensure preprocessing uses the dimensions required by the model."""
    model_path = tmp_path / "model.onnx"
    model_path.write_bytes(b"fake model")

    session = SimpleNamespace(
        get_inputs=lambda: [
            SimpleNamespace(
                name="images",
                shape=[1, 3, 320, 512],
            )
        ],
    )

    monkeypatch.setattr(
        "mlops_workflows.components.object_detection.detectors.yolo_detector.ort.InferenceSession",
        lambda *args, **kwargs: session,
    )

    detector = YoloDetector(
        YoloDetectorConfig(
            model_path=str(model_path),
            class_names=["person"],
        )
    )

    image = np.zeros((480, 640, 3), dtype=np.uint8)

    batch, scale, padding_x, padding_y = detector._preprocess(image)

    assert detector.input_height == 320
    assert detector.input_width == 512
    assert batch.shape == (1, 3, 320, 512)
    assert batch.dtype == np.float32
    assert batch.flags["C_CONTIGUOUS"]
    assert scale > 0
    assert padding_x >= 0
    assert padding_y >= 0


@pytest.mark.parametrize(
    "output_shape",
    [
        (1, 7, 2),  # Wrong number of class scores
        (1, 2, 6),  # Wrong output layout
        (2, 6, 2),  # Unsupported batch size
        (1, 6),  # Missing dimension
    ],
)
def test_detector_rejects_unsupported_output_shapes(output_shape):
    """Ensure unsupported YOLO output shapes are rejected."""
    detector = YoloDetector.__new__(YoloDetector)

    detector.config = YoloDetectorConfig(model_path="unused.onnx")
    detector.class_names = ("cat", "dog")
    detector.input_height = 640
    detector.input_width = 640
    detector.input_name = "images"

    output = np.zeros(output_shape, dtype=np.float32)

    detector.session = SimpleNamespace(
        run=lambda *_: [output],
    )

    image = np.zeros((640, 640, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="Unsupported YOLO output shape"):
        detector.detect(image)


def test_detector_handles_empty_predictions(monkeypatch):
    """Ensure an empty prediction tensor returns no detections."""
    detector = YoloDetector.__new__(YoloDetector)

    detector.class_names = ("person",)
    detector.input_name = "images"

    class FakeSession:
        """Simulate an ONNX session with no predictions."""

        def run(self, *_args, **_kwargs):
            return [np.empty((1, 5, 0), dtype=np.float32)]

    detector.session = FakeSession()

    monkeypatch.setattr(
        detector,
        "_preprocess",
        lambda image: (
            np.zeros((1, 3, 640, 640), dtype=np.float32),
            1.0,
            0,
            0,
        ),
    )

    image = np.zeros((640, 640, 3), dtype=np.uint8)

    assert detector.detect(image) == []


@pytest.fixture
def yolo_with_mock_session(tmp_path, monkeypatch):
    """Create a YOLO detector with a simulated ONNX session."""
    model_path = tmp_path / "model.onnx"
    model_path.write_bytes(b"fake model")

    session = Mock()
    session.get_inputs.return_value = [
        SimpleNamespace(name="images", shape=[1, 3, 640, 640])
    ]

    monkeypatch.setattr(
        "mlops_workflows.components.object_detection.detectors.yolo_detector.ort.InferenceSession",
        Mock(return_value=session),
    )

    return YoloDetector(
        YoloDetectorConfig(
            model_path=str(model_path),
            class_names=["person", "dog", "car"],
        )
    )


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_config_rejects_invalid_confidence(confidence):
    """Reject confidence thresholds outside the valid range."""
    with pytest.raises(ValidationError):
        YoloDetectorConfig(
            model_path="model.onnx",
            confidence_threshold=confidence,
        )


def test_detector_rejects_missing_model(tmp_path):
    """Reject a model path that does not exist."""
    config = YoloDetectorConfig(model_path=str(tmp_path / "missing.onnx"))

    with pytest.raises(FileNotFoundError, match="Model file not found"):
        YoloDetector(config)


def test_preprocess_returns_expected_shape_and_type(yolo_with_mock_session):
    """Return a contiguous, normalized tensor and resize metadata."""
    image = np.zeros((480, 640, 3), dtype=np.uint8)

    batch, scale, padding_x, padding_y = yolo_with_mock_session._preprocess(image)

    assert batch.shape == (1, 3, 640, 640)
    assert batch.dtype == np.float32
    assert batch.flags.c_contiguous
    assert scale == 1.0
    assert padding_x == 0
    assert padding_y == 80


def test_preprocess_converts_bgr_to_normalized_rgb(yolo_with_mock_session):
    """Convert BGR pixels into normalized RGB channels."""
    image = np.zeros((640, 640, 3), dtype=np.uint8)
    image[:, :] = [0, 0, 255]

    batch, _, _, _ = yolo_with_mock_session._preprocess(image)

    np.testing.assert_array_equal(
        batch[0, :, 320, 320],
        [1.0, 0.0, 0.0],
    )


def test_preprocess_adds_gray_padding(yolo_with_mock_session):
    """Use the expected gray value for letterbox padding."""
    image = np.zeros((480, 640, 3), dtype=np.uint8)

    batch, _, _, _ = yolo_with_mock_session._preprocess(image)

    np.testing.assert_allclose(
        batch[0, :, 0, 0],
        [114 / 255, 114 / 255, 114 / 255],
    )


def test_preprocess_resizes_preserving_proportions(yolo_with_mock_session):
    """Preserve image proportions during resizing."""
    image = np.zeros((240, 320, 3), dtype=np.uint8)

    batch, scale, padding_x, padding_y = yolo_with_mock_session._preprocess(image)

    assert batch.shape == (1, 3, 640, 640)
    assert scale == 2.0
    assert padding_x == 0
    assert padding_y == 80


def test_preprocess_rejects_non_array_input(yolo_with_mock_session):
    """Reject input that is not a NumPy array."""
    with pytest.raises(TypeError, match="NumPy array"):
        yolo_with_mock_session._preprocess("not an image")


@pytest.mark.parametrize(
    "image",
    [
        np.zeros((0, 0, 3), dtype=np.uint8),
        np.zeros((10, 10), dtype=np.uint8),
        np.zeros((10, 10, 4), dtype=np.uint8),
        np.zeros((10, 10, 3), dtype=np.float32),
    ],
)
def test_preprocess_rejects_invalid_images(yolo_with_mock_session, image):
    """Reject empty images, invalid channels, and invalid dtypes."""
    with pytest.raises(ValueError, match="nonempty uint8 BGR image"):
        yolo_with_mock_session._preprocess(image)


def test_nms_removes_overlapping_box_with_lower_confidence(
    yolo_with_mock_session,
):
    """Suppress overlapping boxes with lower confidence."""
    boxes = np.array(
        [
            [10, 10, 110, 110],
            [15, 15, 115, 115],
            [200, 200, 250, 250],
        ],
        dtype=np.float32,
    )
    scores = np.array([0.95, 0.80, 0.90], dtype=np.float32)

    selected = yolo_with_mock_session._nms(boxes, scores)

    assert selected == [0, 2]


def test_nms_accepts_empty_predictions(yolo_with_mock_session):
    """Handle NMS without candidate boxes."""
    boxes = np.empty((0, 4), dtype=np.float32)
    scores = np.empty(0, dtype=np.float32)

    assert yolo_with_mock_session._nms(boxes, scores) == []


def test_detect_returns_a_validated_detection(yolo_with_mock_session):
    """Convert model predictions into validated detections."""
    image = np.zeros((640, 640, 3), dtype=np.uint8)

    prediction = np.array(
        [100, 150, 40, 60, 0.90, 0.05, 0.05],
        dtype=np.float32,
    )
    yolo_with_mock_session.session.run.return_value = [prediction.reshape(1, 7, 1)]

    detections = yolo_with_mock_session.detect(image)

    assert len(detections) == 1
    assert detections[0].cls == "person"
    assert detections[0].conf == pytest.approx(0.90)
    assert detections[0].box == pytest.approx([80, 120, 120, 180])


def test_detect_discards_predictions_with_low_confidence(
    yolo_with_mock_session,
):
    """Discard detections below the configured threshold."""
    image = np.zeros((640, 640, 3), dtype=np.uint8)

    prediction = np.array(
        [100, 150, 40, 60, 0.10, 0.20, 0.15],
        dtype=np.float32,
    )
    yolo_with_mock_session.session.run.return_value = [prediction.reshape(1, 7, 1)]

    assert yolo_with_mock_session.detect(image) == []


def test_detect_restores_original_image_coordinates(yolo_with_mock_session):
    """Undo resizing and letterbox padding in detection coordinates."""
    image = np.zeros((240, 320, 3), dtype=np.uint8)

    prediction = np.array(
        [200, 280, 80, 120, 0.05, 0.90, 0.05],
        dtype=np.float32,
    )
    yolo_with_mock_session.session.run.return_value = [prediction.reshape(1, 7, 1)]

    detections = yolo_with_mock_session.detect(image)

    assert len(detections) == 1
    assert detections[0].cls == "dog"
    assert detections[0].box == pytest.approx([80, 70, 120, 130])


def test_detect_clips_boxes_to_image_boundaries(yolo_with_mock_session):
    """Clip bounding boxes to the original image dimensions."""
    image = np.zeros((640, 640, 3), dtype=np.uint8)

    prediction = np.array(
        [320, 320, 800, 800, 0.05, 0.05, 0.90],
        dtype=np.float32,
    )
    yolo_with_mock_session.session.run.return_value = [prediction.reshape(1, 7, 1)]

    detections = yolo_with_mock_session.detect(image)

    assert len(detections) == 1
    assert detections[0].cls == "car"
    assert detections[0].box == pytest.approx([0, 0, 640, 640])


def test_detect_discards_boxes_outside_the_image(yolo_with_mock_session):
    """Discard boxes that do not intersect the image."""
    image = np.zeros((640, 640, 3), dtype=np.uint8)

    prediction = np.array(
        [-100, -100, 20, 20, 0.90, 0.05, 0.05],
        dtype=np.float32,
    )
    yolo_with_mock_session.session.run.return_value = [prediction.reshape(1, 7, 1)]

    assert yolo_with_mock_session.detect(image) == []


@pytest.mark.parametrize(
    ("column", "value"),
    [
        (0, float("nan")),
        (2, float("inf")),
        (4, float("-inf")),
        (5, float("nan")),
    ],
)
def test_detect_discards_nonfinite_predictions(
    yolo_with_mock_session,
    column,
    value,
):
    """Discard invalid predictions while preserving valid ones."""
    image = np.zeros((640, 640, 3), dtype=np.uint8)

    valid = np.array(
        [100, 150, 40, 60, 0.90, 0.05, 0.05],
        dtype=np.float32,
    )

    invalid = valid.copy()
    invalid[column] = value

    output = np.stack([valid, invalid], axis=1)[np.newaxis, ...]
    yolo_with_mock_session.session.run.return_value = [output]

    detections = yolo_with_mock_session.detect(image)

    assert len(detections) == 1
    assert detections[0].cls == "person"
    assert detections[0].conf == pytest.approx(0.90)
