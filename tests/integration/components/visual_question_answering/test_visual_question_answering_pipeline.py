"""Integration test for visual question answering with real artifacts."""

import numpy as np

from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.text.text_content import TextContent
from mlops_workflows.artifacts.text.text_reference import TextReference
from mlops_workflows.components.visual_question_answering.visual_question_answerer import (
    VisualQuestionAnswerer,
)
from mlops_workflows.components.visual_question_answering.visual_question_answering_component import (
    VisualQuestionAnsweringComponent,
)


class FakeAnswerer(VisualQuestionAnswerer):
    """Answer from the image size without running a model."""

    def answer(self, image: np.ndarray, question: str) -> str:
        """Build a deterministic answer from the received inputs."""
        height, width = image.shape[:2]
        return f"Question: {question}\nImage size: {width}x{height}"


def test_image_and_prompt_to_text_answer(tmp_path):
    """Pass image and prompt artifacts through the component to a text artifact."""
    image_reference = ImageReference(
        name="original",
        location=str(tmp_path / "inputs" / "original.png"),
    )
    prompt_reference = TextReference(
        name="prompt",
        location=str(tmp_path / "inputs" / "prompt.txt"),
    )
    answer_reference = TextReference(
        name="answer",
        location=str(tmp_path / "outputs" / "answer.txt"),
    )

    image = np.zeros((40, 60, 3), dtype=np.uint8)
    image[10:20, 10:30] = (255, 0, 0)
    ImageContent(data=image).dematerialize(image_reference)
    TextContent(data="What is shown?").dematerialize(prompt_reference)

    component = VisualQuestionAnsweringComponent(
        answerer=FakeAnswerer(),
        output_reference=answer_reference,
    )

    prepared_data = component.prepare([image_reference, prompt_reference])
    outputs = component.execute(prepared_data)

    assert outputs == [answer_reference]
    assert answer_reference.materialize().data == (
        "Question: What is shown?\nImage size: 60x40"
    )
    np.testing.assert_array_equal(image_reference.materialize().data, image)
    assert prompt_reference.materialize().data == "What is shown?"
