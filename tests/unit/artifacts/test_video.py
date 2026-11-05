"""Test isolated video behavior without reading or writing real videos."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from mlops_workflows.artifacts.video.video_content import VideoContent
from mlops_workflows.artifacts.video.video_reference import VideoReference


def test_dematerialize_rejects_different_frame_sizes():
    """Reject frames with different dimensions before saving."""
    content = VideoContent(
        data=[
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((32, 64, 3), dtype=np.uint8),
        ],
        fps=10.0,
    )
    destination = VideoReference(
        name="output",
        location="output.avi",
    )

    with pytest.raises(ValueError, match="All frames must have the same size"):
        content.dematerialize(destination)


def test_dematerialize_reports_writer_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    """Report a writer failure and release the resource."""

    class FailedWriter:
        """Simulate a video writer that cannot open its destination."""

        def __init__(self):
            self.released = False

        def isOpened(self):
            return False

        def release(self):
            self.released = True

    def skip_directory_creation(*args, **kwargs):
        """Avoid creating directories during this unit test."""
        return

    writer = FailedWriter()
    monkeypatch.setattr(cv2, "VideoWriter", lambda *args: writer)
    monkeypatch.setattr(Path, "mkdir", skip_directory_creation)

    content = VideoContent(
        data=[np.zeros((64, 64, 3), dtype=np.uint8)],
        fps=10.0,
    )
    destination = VideoReference(name="output", location="output.avi")

    with pytest.raises(OSError, match="Could not create the video"):
        content.dematerialize(destination)

    assert writer.released


def test_reference_json_contains_only_reference_fields():
    """Serialize and reconstruct a reference without video content."""
    reference = VideoReference(name="video", location="input.avi")

    message = reference.model_dump_json()
    recovered = VideoReference.model_validate_json(message)

    assert reference.model_dump() == {
        "name": "video",
        "location": "input.avi",
    }
    assert recovered == reference
    assert recovered is not reference
