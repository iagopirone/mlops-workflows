"""Store and save class counts."""

from pathlib import Path

from mlops_workflows.artifacts.class_count.class_count import ClassCount
from mlops_workflows.artifacts.content import ArtifactContent
from mlops_workflows.artifacts.interface import ArtifactReference


class ClassCountContent(ArtifactContent):
    """Represent the class counts of a set of detections."""

    data: ClassCount

    def dematerialize(self, reference: ArtifactReference) -> str:
        """Save the counts as UTF-8 JSON and return their location."""
        path = Path(reference.location)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.data.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return reference.location
