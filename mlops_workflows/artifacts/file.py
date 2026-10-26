"""Artefato que carrega e armazena arquivos locais em bytes."""

from pathlib import Path

from mlops_workflows.artifacts.content import ArtifactContent
from mlops_workflows.artifacts.interface import Artifact


class FileArtifact(Artifact, ArtifactContent):
    def materialize(self) -> ArtifactContent:
        """Carrega o conteúdo no próprio objeto e o retorna."""
        path = Path(self.location)
        self.data = path.read_bytes()

        return self

    def dematerialize(self, content: ArtifactContent) -> str:
        """Salva o conteúdo e retorna a localização do arquivo."""
        if not isinstance(content.data, bytes):
            raise TypeError("O conteúdo deve ser do tipo bytes.")

        path = Path(self.location)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.data)

        self.data = content.data
        return self.location
