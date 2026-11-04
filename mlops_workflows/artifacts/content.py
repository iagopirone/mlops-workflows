"""Define the contract for artifact contents."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict

from mlops_workflows.artifacts.interface import ArtifactReference


class ArtifactContent(BaseModel, ABC):
    """Hold content and define how it is saved."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        validate_assignment=True,
    )

    data: object

    @abstractmethod
    def dematerialize(self, reference: ArtifactReference) -> str:
        """Save the content and return its destination location."""
        raise NotImplementedError
