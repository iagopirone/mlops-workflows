"""Test video artifacts with OpenCV and real temporary files."""

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


def read_video(path: Path) -> tuple[float, list[np.ndarray]]:
    """Read a video directly with OpenCV to inspect a saved result."""
    capture = cv2.VideoCapture(str(path))

    try:
        if not capture.isOpened():
            raise RuntimeError(f"Could not inspect the video: {path}")

        fps = capture.get(cv2.CAP_PROP_FPS)
        frames = []

        while True:
            success, frame = capture.read()

            if not success:
                break

            frames.append(frame)

        return fps, frames
    finally:
        capture.release()


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


def test_dematerialize_saves_frames_and_fps(
    tmp_path: Path,
    frames: list[np.ndarray],
):
    """Save a real video without modifying the source content."""
    expected_frames = [frame.copy() for frame in frames]
    content = VideoContent(data=frames, fps=10.0)
    path = tmp_path / "results" / "output.avi"
    destination = VideoReference(name="output", location=str(path))

    location = content.dematerialize(destination)
    saved_fps, saved_frames = read_video(path)

    assert location == str(path)
    assert path.is_file()
    assert saved_fps == pytest.approx(10.0)
    assert content.fps == pytest.approx(10.0)
    assert len(saved_frames) == len(expected_frames)
    assert len(content.data) == len(expected_frames)

    for saved, expected in zip(saved_frames, expected_frames):
        assert saved.shape == expected.shape
        assert saved.dtype == np.uint8
        np.testing.assert_allclose(saved, expected, atol=5, rtol=0)

    for stored, expected in zip(content.data, expected_frames):
        np.testing.assert_array_equal(stored, expected)


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
