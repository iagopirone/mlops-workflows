"""Define data structures and contracts for pipeline execution."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.components.interface import Component


class Event(BaseModel):
    """Represent a request that starts processing."""

    model_config = ConfigDict(strict=True, extra="forbid")

    pipeline_id: str = Field(min_length=1)
    sensor_data: ArtifactReference
    shop_id: str = Field(min_length=1)
    sensor_id: str = Field(min_length=1)


@dataclass
class Step:
    """Represent a processing step and its dependencies."""

    step_name: str
    component: Component
    depends_on: list["Step"] = field(default_factory=list)
    input_artifacts: list[ArtifactReference] = field(default_factory=list)
    output_artifacts: list[ArtifactReference] = field(default_factory=list)


@dataclass
class Pipeline:
    """Group the steps that define a processing workflow."""

    pipeline_id: str
    steps: list[Step]


class PipelineRepository(ABC):
    """Define how pipelines are retrieved."""

    @abstractmethod
    def get_by_id(self, pipeline_id: str) -> Pipeline:
        """Find a pipeline by its identifier."""
        raise NotImplementedError


class StepSelector:
    def execute(
        self,
        pipeline: Pipeline,
        started_steps: list[Step],
        completed_steps: list[Step],
    ) -> list[Step]:
        """Select unstarted steps whose dependencies are completed."""
        raise NotImplementedError


class ComponentExecutor:
    def execute(
        self,
        component: Component,
        input_artifacts: list[ArtifactReference],
    ) -> list[ArtifactReference]:
        """Call the component's preparation and execution methods."""
        raise NotImplementedError


class WorkflowRunner:
    def run(self, event: Event, pipeline: Pipeline) -> None:
        """Coordinate the steps until completion or failure."""
        raise NotImplementedError


class PipelineSelector:
    def execute(self, event: Event) -> Pipeline:
        """Find a pipeline, run its workflow, and return the pipeline."""
        raise NotImplementedError
