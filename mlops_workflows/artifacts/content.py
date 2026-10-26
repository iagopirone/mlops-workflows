"""Conteúdo carregado ou produzido durante o processamento."""

from pydantic import BaseModel


class ArtifactContent(BaseModel):
    data: object = None  # permite criar o objeto sem informar data, ou seja, o conteúdo ainda não está disponível no objeto
