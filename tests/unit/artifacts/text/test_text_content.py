"""Test TextContent validation and persistence."""

import pytest
from pydantic import ValidationError

from mlops_workflows.artifacts.text.text_content import TextContent
from mlops_workflows.artifacts.text.text_reference import TextReference


def test_dematerialize_creates_parent_directory(tmp_path):
    """Create parent directories when saving text."""
    reference = TextReference(
        name="response",
        location=str(tmp_path / "nested" / "response.txt"),
    )

    TextContent(data="Model response").dematerialize(reference)

    assert reference.materialize().data == "Model response"


def test_text_content_rejects_non_string():
    """Require text content to contain a string."""
    with pytest.raises(ValidationError):
        TextContent(data=123)
