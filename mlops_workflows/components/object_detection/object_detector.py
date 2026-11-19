"""Define the interface for object detection algorithms."""

from abc import ABC, abstractmethod

import numpy as np

from mlops_workflows.artifacts.detection.detection import Detection


class ObjectDetector(ABC):
    """Define a common interface for object detection algorithms."""

    @abstractmethod
    def detect(self, image: np.ndarray) -> list[Detection]:
        """Detect objects in a BGR image."""
        raise NotImplementedError
