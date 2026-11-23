"""Tests for the class count model."""

import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.class_count.class_count import ClassCount


def test_generic_counts_are_accepted():
    """Accept generic counts without exclusions."""
    class_count = ClassCount(
        classes=None,
        counts={"RBC": 2, "WBC": 1},
        total=3,
        excluded={},
        detection_count=3,
    )

    assert class_count.counts == {"RBC": 2, "WBC": 1}


def test_restricted_counts_are_accepted():
    """Accept restricted counts with zeros and exclusions."""
    class_count = ClassCount(
        classes=["RBC", "Platelets"],
        counts={"RBC": 2, "Platelets": 0},
        total=2,
        excluded={"Bacteria": 1},
        detection_count=3,
    )

    assert class_count.excluded == {"Bacteria": 1}


def test_empty_domain_is_accepted():
    """Accept an empty domain where every detection is excluded."""
    class_count = ClassCount(
        classes=[],
        counts={},
        total=0,
        excluded={"RBC": 2},
        detection_count=2,
    )

    assert class_count.total == 0


@pytest.mark.parametrize(
    "fields",
    [
        # Total does not match the counts.
        {"classes": None, "counts": {"RBC": 2}, "total": 3, "detection_count": 3},
        # Detection count does not match total plus excluded.
        {"classes": None, "counts": {"RBC": 2}, "total": 2, "detection_count": 3},
        # Generic counting cannot exclude classes.
        {
            "classes": None,
            "counts": {"RBC": 2},
            "total": 2,
            "excluded": {"WBC": 1},
            "detection_count": 3,
        },
        # Generic counting only lists detected classes.
        {"classes": None, "counts": {"RBC": 0}, "total": 0, "detection_count": 0},
        # Duplicate configured classes.
        {
            "classes": ["RBC", "RBC"],
            "counts": {"RBC": 1},
            "total": 1,
            "detection_count": 1,
        },
        # Counts missing a configured class.
        {"classes": ["RBC", "WBC"], "counts": {"RBC": 1}, "total": 1},
        # Counts in a different order from the configured classes.
        {
            "classes": ["RBC", "WBC"],
            "counts": {"WBC": 0, "RBC": 1},
            "total": 1,
            "detection_count": 1,
        },
        # Counts with a class outside the domain.
        {
            "classes": ["RBC"],
            "counts": {"RBC": 1, "WBC": 1},
            "total": 2,
            "detection_count": 2,
        },
        # Excluded class inside the domain.
        {
            "classes": ["RBC"],
            "counts": {"RBC": 1},
            "total": 1,
            "excluded": {"RBC": 1},
            "detection_count": 2,
        },
        # Negative count.
        {"classes": ["RBC"], "counts": {"RBC": -1}, "total": -1},
        # Zero exclusion.
        {
            "classes": ["RBC"],
            "counts": {"RBC": 1},
            "total": 1,
            "excluded": {"WBC": 0},
            "detection_count": 1,
        },
    ],
)
def test_inconsistent_counts_are_rejected(fields):
    """Reject counts that do not add up or do not match the domain."""
    values = {"excluded": {}, "detection_count": 1, **fields}

    with pytest.raises(ValidationError):
        ClassCount(**values)


def test_strict_types_are_required():
    """Reject coerced values and unknown fields."""
    with pytest.raises(ValidationError):
        ClassCount(
            classes=None,
            counts={"RBC": "2"},
            total=2,
            excluded={},
            detection_count=2,
        )

    with pytest.raises(ValidationError):
        ClassCount(
            classes=("RBC",),
            counts={"RBC": 2},
            total=2,
            excluded={},
            detection_count=2,
        )

    with pytest.raises(ValidationError):
        ClassCount(
            classes=None,
            counts={},
            total=0,
            excluded={},
            detection_count=0,
            extra="field",
        )
