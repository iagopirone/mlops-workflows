"""Integrate visual question answering with the artifact workflow."""

from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.artifacts.text.text_content import TextContent
from mlops_workflows.artifacts.text.text_reference import TextReference
from mlops_workflows.components.interface import Component
from mlops_workflows.components.visual_question_answering.visual_question_answerer import (
    VisualQuestionAnswerer,
)


class VisualQuestionAnsweringComponent(Component):
    """Answer a text prompt about an image and save the answer as text."""

    def __init__(
        self,
        answerer: VisualQuestionAnswerer,
        output_reference: TextReference,
    ):
        self.answerer = answerer
        self.output_reference = output_reference

    def prepare(
        self,
        input_artifacts: list[ArtifactReference],
    ) -> tuple[ImageContent, TextContent]:
        """Load the image and prompt artifacts."""
        if (
            len(input_artifacts) != 2
            or not isinstance(input_artifacts[0], ImageReference)
            or not isinstance(input_artifacts[1], TextReference)
        ):
            raise ValueError("Expected an ImageReference and a TextReference.")

        image_content = input_artifacts[0].materialize()
        prompt_content = input_artifacts[1].materialize()

        return image_content, prompt_content

    def execute(
        self,
        prepared_data: object,
    ) -> list[ArtifactReference]:
        """Answer the prompt and save the answer as a text artifact."""
        if not isinstance(prepared_data, tuple) or len(prepared_data) != 2:
            raise TypeError("Expected an ImageContent and a TextContent.")

        image_content, prompt_content = prepared_data

        if not isinstance(image_content, ImageContent) or not isinstance(
            prompt_content, TextContent
        ):
            raise TypeError("Expected an ImageContent and a TextContent.")

        if not prompt_content.data.strip():
            raise ValueError("The prompt must not be blank.")

        # Pass a copy so the answerer cannot modify the loaded image.
        answer = self.answerer.answer(
            image_content.data.copy(),
            prompt_content.data,
        )

        if not isinstance(answer, str):
            raise TypeError("The answerer must return a string.")

        TextContent(data=answer).dematerialize(self.output_reference)

        return [self.output_reference]
