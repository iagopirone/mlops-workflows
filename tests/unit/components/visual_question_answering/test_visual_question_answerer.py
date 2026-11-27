"""Test the visual question answerer interface."""

import pytest

from mlops_workflows.components.visual_question_answering.visual_question_answerer import (
    VisualQuestionAnswerer,
)


def test_visual_question_answerer_cannot_be_instantiated():
    """Ensure the abstract answerer cannot be instantiated."""
    with pytest.raises(TypeError):
        VisualQuestionAnswerer()
