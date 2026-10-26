"""Contrato para carregar e armazenar conteúdos de artefatos."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field

from mlops_workflows.artifacts.content import ArtifactContent


class Artifact(BaseModel, ABC):
    model_config = ConfigDict(strict=True, extra="forbid")

    name: str = Field(min_length=1)
    location: str = Field(min_length=1)

    @abstractmethod
    def materialize(self) -> ArtifactContent:
        """Carrega o conteúdo referenciado pelo artefato."""
        raise NotImplementedError

    @abstractmethod
    def dematerialize(self, content: ArtifactContent) -> str:  # retorna a referência
        """Armazena o conteúdo na localização do artefato."""
        raise NotImplementedError


"""1. Criar uma classe-filho que herde tanto da Artifact quanto do ArtifactContent
1. Implementar o que foi feito até agora (um artefato de verdade), fazendo os testes:
 - um artefato de um vídeo, um de detecção de imagens, etc. e ver como as coisas funcionam
 - trabalhar localmente (a referência é local)
 - a desmaterialização salva

2. O BaseModel tem recursos para manipular os campos: converter pra Jason, adicionar... aprender essa estruturação. Assim, eu posso usar só o BaseModel para fazer estruturação.

"""
