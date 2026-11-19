"""Identify and load text artifacts."""

from pathlib import Path

from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.artifacts.text.text_content import TextContent


class TextReference(ArtifactReference):
    """Identify a text artifact by name and location."""

    def materialize(self) -> TextContent:
        """Load text from a UTF-8 file."""
        path = Path(self.location)

        if not path.is_file():
            raise FileNotFoundError(f"Text file not found: {path}")

        return TextContent(data=path.read_text(encoding="utf-8"))
