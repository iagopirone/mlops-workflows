"""Test image artifacts with OpenCV and real temporary files."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference


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
    """Create an input PNG independently of the artifact classes."""
    path = tmp_path / "input.png"

    if not cv2.imwrite(str(path), pixels):
        raise RuntimeError("Could not create the test image.")

    return path


def test_reference_does_not_require_an_existing_file(tmp_path: Path):
    """Allow a reference to a future output file."""
    path = tmp_path / "future.png"

    reference = ImageReference(name="future", location=str(path))

    assert reference.location == str(path)
    assert not path.exists()


def test_materialize_loads_expected_pixels(
    image_path: Path,
    pixels: np.ndarray,
):
    """Load a real PNG into image content."""
    reference = ImageReference(name="input", location=str(image_path))

    content = reference.materialize()

    assert isinstance(content, ImageContent)
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
    """Reject a real file that cannot be decoded as an image."""
    path = tmp_path / "invalid.png"
    path.write_text("This is not an image.", encoding="utf-8")
    reference = ImageReference(name="invalid", location=str(path))

    with pytest.raises(ValueError, match="Could not read the image"):
        reference.materialize()


def test_dematerialize_saves_expected_pixels(
    tmp_path: Path,
    pixels: np.ndarray,
):
    """Save a PNG in a new directory and preserve the input pixels."""
    expected = pixels.copy()
    content = ImageContent(data=pixels)
    path = tmp_path / "results" / "images" / "output.png"
    reference = ImageReference(name="output", location=str(path))

    location = content.dematerialize(reference)
    saved = cv2.imread(str(path))

    assert location == str(path)
    assert path.is_file()
    assert saved is not None
    np.testing.assert_array_equal(saved, expected)
    np.testing.assert_array_equal(content.data, expected)


def test_dematerialize_overwrites_an_existing_image(
    image_path: Path,
    pixels: np.ndarray,
):
    """Replace an existing image with new pixel data."""
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


def test_dematerialize_reports_an_invalid_parent(
    tmp_path: Path,
    pixels: np.ndarray,
):
    """Reject a destination whose parent is a file."""
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


def test_image_round_trip(
    tmp_path: Path,
    image_path: Path,
    pixels: np.ndarray,
):
    """Recover saved pixels from a serialized destination reference."""
    source = ImageReference(name="source", location=str(image_path))
    destination = ImageReference(
        name="destination",
        location=str(tmp_path / "copy.png"),
    )

    content = source.materialize()
    saved_location = content.dematerialize(destination)
    message = destination.model_dump_json()
    recovered_reference = ImageReference.model_validate_json(message)
    recovered_content = recovered_reference.materialize()
    original = cv2.imread(str(image_path))

    assert saved_location == destination.location
    assert recovered_reference == destination
    np.testing.assert_array_equal(recovered_content.data, pixels)
    np.testing.assert_array_equal(original, pixels)
