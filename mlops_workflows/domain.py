"""Dados e contratos para a execução de pipelines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

# DADOS


class ArtifactContent(BaseModel):
    """Conteúdo carregado ou produzido durante o processamento."""

    data: object


class Artifact(BaseModel, ABC):
    """Referência de um artefato e operações sobre seu conteúdo."""

    model_config = ConfigDict(strict=True, extra="forbid")

    name: str = Field(min_length=1)
    location: str = Field(min_length=1)

    @abstractmethod
    def materialize(self) -> ArtifactContent:
        """Carrega o conteúdo."""
        raise NotImplementedError

    @abstractmethod
    def dematerialize(self, content: ArtifactContent) -> None:
        """Armazena o conteúdo."""
        raise NotImplementedError


class Event(BaseModel):
    """Pedido que inicia o processamento."""

    model_config = ConfigDict(strict=True, extra="forbid")

    pipeline_id: str = Field(min_length=1)
    sensor_data: Artifact
    shop_id: str = Field(min_length=1)
    sensor_id: str = Field(min_length=1)


# COMPONENTE E ESTRUTURA DO PIPELINE


class Component(ABC):
    """Contrato das tarefas que processam os dados."""

    @abstractmethod
    def prepare(self, input_artifacts: list[Artifact]) -> object:
        """Carrega e prepara as entradas."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, prepared_data: object) -> list[Artifact]:
        """Processa, armazena as saídas e retorna suas referências."""
        raise NotImplementedError


@dataclass
class Step:
    """Uma etapa e suas dependências."""

    step_name: str
    component: Component
    depends_on: list["Step"] = field(default_factory=list)
    input_artifacts: list[Artifact] = field(default_factory=list)
    output_artifacts: list[Artifact] = field(default_factory=list)


@dataclass
class Pipeline:
    """Conjunto de etapas de um processamento."""

    pipeline_id: str
    steps: list[Step]


# CONSULTA E EXECUÇÃO


class PipelineRepository(ABC):
    @abstractmethod
    def get_by_id(self, pipeline_id: str) -> Pipeline:
        """Busca um pipeline pelo identificador."""
        raise NotImplementedError


class StepSelector:
    def execute(
        self,
        pipeline: Pipeline,
        started_steps: list[Step],
        completed_steps: list[Step],
    ) -> list[Step]:
        """Seleciona etapas não iniciadas com dependências concluídas."""
        raise NotImplementedError


class ComponentExecutor:
    def execute(
        self,
        component: Component,
        input_artifacts: list[Artifact],
    ) -> list[Artifact]:
        """Chama prepare() e execute() do componente."""
        raise NotImplementedError


class WorkflowRunner:
    def run(self, event: Event, pipeline: Pipeline) -> None:
        """Coordena as etapas até a conclusão ou falha."""
        raise NotImplementedError


class PipelineSelector:
    def execute(self, event: Event) -> Pipeline:
        """Busca o pipeline, aciona o workflow e retorna o pipeline."""
        raise NotImplementedError
