from pathlib import Path

import cv2
import numpy as np
import pytest

from mlops_workflows.artifacts.video import VideoArtifact


def test_materialize(tmp_path: Path):
    path = tmp_path / "entrada.avi"
    fps = 10.0

    frames = [np.full((64, 64, 3), value, dtype=np.uint8) for value in (30, 120, 220)]

    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        fps,
        (64, 64),
    )

    try:
        assert writer.isOpened(), "Não foi possível criar o vídeo de teste."

        for frame in frames:
            writer.write(frame)
    finally:
        writer.release()

    artifact = VideoArtifact(
        name="video_entrada",
        location=str(path),
    )

    result = artifact.materialize()

    assert result is artifact
    assert artifact.fps == pytest.approx(fps)
    assert artifact.data is not None
    assert len(artifact.data) == len(frames)

    for loaded, expected in zip(artifact.data, frames):
        assert loaded.shape == expected.shape
        assert loaded.dtype == np.uint8
        np.testing.assert_allclose(loaded, expected, atol=5, rtol=0)


def test_dematerialize(tmp_path: Path):
    fps = 10.0
    frames = [np.full((64, 64, 3), value, dtype=np.uint8) for value in (30, 120, 220)]

    content = VideoArtifact(
        name="video_em_memoria",
        location=str(tmp_path / "origem.avi"),
        data=frames,
        fps=fps,
    )

    path = tmp_path / "resultados" / "saida.avi"
    artifact = VideoArtifact(
        name="video_saida",
        location=str(path),
    )

    reference = artifact.dematerialize(content)

    assert reference == str(path)
    assert path.is_file()
    assert artifact.fps == pytest.approx(fps)
    assert artifact.data is not None
    assert len(artifact.data) == len(frames)

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

    assert len(saved_frames) == len(frames)

    for saved, expected in zip(saved_frames, frames):
        assert saved.shape == expected.shape
        assert saved.dtype == np.uint8
        np.testing.assert_allclose(saved, expected, atol=5, rtol=0)

    for stored, expected in zip(artifact.data, frames):
        np.testing.assert_array_equal(stored, expected)


def test_video_round_trip(tmp_path: Path):
    fps = 10.0
    frames = [np.full((64, 64, 3), value, dtype=np.uint8) for value in (30, 120, 220)]

    source_path = tmp_path / "entrada.avi"
    writer = cv2.VideoWriter(
        str(source_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        fps,
        (64, 64),
    )

    try:
        assert writer.isOpened()

        for frame in frames:
            writer.write(frame)
    finally:
        writer.release()

    source = VideoArtifact(
        name="entrada",
        location=str(source_path),
    )
    source.materialize()

    destination = VideoArtifact(
        name="saida",
        location=str(tmp_path / "resultados" / "saida.avi"),
    )
    reference = destination.dematerialize(source)

    assert reference == destination.location

    message = destination.model_dump_json(include={"name", "location", "fps"})

    recovered = VideoArtifact.model_validate_json(message)

    assert recovered.data is None
    assert recovered.fps == pytest.approx(fps)

    recovered.materialize()

    assert recovered.fps == pytest.approx(fps)
    assert recovered.data is not None
    assert len(recovered.data) == len(frames)

    for loaded, expected in zip(recovered.data, frames):
        assert loaded.shape == expected.shape
        assert loaded.dtype == np.uint8
        np.testing.assert_allclose(loaded, expected, atol=5, rtol=0)
