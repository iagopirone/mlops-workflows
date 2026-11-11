"""Identify and load saved object detection results."""

import json
from pathlib import Path

from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.detection.detection_content import (
    DetectionContent,
)
from mlops_workflows.artifacts.interface import ArtifactReference


class DetectionReference(ArtifactReference):
    """Identify detection results by name and location."""

    def materialize(self) -> DetectionContent:
        """Load detection results from a JSON file."""
        path = Path(self.location)

        if not path.is_file():
            raise FileNotFoundError(f"Detection file not found: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, list):
            raise TypeError("Expected a list of detections.")

        detections = [Detection.model_validate(item) for item in data]

        return DetectionContent(data=detections)
