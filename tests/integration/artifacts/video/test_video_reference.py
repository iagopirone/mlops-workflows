"""Test VideoReference loading with OpenCV and real temporary files."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from mlops_workflows.artifacts.video.video_content import VideoContent
from mlops_workflows.artifacts.video.video_reference import VideoReference


@pytest.fixture
def frames() -> list[np.ndarray]:
    """Provide three BGR frames with known pixel values."""
    return [np.full((64, 64, 3), value, dtype=np.uint8) for value in (30, 120, 220)]


@pytest.fixture
def video_path(tmp_path: Path, frames: list[np.ndarray]) -> Path:
    """Create an input video independently of the artifact classes."""
    path = tmp_path / "input.avi"
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        10.0,
        (64, 64),
    )

    try:
        if not writer.isOpened():
            raise RuntimeError("Could not create the test video.")

        for frame in frames:
            writer.write(frame)
    finally:
        writer.release()

    return path


def test_materialize_loads_frames_and_fps(
    video_path: Path,
    frames: list[np.ndarray],
):
    """Load the expected frames and playback rate from a real video."""
    reference = VideoReference(
        name="input",
        location=str(video_path),
    )

    content = reference.materialize()

    assert isinstance(content, VideoContent)
    assert content.fps == pytest.approx(10.0)
    assert len(content.data) == len(frames)

    for loaded, expected in zip(content.data, frames):
        assert loaded.shape == expected.shape
        assert loaded.dtype == np.uint8
        np.testing.assert_allclose(loaded, expected, atol=5, rtol=0)


def test_video_round_trip(
    tmp_path: Path,
    video_path: Path,
    frames: list[np.ndarray],
):
    """Recover a saved video from its serialized reference."""
    source = VideoReference(name="input", location=str(video_path))
    destination = VideoReference(
        name="output",
        location=str(tmp_path / "results" / "output.avi"),
    )

    content = source.materialize()
    location = content.dematerialize(destination)
    message = destination.model_dump_json()
    recovered_reference = VideoReference.model_validate_json(message)
    recovered_content = recovered_reference.materialize()

    assert location == destination.location
    assert recovered_reference == destination
    assert recovered_content.fps == pytest.approx(10.0)
    assert len(recovered_content.data) == len(frames)

    for loaded, expected in zip(recovered_content.data, frames):
        assert loaded.shape == expected.shape
        assert loaded.dtype == np.uint8
        np.testing.assert_allclose(loaded, expected, atol=5, rtol=0)


def test_materialize_rejects_a_missing_file(tmp_path: Path):
    """Report a source file that does not exist on disk."""
    reference = VideoReference(
        name="missing",
        location=str(tmp_path / "missing.avi"),
    )

    with pytest.raises(FileNotFoundError):
        reference.materialize()
