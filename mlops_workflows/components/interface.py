"""Define the contract for processing components."""

from abc import ABC, abstractmethod

from mlops_workflows.artifacts.interface import ArtifactReference


class Component(ABC):
    """Define how a component prepares inputs and produces outputs."""

    @abstractmethod
    def prepare(
        self,
        input_artifacts: list[ArtifactReference],
    ) -> object:
        """Load and prepare the input data."""
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        prepared_data: object,
    ) -> list[ArtifactReference]:
        """Process data, save outputs, and return their references."""
        raise NotImplementedError
