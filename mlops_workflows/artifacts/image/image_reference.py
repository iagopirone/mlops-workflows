"""Identify and load local images."""

from pathlib import Path

import cv2

from mlops_workflows.artifacts.image.image_content import ImageContent
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
