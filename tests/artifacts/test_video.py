"""Test video loading, saving, and reference reconstruction."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from mlops_workflows.artifacts.video import VideoContent, VideoReference


def test_materialize(tmp_path: Path):
    """Load video frames and FPS without adding content to the reference."""
    path = tmp_path / "input.avi"
    fps = 10.0
    frames = [np.full((64, 64, 3), value, dtype=np.uint8) for value in (30, 120, 220)]

    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        fps,
        (64, 64),
    )

    try:
        assert writer.isOpened(), "Could not create the test video."

        for frame in frames:
            writer.write(frame)
    finally:
        writer.release()

    reference = VideoReference(name="input", location=str(path))

    content = reference.materialize()

    assert isinstance(content, VideoContent)
    assert not hasattr(reference, "data")
    assert content.fps == pytest.approx(fps)
    assert len(content.data) == len(frames)

    for loaded, expected in zip(content.data, frames):
        assert loaded.shape == expected.shape
        assert loaded.dtype == np.uint8
        np.testing.assert_allclose(loaded, expected, atol=5, rtol=0)


def test_dematerialize(tmp_path: Path):
    """Save video content and check the file using OpenCV directly."""
    fps = 10.0
    frames = [np.full((64, 64, 3), value, dtype=np.uint8) for value in (30, 120, 220)]
    original_frames = [frame.copy() for frame in frames]

    content = VideoContent(data=frames, fps=fps)

    path = tmp_path / "results" / "output.avi"
    destination = VideoReference(name="output", location=str(path))

    location = content.dematerialize(destination)

    assert location == str(path)
    assert path.is_file()
    assert not hasattr(destination, "data")
    assert content.fps == pytest.approx(fps)

    capture = cv2.VideoCapture(str(path))

    try:
        assert capture.isOpened()
        assert capture.get(cv2.CAP_PROP_FPS) == pytest.approx(fps)

        saved_frames = []

        while True:
            success, frame = capture.read()

            if not success:
                break

            saved_frames.append(frame)
    finally:
        capture.release()

    assert len(saved_frames) == len(original_frames)

    for saved, expected in zip(saved_frames, original_frames):
        assert saved.shape == expected.shape
        assert saved.dtype == np.uint8
        np.testing.assert_allclose(saved, expected, atol=5, rtol=0)

    assert len(content.data) == len(original_frames)

    for stored, expected in zip(content.data, original_frames):
        np.testing.assert_array_equal(stored, expected)


def test_video_round_trip(tmp_path: Path):
    """Load, save, serialize the reference, and reload the video."""
    fps = 10.0
    frames = [np.full((64, 64, 3), value, dtype=np.uint8) for value in (30, 120, 220)]

    source_path = tmp_path / "input.avi"
    writer = cv2.VideoWriter(
        str(source_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        fps,
        (64, 64),
    )

    try:
        assert writer.isOpened(), "Could not create the test video."

        for frame in frames:
            writer.write(frame)
    finally:
        writer.release()

    source = VideoReference(name="input", location=str(source_path))
    content = source.materialize()

    destination = VideoReference(
        name="output",
        location=str(tmp_path / "results" / "output.avi"),
    )

    location = content.dematerialize(destination)

    assert location == destination.location
    assert destination.model_dump() == {
        "name": "output",
        "location": str(tmp_path / "results" / "output.avi"),
    }

    message = destination.model_dump_json()
    recovered_reference = VideoReference.model_validate_json(message)

    assert recovered_reference == destination
    assert recovered_reference is not destination
    assert not hasattr(recovered_reference, "data")

    recovered_content = recovered_reference.materialize()

    assert recovered_content.fps == pytest.approx(fps)
    assert len(recovered_content.data) == len(frames)

    for loaded, expected in zip(recovered_content.data, frames):
        assert loaded.shape == expected.shape
        assert loaded.dtype == np.uint8
        np.testing.assert_allclose(loaded, expected, atol=5, rtol=0)


def test_materialize_missing_file(tmp_path: Path):
    """Reject a reference to a missing video file."""
    reference = VideoReference(
        name="missing",
        location=str(tmp_path / "missing.avi"),
    )

    with pytest.raises(FileNotFoundError):
        reference.materialize()


def test_dematerialize_frames_with_different_sizes(tmp_path: Path):
    """Reject frames with different dimensions before creating a file."""
    content = VideoContent(
        data=[
            np.zeros((64, 64, 3), dtype=np.uint8),
            np.zeros((32, 64, 3), dtype=np.uint8),
        ],
        fps=10.0,
    )
    destination = VideoReference(
        name="output",
        location=str(tmp_path / "output.avi"),
    )

    with pytest.raises(ValueError, match="All frames must have the same size"):
        content.dematerialize(destination)

    assert not Path(destination.location).exists()


def test_dematerialize_writer_failure(tmp_path: Path, monkeypatch):
    """Report a writer failure and release the resource."""

    class FailedWriter:
        def __init__(self):
            self.released = False

        def isOpened(self):
            return False

        def release(self):
            self.released = True

    writer = FailedWriter()
    monkeypatch.setattr(cv2, "VideoWriter", lambda *args: writer)

    content = VideoContent(
        data=[np.zeros((64, 64, 3), dtype=np.uint8)],
        fps=10.0,
    )
    destination = VideoReference(
        name="output",
        location=str(tmp_path / "output.avi"),
    )

    with pytest.raises(OSError, match="Could not create the video"):
        content.dematerialize(destination)

    assert writer.released
