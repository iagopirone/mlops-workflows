"""Test ImageContent persistence with OpenCV and real temporary files."""

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
