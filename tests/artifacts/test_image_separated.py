"""Test image references, contents, loading, and saving."""

from pathlib import Path

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.image_separated import (
    ImageContent,
    ImageReference,
)


@pytest.fixture
def pixels() -> np.ndarray:
    """Provide a small BGR image with known pixel values."""
    return np.array(
        [
            [[0, 0, 255], [0, 255, 0]],
            [[255, 0, 0], [255, 255, 255]],
        ],
        dtype=np.uint8,
    )


@pytest.fixture
def image_path(tmp_path: Path, pixels: np.ndarray) -> Path:
    """Create a valid PNG independently of the artifact classes."""
    path = tmp_path / "input.png"
    assert cv2.imwrite(str(path), pixels)
    return path


# REFERENCE VALIDATION


def test_reference_does_not_require_an_existing_file(tmp_path: Path):
    """Allow references to files that will be created later."""
    path = tmp_path / "future.png"

    reference = ImageReference(
        name="future_image",
        location=str(path),
    )

    assert reference.location == str(path)
    assert not path.exists()


@pytest.mark.parametrize("location", ["", " ", "\t\n"])
def test_reference_rejects_blank_locations(location: str):
    """Reject empty locations and locations containing only whitespace."""
    with pytest.raises(ValidationError):
        ImageReference(name="image", location=location)


def test_reference_rejects_an_empty_name():
    """Reject references without a name."""
    with pytest.raises(ValidationError):
        ImageReference(name="", location="image.png")


def test_reference_rejects_invalid_location_assignment():
    """Validate location changes and preserve the previous valid value."""
    reference = ImageReference(
        name="image",
        location="original.png",
    )

    with pytest.raises(ValidationError):
        reference.location = "   "

    assert reference.location == "original.png"


# CONTENT VALIDATION


def test_content_requires_data():
    """Reject content objects created without data."""
    with pytest.raises(ValidationError):
        ImageContent()


@pytest.mark.parametrize("data", [None, "image", b"image", [1, 2, 3]])
def test_content_rejects_incompatible_data(data: object):
    """Reject values that are not NumPy arrays."""
    with pytest.raises(ValidationError):
        ImageContent(data=data)


def test_content_rejects_an_empty_array():
    """Reject arrays without pixels."""
    empty = np.empty((0, 0, 3), dtype=np.uint8)

    with pytest.raises(ValidationError):
        ImageContent(data=empty)


def test_content_validates_assignment(pixels: np.ndarray):
    """Reject incompatible data assigned after construction."""
    content = ImageContent(data=pixels)

    with pytest.raises(ValidationError):
        content.data = None

    np.testing.assert_array_equal(content.data, pixels)


# MATERIALIZATION


def test_materialize_loads_expected_pixels(
    image_path: Path,
    pixels: np.ndarray,
):
    """Return a content object containing the decoded image."""
    reference = ImageReference(
        name="input",
        location=str(image_path),
    )

    content = reference.materialize()

    assert isinstance(content, ImageContent)
    assert not hasattr(reference, "data")
    np.testing.assert_array_equal(content.data, pixels)


def test_materialize_rejects_a_missing_file(tmp_path: Path):
    """Report a missing source file."""
    reference = ImageReference(
        name="missing",
        location=str(tmp_path / "missing.png"),
    )

    with pytest.raises(FileNotFoundError):
        reference.materialize()


def test_materialize_rejects_a_directory(tmp_path: Path):
    """Reject a directory used as an image source."""
    reference = ImageReference(
        name="directory",
        location=str(tmp_path),
    )

    with pytest.raises(FileNotFoundError):
        reference.materialize()


def test_materialize_rejects_an_invalid_image(tmp_path: Path):
    """Reject a file whose contents cannot be decoded as an image."""
    path = tmp_path / "invalid.png"
    path.write_text("This is not an image.", encoding="utf-8")

    reference = ImageReference(
        name="invalid",
        location=str(path),
    )

    with pytest.raises(ValueError, match="Could not read the image"):
        reference.materialize()


# DEMATERIALIZATION


def test_dematerialize_saves_pixels_and_returns_location(
    tmp_path: Path,
    pixels: np.ndarray,
):
    """Create destination directories and save the expected pixels."""
    content = ImageContent(data=pixels)
    path = tmp_path / "results" / "images" / "output.png"
    reference = ImageReference(
        name="output",
        location=str(path),
    )

    location = content.dematerialize(reference)

    assert location == str(path)
    assert path.is_file()

    saved = cv2.imread(str(path))
    assert saved is not None
    np.testing.assert_array_equal(saved, pixels)
    np.testing.assert_array_equal(content.data, pixels)


def test_dematerialize_overwrites_an_existing_image(
    image_path: Path,
    pixels: np.ndarray,
):
    """Replace an existing image with the new content."""
    replacement = np.zeros_like(pixels)
    content = ImageContent(data=replacement)
    reference = ImageReference(
        name="replacement",
        location=str(image_path),
    )

    content.dematerialize(reference)

    saved = cv2.imread(str(image_path))
    assert saved is not None
    np.testing.assert_array_equal(saved, replacement)


def test_dematerialize_reports_a_write_failure(
    tmp_path: Path,
    pixels: np.ndarray,
    monkeypatch: pytest.MonkeyPatch,
):
    """Report failure when OpenCV cannot save the image."""

    def fail_to_write(*args, **kwargs):
        """Simulate an unsuccessful OpenCV write."""
        return False

    monkeypatch.setattr(cv2, "imwrite", fail_to_write)

    content = ImageContent(data=pixels)
    reference = ImageReference(
        name="output",
        location=str(tmp_path / "output.png"),
    )

    with pytest.raises(OSError, match="Could not save the image"):
        content.dematerialize(reference)


def test_dematerialize_reports_an_invalid_parent(
    tmp_path: Path,
    pixels: np.ndarray,
):
    """Report an error when a destination parent is a file."""
    parent = tmp_path / "parent"
    parent.write_bytes(b"existing file")

    reference = ImageReference(
        name="output",
        location=str(parent / "output.png"),
    )
    content = ImageContent(data=pixels)

    with pytest.raises(OSError):
        content.dematerialize(reference)

    assert parent.read_bytes() == b"existing file"


def test_dematerialize_rejects_content_emptied_in_place(
    tmp_path: Path,
    pixels: np.ndarray,
):
    """Reject an array emptied without assigning a new field value."""
    content = ImageContent(data=pixels.copy())

    # In-place changes do not trigger Pydantic assignment validation.
    content.data.resize((0, 0, 3), refcheck=False)

    path = tmp_path / "output.png"
    reference = ImageReference(
        name="output",
        location=str(path),
    )

    with pytest.raises(ValueError, match="Image data must not be empty"):
        content.dematerialize(reference)

    assert not path.exists()


# COMPLETE FLOW


def test_image_round_trip(
    tmp_path: Path,
    image_path: Path,
    pixels: np.ndarray,
):
    """Load, save, serialize the reference, and recover the image."""
    source = ImageReference(
        name="source",
        location=str(image_path),
    )
    content = source.materialize()

    destination = ImageReference(
        name="destination",
        location=str(tmp_path / "copy.png"),
    )
    saved_location = content.dematerialize(destination)

    assert saved_location == destination.location

    # The reference must never include the image pixels.
    assert set(destination.model_dump()) == {"name", "location"}

    message = destination.model_dump_json()
    recovered_reference = ImageReference.model_validate_json(message)
    recovered_content = recovered_reference.materialize()

    assert recovered_reference.name == destination.name
    assert recovered_reference.location == destination.location
    np.testing.assert_array_equal(recovered_content.data, pixels)

    # Saving to another location must preserve the source image.
    original = cv2.imread(str(image_path))
    np.testing.assert_array_equal(original, pixels)
