"""Test TextReference loading and round trips."""

import pytest

from mlops_workflows.artifacts.text.text_content import TextContent
from mlops_workflows.artifacts.text.text_reference import TextReference


def test_text_round_trip(tmp_path):
    """Preserve text when saving and loading an artifact."""
    reference = TextReference(
        name="prompt",
        location=str(tmp_path / "prompt.txt"),
    )

    content = TextContent(data="Detect objects.\nOlá, mundo!")

    location = content.dematerialize(reference)
    restored = reference.materialize()

    assert location == reference.location
    assert restored.data == content.data


def test_empty_text_round_trip(tmp_path):
    """Allow empty text artifacts."""
    reference = TextReference(
        name="empty",
        location=str(tmp_path / "empty.txt"),
    )

    TextContent(data="").dematerialize(reference)

    assert reference.materialize().data == ""


def test_materialize_rejects_missing_file(tmp_path):
    """Reject nonexistent text files."""
    reference = TextReference(
        name="missing",
        location=str(tmp_path / "missing.txt"),
    )

    with pytest.raises(FileNotFoundError):
        reference.materialize()


def test_materialize_rejects_directory(tmp_path):
    """Reject directories as text files."""
    reference = TextReference(
        name="directory",
        location=str(tmp_path),
    )

    with pytest.raises(FileNotFoundError):
        reference.materialize()


def test_materialize_rejects_invalid_encoding(tmp_path):
    """Reject text files with invalid UTF-8 encoding."""
    path = tmp_path / "invalid.txt"
    path.write_bytes(b"\xff")

    reference = TextReference(
        name="invalid",
        location=str(path),
    )

    with pytest.raises(UnicodeDecodeError):
        reference.materialize()
