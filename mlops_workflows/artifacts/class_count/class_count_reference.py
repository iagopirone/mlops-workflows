"""Identify and load saved class counts."""

from pathlib import Path

from mlops_workflows.artifacts.class_count.class_count import ClassCount
from mlops_workflows.artifacts.class_count.class_count_content import (
    ClassCountContent,
)
from mlops_workflows.artifacts.interface import ArtifactReference


class ClassCountReference(ArtifactReference):
    """Identify class counts by name and location."""

    def materialize(self) -> ClassCountContent:
        """Load and validate class counts from a JSON file."""
        path = Path(self.location)
        if not path.is_file():
            raise FileNotFoundError(f"Class count file not found: {path}")
        class_count = ClassCount.model_validate_json(path.read_text(encoding="utf-8"))
        return ClassCountContent(data=class_count)
