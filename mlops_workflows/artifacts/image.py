"""Artefato para carregar e salvar imagens locais."""

from pathlib import Path

import cv2
import numpy as np
from pydantic import ConfigDict

from mlops_workflows.artifacts.content import ArtifactContent
from mlops_workflows.artifacts.interface import Artifact


class ImageArtifact(Artifact, ArtifactContent):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    data: np.ndarray | None = None

    def materialize(self) -> ArtifactContent:
        """Carrega a imagem como uma matriz de pixels em BGR."""
        path = Path(self.location)

        if not path.is_file():
            raise FileNotFoundError(f"Imagem não encontrada: {path}")

        image = cv2.imread(str(path))

        if image is None:
            raise ValueError(f"Não foi possível ler a imagem: {path}")

        self.data = image
        return self

    def dematerialize(self, content: ArtifactContent) -> str:
        """Salva a matriz de pixels e retorna a localização."""
        if not isinstance(content.data, np.ndarray):
            raise TypeError("O conteúdo deve ser uma matriz NumPy.")

        if content.data.size == 0:
            raise ValueError("A imagem não pode estar vazia.")

        path = Path(self.location)
        path.parent.mkdir(parents=True, exist_ok=True)

        saved = cv2.imwrite(str(path), content.data)

        if not saved:
            raise OSError(f"Não foi possível salvar a imagem: {path}")

        self.data = content.data
        return self.location
