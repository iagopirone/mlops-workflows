"""Test DetectionContent validation and JSON persistence.

The saved file is read directly with ``json`` so these tests do not depend on
``DetectionReference.materialize()``.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_content import (
    DetectionContent,
)
from mlops_workflows.artifacts.detection.detection_reference import (
    DetectionReference,
)


@pytest.fixture
def detections() -> list[Detection]:
    """Provide detections with and without confidence."""
    return [
        Detection(cls="WBC", conf=0.95, box=[10, 20, 100, 200]),
        Detection(cls="RBC", conf=None, box=[30.5, 40, 150, 250.25]),
    ]


def _reference(path: Path) -> DetectionReference:
    """Point a reference to a JSON file."""
    return DetectionReference(name="detections", location=str(path))


def _saved(path: Path) -> object:
    """Read the saved JSON file without materializing it."""
    return json.loads(path.read_text(encoding="utf-8"))


def test_content_requires_data():
    """Require data when creating detection content."""
    with pytest.raises(ValidationError):
        DetectionContent()


def test_content_accepts_an_empty_list():
    """Allow content without detections."""
    assert DetectionContent(data=[]).data == []


@pytest.mark.parametrize(
    "data",
    [
        None,
        "detections",
        Detection(cls="WBC", conf=0.9, box=[1, 2, 3, 4]),
        (Detection(cls="WBC", conf=0.9, box=[1, 2, 3, 4]),),
    ],
)
def test_content_rejects_data_that_is_not_a_list(data: object):
    """Reject values that are not lists, including tuples in strict mode."""
    with pytest.raises(ValidationError):
        DetectionContent(data=data)


@pytest.mark.parametrize("item", [None, "WBC", 1])
def test_content_rejects_items_that_are_not_detections(
    detections: list[Detection],
    item: object,
):
    """Reject a list that contains anything other than detections."""
    with pytest.raises(ValidationError):
        DetectionContent(data=[*detections, item])


def test_content_rejects_extra_fields(detections: list[Detection]):
    """Reject fields other than data."""
    with pytest.raises(ValidationError):
        DetectionContent(data=detections, source="model")


def test_content_validates_assignment(detections: list[Detection]):
    """Reject incompatible data assigned after construction."""
    content = DetectionContent(data=detections)

    with pytest.raises(ValidationError):
        content.data = "detections"

    assert content.data == detections


def test_dematerialize_returns_the_reference_location(
    tmp_path: Path,
    detections: list[Detection],
):
    """Return the location where the detections were saved."""
    reference = _reference(tmp_path / "detections.json")

    location = DetectionContent(data=detections).dematerialize(reference)

    assert location == reference.location


def test_dematerialize_saves_detections_as_a_json_list(
    tmp_path: Path,
    detections: list[Detection],
):
    """Save every field of every detection, in order."""
    path = tmp_path / "detections.json"

    DetectionContent(data=detections).dematerialize(_reference(path))

    assert _saved(path) == [
        {"cls": "WBC", "conf": 0.95, "box": [10.0, 20.0, 100.0, 200.0]},
        {"cls": "RBC", "conf": None, "box": [30.5, 40.0, 150.0, 250.25]},
    ]


def test_dematerialize_saves_missing_confidence_as_null(tmp_path: Path):
    """Keep conf as JSON null instead of inventing a value."""
    path = tmp_path / "detections.json"
    content = DetectionContent(data=[Detection(cls="WBC", conf=None, box=[1, 2, 3, 4])])

    content.dematerialize(_reference(path))

    assert _saved(path)[0]["conf"] is None


def test_dematerialize_saves_an_empty_list(tmp_path: Path):
    """Save content without detections as an empty JSON list."""
    path = tmp_path / "detections.json"

    DetectionContent(data=[]).dematerialize(_reference(path))

    assert _saved(path) == []


def test_dematerialize_creates_parent_directories(
    tmp_path: Path,
    detections: list[Detection],
):
    """Create missing parent directories before saving."""
    path = tmp_path / "nested" / "run" / "detections.json"

    DetectionContent(data=detections).dematerialize(_reference(path))

    assert path.is_file()


def test_dematerialize_overwrites_an_existing_file(
    tmp_path: Path,
    detections: list[Detection],
):
    """Replace the previous content of the destination file."""
    path = tmp_path / "detections.json"
    path.write_text("previous content", encoding="utf-8")

    DetectionContent(data=detections[:1]).dematerialize(_reference(path))

    assert _saved(path) == [
        {"cls": "WBC", "conf": 0.95, "box": [10.0, 20.0, 100.0, 200.0]},
    ]
