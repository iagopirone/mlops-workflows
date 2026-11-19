"""Test ExecutionReportContent validation."""

import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.report.execution_report_content import (
    ExecutionReportContent,
)


def test_content_requires_a_report():
    with pytest.raises(ValidationError):
        ExecutionReportContent(data={"run_id": "x"})
