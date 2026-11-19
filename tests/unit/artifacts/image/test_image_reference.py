"""Test ImageReference validation and serialization."""

import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.image.image_reference import ImageReference


def test_reference_stores_name_and_location():
    """Store reference fields without loading content."""
    reference = ImageReference(
        name="image",
        location="input.png",
    )

    assert reference.name == "image"
    assert reference.location == "input.png"
    assert not hasattr(reference, "data")


@pytest.mark.parametrize("location", ["", " ", "\t\n"])
def test_reference_rejects_blank_locations(location: str):
    """Reject blank locations."""
    with pytest.raises(ValidationError):
        ImageReference(name="image", location=location)


def test_reference_rejects_an_empty_name():
    """Reject an empty reference name."""
    with pytest.raises(ValidationError):
        ImageReference(name="", location="input.png")


def test_reference_validates_location_assignment():
    """Reject a blank location assigned after construction."""
    reference = ImageReference(name="image", location="input.png")

    with pytest.raises(ValidationError):
        reference.location = "   "

    assert reference.location == "input.png"


def test_reference_json_contains_only_reference_fields():
    """Serialize reference fields without image content."""
    reference = ImageReference(name="image", location="input.png")

    message = reference.model_dump_json()
    recovered = ImageReference.model_validate_json(message)

    assert reference.model_dump() == {
        "name": "image",
        "location": "input.png",
    }
    assert recovered == reference
    assert recovered is not reference
