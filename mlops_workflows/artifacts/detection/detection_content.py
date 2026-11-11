"""Store and save object detection results."""

import json
from pathlib import Path

from mlops_workflows.artifacts.content import ArtifactContent
from mlops_workflows.artifacts.detection.detection import Detection
from mlops_workflows.artifacts.interface import ArtifactReference


class DetectionContent(ArtifactContent):
    """Store a list of detected objects."""

    data: list[Detection]

    def dematerialize(self, reference: ArtifactReference) -> str:
        """Save detections as JSON and return their location."""
        path = Path(reference.location)
        path.parent.mkdir(parents=True, exist_ok=True)

        detections = [detection.model_dump() for detection in self.data]

        path.write_text(
            json.dumps(detections, indent=2),
            encoding="utf-8",
        )

        return reference.location
