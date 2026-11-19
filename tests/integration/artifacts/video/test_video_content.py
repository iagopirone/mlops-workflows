"""Test VideoContent persistence with OpenCV and real temporary files."""

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
