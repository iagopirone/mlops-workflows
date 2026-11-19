"""Store and save end-to-end execution reports."""

from pathlib import Path

from mlops_workflows.artifacts.content import ArtifactContent
from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.artifacts.report.execution_report import ExecutionReport


class ExecutionReportContent(ArtifactContent):
    """Represent an execution report."""

    data: ExecutionReport

    def dematerialize(self, reference: ArtifactReference) -> str:
        """Save the report as UTF-8 JSON and return its location."""
        path = Path(reference.location)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.data.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return reference.location
