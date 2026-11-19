"""Test detection artifact serialization and loading."""

import json

import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_content import (
    DetectionContent,
)
from mlops_workflows.artifacts.detection.detection_reference import (
    DetectionReference,
)


def test_detection_artifact_round_trip(tmp_path):
    """Ensure detections can be saved and loaded without data loss."""
    reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )

    content = DetectionContent(
        data=[
            Detection(
                cls="person",
                conf=0.95,
                box=[10, 20, 100, 200],
            ),
            Detection(
                cls="car",
                conf=0.85,
                box=[30, 40, 150, 250],
            ),
        ]
    )

    location = content.dematerialize(reference)
    restored = reference.materialize()

    assert location == reference.location
    assert restored.data == content.data


def test_empty_detections_round_trip(tmp_path):
    """Ensure an empty list of detections can be saved and loaded."""
    reference = DetectionReference(
        name="empty_detections",
        location=str(tmp_path / "empty.json"),
    )

    content = DetectionContent(data=[])

    content.dematerialize(reference)
    restored = reference.materialize()

    assert restored.data == []


def test_detection_reference_rejects_missing_file(tmp_path):
    """Ensure loading a nonexistent file raises an error."""
    reference = DetectionReference(
        name="missing_detections",
        location=str(tmp_path / "missing.json"),
    )

    with pytest.raises(FileNotFoundError):
        reference.materialize()


@pytest.mark.parametrize(
    "invalid_data",
    [
        {"cls": "person"},
        [{"cls": "person", "conf": 1.5, "box": [1, 2, 3, 4]}],
        [{"cls": "person", "conf": 0.9, "box": [1, 2]}],
    ],
)
def test_detection_reference_rejects_invalid_data(
    tmp_path,
    invalid_data,
):
    """Ensure invalid detection data is rejected."""
    path = tmp_path / "invalid.json"

    path.write_text(
        json.dumps(invalid_data),
        encoding="utf-8",
    )

    reference = DetectionReference(
        name="invalid_detections",
        location=str(path),
    )

    with pytest.raises((TypeError, ValueError, ValidationError)):
        reference.materialize()


def test_detection_without_confidence_round_trip(tmp_path):
    """Save an unknown confidence as JSON null and load it back as None."""
    reference = DetectionReference(
        name="text_detections",
        location=str(tmp_path / "text_detections.json"),
    )
    content = DetectionContent(
        data=[Detection(cls="WBC", conf=None, box=[1, 2, 3, 4])],
    )

    content.dematerialize(reference)

    saved = json.loads((tmp_path / "text_detections.json").read_text("utf-8"))
    restored = reference.materialize()

    assert saved == [{"cls": "WBC", "conf": None, "box": [1.0, 2.0, 3.0, 4.0]}]
    assert restored.data[0].conf is None


def test_detection_requires_explicit_confidence():
    """Require conf to be given, even when it is None."""
    with pytest.raises(ValidationError):
        Detection(cls="WBC", box=[1, 2, 3, 4])


@pytest.mark.parametrize("conf", [-0.01, 1.01])
def test_detection_rejects_confidence_out_of_range(conf):
    """Keep validating numeric confidence values."""
    with pytest.raises(ValidationError):
        Detection(cls="WBC", conf=conf, box=[1, 2, 3, 4])
