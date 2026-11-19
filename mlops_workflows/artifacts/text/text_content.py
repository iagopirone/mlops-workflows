"""Store and save text artifacts."""

from pathlib import Path

from mlops_workflows.artifacts.content import ArtifactContent
from mlops_workflows.artifacts.interface import ArtifactReference


class TextContent(ArtifactContent):
    """Represent the content of a text artifact."""

    data: str

    def dematerialize(self, reference: ArtifactReference) -> str:
        """Save text as UTF-8 and return its location."""
        path = Path(reference.location)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.data, encoding="utf-8")

        return reference.location
