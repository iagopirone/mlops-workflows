"""Artefato para carregar e salvar vídeos locais sem áudio."""

from math import isfinite
from pathlib import Path

import cv2
import numpy as np
from pydantic import ConfigDict, Field

from mlops_workflows.artifacts.content import ArtifactContent
from mlops_workflows.artifacts.interface import Artifact


class VideoArtifact(Artifact, ArtifactContent):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    data: list[np.ndarray] | None = None
    fps: float | None = Field(default=None, gt=0)

    def materialize(self) -> ArtifactContent:
        """Carrega os quadros em BGR e a taxa de reprodução."""
        path = Path(self.location)

        if not path.is_file():
            raise FileNotFoundError(f"Vídeo não encontrado: {path}")

        capture = cv2.VideoCapture(str(path))

        try:
            if not capture.isOpened():
                raise ValueError(f"Não foi possível abrir o vídeo: {path}")

            fps = capture.get(cv2.CAP_PROP_FPS)

            if not isfinite(fps) or fps <= 0:
                raise ValueError("O vídeo não possui um FPS válido.")

            frames = []

            while True:
                success, frame = capture.read()

                if not success:
                    break

                frames.append(frame)

            if not frames:
                raise ValueError("O vídeo não possui quadros legíveis.")
        finally:
            capture.release()

        self.data = frames
        self.fps = fps
        return self

    def dematerialize(self, content: ArtifactContent) -> str:
        """Salva os quadros como vídeo e retorna a localização."""
        if not isinstance(content, VideoArtifact):
            raise TypeError("O conteúdo deve ser um VideoArtifact.")

        if not isinstance(content.data, list) or not content.data:
            raise ValueError("O conteúdo deve conter uma lista de quadros.")

        if content.fps is None:
            raise ValueError("O FPS deve ser informado.")

        if not isfinite(content.fps) or content.fps <= 0:
            raise ValueError("O FPS deve ser positivo e finito.")

        for frame in content.data:
            if not isinstance(frame, np.ndarray):
                raise TypeError("Cada quadro deve ser uma matriz NumPy.")

            if (
                frame.dtype != np.uint8
                or frame.ndim != 3
                or frame.shape[2] != 3
                or frame.size == 0
            ):
                raise ValueError(
                    "Cada quadro deve ser uma imagem BGR não vazia em uint8."
                )

            if frame.shape != content.data[0].shape:
                raise ValueError("Todos os quadros devem ter o mesmo tamanho.")

        path = Path(self.location)
        codecs = {".avi": "MJPG", ".mp4": "mp4v"}
        codec = codecs.get(path.suffix.lower())

        if codec is None:
            raise ValueError("O destino deve ter extensão .avi ou .mp4.")

        height, width = content.data[0].shape[:2]
        path.parent.mkdir(parents=True, exist_ok=True)

        writer = cv2.VideoWriter(
            str(path),
            cv2.VideoWriter_fourcc(*codec),
            content.fps,
            (width, height),
        )

        try:
            if not writer.isOpened():
                raise OSError(f"Não foi possível criar o vídeo: {path}")

            for frame in content.data:
                writer.write(frame)
        finally:
            writer.release()

        self.data = content.data
        self.fps = content.fps
        return self.location
