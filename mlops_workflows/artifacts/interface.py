"""Define the contract for artifact references."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from mlops_workflows.artifacts.content import ArtifactContent


class ArtifactReference(BaseModel, ABC):
    """Identify an artifact and define how its content is loaded."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        validate_assignment=True,
    )

    name: str = Field(min_length=1)
    location: str = Field(min_length=1)

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str) -> str:
        """Reject blank locations."""
        if not value.strip():
            raise ValueError("The location must not be blank.")

        return value

    @abstractmethod
    def materialize(self) -> ArtifactContent:
        """Load and return the referenced content."""
        raise NotImplementedError
