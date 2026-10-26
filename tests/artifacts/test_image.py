from pathlib import Path

import cv2
import numpy as np

from mlops_workflows.artifacts.image import ImageArtifact


def test_materialize(tmp_path: Path):
    expected = np.array(
        [
            [[0, 0, 255], [0, 255, 0]],
            [[255, 0, 0], [255, 255, 255]],
        ],
        dtype=np.uint8,
    )

    path = tmp_path / "entrada.png"
    assert cv2.imwrite(str(path), expected)

    artifact = ImageArtifact(
        name="imagem_entrada",
        location=str(path),
    )

    assert artifact.data is None

    result = artifact.materialize()

    assert result is artifact
    np.testing.assert_array_equal(artifact.data, expected)


def test_dematerialize(tmp_path: Path):
    expected = np.array(
        [
            [[0, 0, 255], [0, 255, 0]],
            [[255, 0, 0], [255, 255, 255]],
        ],
        dtype=np.uint8,
    )

    content = ImageArtifact(
        name="imagem_em_memoria",
        location=str(tmp_path / "origem.png"),
        data=expected,
    )

    path = tmp_path / "resultados" / "saida.png"
    artifact = ImageArtifact(
        name="imagem_saida",
        location=str(path),
    )

    reference = artifact.dematerialize(content)

    assert reference == str(path)
    assert path.is_file()

    saved = cv2.imread(str(path))
    assert saved is not None
    np.testing.assert_array_equal(saved, expected)
    np.testing.assert_array_equal(artifact.data, expected)


def test_image_round_trip(tmp_path: Path):
    expected = np.array(
        [
            [[0, 0, 255], [0, 255, 0]],
            [[255, 0, 0], [255, 255, 255]],
        ],
        dtype=np.uint8,
    )

    source_path = tmp_path / "entrada.png"
    assert cv2.imwrite(str(source_path), expected)

    source = ImageArtifact(
        name="entrada",
        location=str(source_path),
    )
    source.materialize()

    destination = ImageArtifact(
        name="saida",
        location=str(tmp_path / "resultados" / "saida.png"),
    )
    destination.dematerialize(source)

    message = destination.model_dump_json(include={"name", "location"})

    recovered = ImageArtifact.model_validate_json(message)
    assert recovered.data is None

    recovered.materialize()

    np.testing.assert_array_equal(recovered.data, expected)
