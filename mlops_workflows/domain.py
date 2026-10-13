"""Classes e contratos do domínio dos pipelines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ArtifactContent:
    data: object


@dataclass
class Artifact(ABC):
    name: str
    location: str

    @abstractmethod
    def materialize(self) -> ArtifactContent:
        """Obtém o conteúdo referenciado pelo artefato."""
        raise NotImplementedError

    @abstractmethod
    def dematerialize(self, content: ArtifactContent) -> None:
        """Armazena o conteúdo na localização do artefato."""
        raise NotImplementedError


@dataclass
class Event:
    pipeline_id: str
    sensor_data: Artifact
    shop_id: str
    sensor_id: str


class Component(ABC):
    @abstractmethod
    def prepare(self, input_artifacts: list[Artifact]) -> object:
        """Materializa as entradas e prepara os dados para execução."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, prepared_data: object) -> list[Artifact]:
        """Processa os dados, armazena as saídas e retorna suas referências."""
        raise NotImplementedError


@dataclass
class Step:
    step_name: str
    component: Component
    depends_on: list["Step"] = field(default_factory=list)
    input_artifacts: list[Artifact] = field(default_factory=list)
    output_artifacts: list[Artifact] = field(default_factory=list)


@dataclass
class Pipeline:
    pipeline_id: str
    steps: list[Step]


class PipelineRepository(ABC):
    @abstractmethod
    def get_by_id(self, pipeline_id: str) -> Pipeline:
        """Busca o pipeline pelo identificador."""
        raise NotImplementedError


class StepSelector:
    def execute(
        self,
        pipeline: Pipeline,
        started_steps: list[Step],
        completed_steps: list[Step],
    ) -> list[Step]:
        """Seleciona etapas não iniciadas cujas dependências foram concluídas."""
        raise NotImplementedError


class ComponentExecutor:
    def execute(
        self,
        component: Component,
        input_artifacts: list[Artifact],
    ) -> list[Artifact]:
        """Chama prepare() e execute() e retorna os artefatos de saída."""
        raise NotImplementedError


class WorkflowRunner:
    def run(self, event: Event, pipeline: Pipeline) -> None:
        """Coordena as etapas até a conclusão ou informa uma falha."""
        raise NotImplementedError


class PipelineSelector:
    def execute(self, event: Event) -> Pipeline:
        """Busca o pipeline, aciona o workflow e retorna o pipeline utilizado."""
        raise NotImplementedError
