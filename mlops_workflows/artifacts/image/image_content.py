"""Store and save image pixel data."""

from pathlib import Path

import cv2
import numpy as np
from pydantic import ConfigDict, field_validator

from mlops_workflows.artifacts.content import ArtifactContent
from mlops_workflows.artifacts.interface import ArtifactReference


class ImageContent(ArtifactContent):
    """Store the pixels of a loaded or generated image."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: np.ndarray

    @field_validator("data")
    @classmethod
    def validate_data(cls, value: np.ndarray) -> np.ndarray:
        """Reject empty image arrays."""
        if value.size == 0:
            raise ValueError("Image data must not be empty.")

        return value

    def dematerialize(self, reference: ArtifactReference) -> str:
        """Save the pixels and return the destination location."""
        if self.data.size == 0:
            raise ValueError("Image data must not be empty.")

        path = Path(reference.location)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not cv2.imwrite(str(path), self.data):
            raise OSError(f"Could not save the image: {path}")

        return reference.location
