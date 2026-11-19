"""Test ImageContent validation and isolated write errors."""

from pathlib import Path

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference


@pytest.fixture
def pixels() -> np.ndarray:
    """Provide a small BGR image."""
    return np.array(
        [
            [[0, 0, 255], [0, 255, 0]],
            [[255, 0, 0], [255, 255, 255]],
        ],
        dtype=np.uint8,
    )


def test_content_requires_data():
    """Require data when creating image content."""
    with pytest.raises(ValidationError):
        ImageContent()


@pytest.mark.parametrize("data", [None, "image", b"image", [1, 2, 3]])
def test_content_rejects_incompatible_data(data: object):
    """Reject values that are not NumPy arrays."""
    with pytest.raises(ValidationError):
        ImageContent(data=data)


def test_content_rejects_an_empty_array():
    """Reject an array without pixels."""
    empty = np.empty((0, 0, 3), dtype=np.uint8)

    with pytest.raises(ValidationError):
        ImageContent(data=empty)


def test_content_validates_assignment(pixels: np.ndarray):
    """Reject incompatible data assigned after construction."""
    content = ImageContent(data=pixels)

    with pytest.raises(ValidationError):
        content.data = None

    np.testing.assert_array_equal(content.data, pixels)


def test_dematerialize_reports_a_write_failure(
    pixels: np.ndarray,
    monkeypatch: pytest.MonkeyPatch,
):
    """Report an unsuccessful OpenCV write without accessing the disk."""

    def skip_directory_creation(*args, **kwargs):
        """Avoid creating directories during this unit test."""
        return

    def fail_to_write(*args, **kwargs):
        """Simulate an unsuccessful image write."""
        return False

    monkeypatch.setattr(Path, "mkdir", skip_directory_creation)
    monkeypatch.setattr(cv2, "imwrite", fail_to_write)

    content = ImageContent(data=pixels)
    reference = ImageReference(name="output", location="output.png")

    with pytest.raises(OSError, match="Could not save the image"):
        content.dematerialize(reference)


def test_dematerialize_rejects_content_emptied_in_place(
    pixels: np.ndarray,
):
    """Reject content emptied after its initial validation."""
    content = ImageContent(data=pixels.copy())
    content.data.resize((0, 0, 3), refcheck=False)
    reference = ImageReference(name="output", location="output.png")

    with pytest.raises(ValueError, match="Image data must not be empty"):
        content.dematerialize(reference)
