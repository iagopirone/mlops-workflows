"""Represent an image reference and its content as separate objects."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from pydantic import ConfigDict, field_validator

from mlops_workflows.artifacts.content import ArtifactContent
from mlops_workflows.artifacts.interface import ArtifactReference


class ImageReference(ArtifactReference):
    """Identify an image by its name and location."""

    def materialize(self) -> ImageContent:
        """Load the image and return its BGR pixel data."""
        path = Path(self.location)

        if not path.is_file():
            raise FileNotFoundError(f"Image file not found: {path}")

        image = cv2.imread(str(path))

        if image is None:
            raise ValueError(f"Could not read the image: {path}")

        return ImageContent(data=image)


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
        """Save the pixels to the destination and return its location."""
        if self.data.size == 0:
            raise ValueError("Image data must not be empty.")

        path = Path(reference.location)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not cv2.imwrite(str(path), self.data):
            raise OSError(f"Could not save the image: {path}")

        return reference.location
