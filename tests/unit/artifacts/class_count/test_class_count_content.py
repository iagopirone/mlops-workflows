"""Tests for the class count content."""

import json

import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.class_count.class_count import ClassCount
from mlops_workflows.artifacts.class_count.class_count_content import (
    ClassCountContent,
)
from mlops_workflows.artifacts.class_count.class_count_reference import (
    ClassCountReference,
)


def make_class_count() -> ClassCount:
    """Return restricted counts with a zero and an exclusion."""
    return ClassCount(
        classes=["RBC", "WBC", "Platelets"],
        counts={"RBC": 2, "WBC": 1, "Platelets": 0},
        total=3,
        excluded={"Bacteria": 1},
        detection_count=4,
    )


def test_data_must_be_a_class_count():
    """Reject data that is not a ClassCount."""
    with pytest.raises(ValidationError):
        ClassCountContent(data={"RBC": 2})


def test_dematerialize_writes_json(tmp_path):
    """Save every field as JSON, creating parent folders."""
    reference = ClassCountReference(
        name="counts",
        location=str(tmp_path / "nested" / "counts.json"),
    )

    location = ClassCountContent(data=make_class_count()).dematerialize(reference)

    saved = json.loads((tmp_path / "nested" / "counts.json").read_text("utf-8"))

    assert location == reference.location
    assert saved == {
        "classes": ["RBC", "WBC", "Platelets"],
        "counts": {"RBC": 2, "WBC": 1, "Platelets": 0},
        "total": 3,
        "excluded": {"Bacteria": 1},
        "detection_count": 4,
    }
    assert list(saved["counts"]) == ["RBC", "WBC", "Platelets"]


def test_dematerialize_writes_null_domain(tmp_path):
    """Save generic counts with a null domain."""
    reference = ClassCountReference(
        name="counts",
        location=str(tmp_path / "counts.json"),
    )
    class_count = ClassCount(
        classes=None,
        counts={},
        total=0,
        excluded={},
        detection_count=0,
    )

    ClassCountContent(data=class_count).dematerialize(reference)

    saved = json.loads((tmp_path / "counts.json").read_text("utf-8"))

    assert saved["classes"] is None
