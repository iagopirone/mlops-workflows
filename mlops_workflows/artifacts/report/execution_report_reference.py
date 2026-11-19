"""Identify and load saved execution reports."""

from pathlib import Path

from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.artifacts.report.execution_report import ExecutionReport
from mlops_workflows.artifacts.report.execution_report_content import (
    ExecutionReportContent,
)


class ExecutionReportReference(ArtifactReference):
    """Identify an execution report by name and location."""

    def materialize(self) -> ExecutionReportContent:
        """Load and validate a report from a JSON file."""
        path = Path(self.location)
        if not path.is_file():
            raise FileNotFoundError(f"Report file not found: {path}")
        report = ExecutionReport.model_validate_json(path.read_text(encoding="utf-8"))
        return ExecutionReportContent(data=report)
