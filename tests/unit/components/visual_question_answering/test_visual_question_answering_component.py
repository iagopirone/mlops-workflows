"""Test the visual question answering component."""

from pathlib import Path

import numpy as np
import pytest

from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
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
    """Return a predefined answer and record the received inputs."""

    def __init__(self, response: object = "There is one white blood cell."):
        self.response = response
        self.received_image = None
        self.received_question = None

    def answer(self, image: np.ndarray, question: str) -> str:
        """Record the inputs and return the predefined answer."""
        self.received_image = image
        self.received_question = question
        return self.response


class MutatingAnswerer(VisualQuestionAnswerer):
    """Modify the received image to simulate a careless implementation."""

    def answer(self, image: np.ndarray, question: str) -> str:
        """Overwrite the image pixels and return an answer."""
        image[:] = 255
        return "Modified."


class FailingAnswerer(VisualQuestionAnswerer):
    """Simulate an inference failure."""

    def answer(self, image: np.ndarray, question: str) -> str:
        """Raise an inference error."""
        raise RuntimeError("Inference failed.")


@pytest.fixture
def image() -> np.ndarray:
    """Provide a small BGR image with a known pattern."""
    pixels = np.zeros((32, 48, 3), dtype=np.uint8)
    pixels[4:12, 8:20] = (0, 0, 255)
    return pixels


@pytest.fixture
def artifacts(tmp_path, image):
    """Create image and prompt artifacts for testing."""
    image_reference = ImageReference(
        name="original",
        location=str(tmp_path / "original.png"),
    )
    ImageContent(data=image).dematerialize(image_reference)

    prompt_reference = TextReference(
        name="prompt",
        location=str(tmp_path / "prompt.txt"),
    )
    TextContent(data="How many white blood cells?").dematerialize(prompt_reference)

    return image_reference, prompt_reference


@pytest.fixture
def output_reference(tmp_path) -> TextReference:
    """Provide the destination of the answer."""
    return TextReference(
        name="answer",
        location=str(tmp_path / "answer.txt"),
    )


def test_prepare_loads_artifact_contents(artifacts, output_reference, image):
    """Return the image and prompt contents instead of raw data."""
    component = VisualQuestionAnsweringComponent(FakeAnswerer(), output_reference)

    image_content, prompt_content = component.prepare(list(artifacts))

    assert isinstance(image_content, ImageContent)
    assert isinstance(prompt_content, TextContent)
    np.testing.assert_array_equal(image_content.data, image)
    assert prompt_content.data == "How many white blood cells?"


def test_prepare_rejects_invalid_artifacts(tmp_path, artifacts, output_reference):
    """Require exactly an ImageReference and a TextReference in order."""
    component = VisualQuestionAnsweringComponent(FakeAnswerer(), output_reference)
    image_reference, prompt_reference = artifacts
    detection_reference = DetectionReference(
        name="detections",
        location=str(tmp_path / "detections.json"),
    )

    invalid_inputs = [
        [],
        [image_reference],
        [prompt_reference, image_reference],
        [image_reference, detection_reference],
        [image_reference, prompt_reference, prompt_reference],
    ]

    for input_artifacts in invalid_inputs:
        with pytest.raises(ValueError, match="ImageReference and a TextReference"):
            component.prepare(input_artifacts)


def test_execute_passes_inputs_and_saves_answer(artifacts, output_reference, image):
    """Send the image and prompt to the answerer and persist its answer."""
    answerer = FakeAnswerer("There is one white blood cell.\nOlá!")
    component = VisualQuestionAnsweringComponent(answerer, output_reference)

    prepared_data = component.prepare(list(artifacts))
    result = component.execute(prepared_data)

    assert result == [output_reference]
    np.testing.assert_array_equal(answerer.received_image, image)
    assert answerer.received_question == "How many white blood cells?"

    restored = output_reference.materialize()

    assert isinstance(restored, TextContent)
    assert restored.data == "There is one white blood cell.\nOlá!"


def test_execute_preserves_the_original_image(artifacts, output_reference, image):
    """Keep the loaded content and the source file unchanged."""
    component = VisualQuestionAnsweringComponent(MutatingAnswerer(), output_reference)

    image_content, prompt_content = component.prepare(list(artifacts))
    component.execute((image_content, prompt_content))

    np.testing.assert_array_equal(image_content.data, image)
    np.testing.assert_array_equal(artifacts[0].materialize().data, image)


def test_execute_rejects_invalid_prepared_data(output_reference, image):
    """Reject data that is not an ImageContent and a TextContent."""
    component = VisualQuestionAnsweringComponent(FakeAnswerer(), output_reference)
    image_content = ImageContent(data=image)
    prompt_content = TextContent(data="Describe the image.")

    invalid_inputs = [
        None,
        (image_content,),
        (prompt_content, image_content),
        (image, prompt_content),
        (image_content, "Describe the image."),
    ]

    for prepared_data in invalid_inputs:
        with pytest.raises(TypeError):
            component.execute(prepared_data)

    assert not Path(output_reference.location).exists()


def test_execute_rejects_blank_prompt(output_reference, image):
    """Do not call the answerer with an empty or blank prompt."""
    answerer = FakeAnswerer()
    component = VisualQuestionAnsweringComponent(answerer, output_reference)

    for prompt in ["", "  \n\t"]:
        with pytest.raises(ValueError, match="blank"):
            component.execute((ImageContent(data=image), TextContent(data=prompt)))

    assert answerer.received_question is None
    assert not Path(output_reference.location).exists()


def test_execute_rejects_non_text_answer(output_reference, image):
    """Do not persist an answer that is not a string."""
    component = VisualQuestionAnsweringComponent(
        FakeAnswerer(response=["not", "text"]),
        output_reference,
    )

    with pytest.raises(TypeError, match="must return a string"):
        component.execute((ImageContent(data=image), TextContent(data="Describe.")))

    assert not Path(output_reference.location).exists()


def test_execute_does_not_save_output_when_answerer_fails(output_reference, image):
    """Propagate inference errors without creating an output artifact."""
    component = VisualQuestionAnsweringComponent(FailingAnswerer(), output_reference)

    with pytest.raises(RuntimeError, match="Inference failed"):
        component.execute((ImageContent(data=image), TextContent(data="Describe.")))

    assert not Path(output_reference.location).exists()
