"""Tests for the class count reference."""

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


@pytest.mark.parametrize(
    "class_count",
    [
        ClassCount(
            classes=["RBC", "WBC", "Platelets"],
            counts={"RBC": 2, "WBC": 1, "Platelets": 0},
            total=3,
            excluded={"Bacteria": 1},
            detection_count=4,
        ),
        ClassCount(
            classes=None,
            counts={"WBC": 1, "RBC": 2},
            total=3,
            excluded={},
            detection_count=3,
        ),
        ClassCount(
            classes=[],
            counts={},
            total=0,
            excluded={"RBC": 2},
            detection_count=2,
        ),
    ],
)
def test_round_trip_preserves_counts(tmp_path, class_count):
    """Load the same counts, in the same order, that were saved."""
    reference = ClassCountReference(
        name="counts",
        location=str(tmp_path / "counts.json"),
    )

    ClassCountContent(data=class_count).dematerialize(reference)
    loaded = reference.materialize()

    assert isinstance(loaded, ClassCountContent)
    assert loaded.data == class_count
    assert list(loaded.data.counts) == list(class_count.counts)


def test_materialize_rejects_missing_file(tmp_path):
    """Raise when the file does not exist."""
    reference = ClassCountReference(
        name="counts",
        location=str(tmp_path / "missing.json"),
    )

    with pytest.raises(FileNotFoundError):
        reference.materialize()


def test_materialize_revalidates_the_file(tmp_path):
    """Reject a saved file whose counts do not add up."""
    path = tmp_path / "counts.json"
    path.write_text(
        json.dumps(
            {
                "classes": None,
                "counts": {"RBC": 2},
                "total": 5,
                "excluded": {},
                "detection_count": 5,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        ClassCountReference(name="counts", location=str(path)).materialize()


def test_reference_requires_name_and_location():
    """Reject empty or blank reference fields."""
    with pytest.raises(ValidationError):
        ClassCountReference(name="", location="counts.json")

    with pytest.raises(ValidationError):
        ClassCountReference(name="counts", location="   ")
