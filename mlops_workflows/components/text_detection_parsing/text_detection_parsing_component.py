"""Turn a model's text response into a detection artifact."""

from mlops_workflows.artifacts.detection.detection_content import DetectionContent
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.artifacts.text.text_content import TextContent
from mlops_workflows.artifacts.text.text_reference import TextReference
from mlops_workflows.components.interface import Component
from mlops_workflows.components.text_detection_parsing.text_detection_parser import (
    TextDetectionParser,
)


class TextDetectionParsingComponent(Component):
    """Parse detections from a text response and save them as JSON."""

    def __init__(
        self,
        parser: TextDetectionParser,
        output_reference: DetectionReference,
    ):
        self.parser = parser
        self.output_reference = output_reference

    def prepare(
        self,
        input_artifacts: list[ArtifactReference],
    ) -> tuple[ImageContent, TextContent]:
        """Load the source image and the text response."""
        if (
            len(input_artifacts) != 2
            or not isinstance(input_artifacts[0], ImageReference)
            or not isinstance(input_artifacts[1], TextReference)
        ):
            raise ValueError("Expected an ImageReference and a TextReference.")

        image_content = input_artifacts[0].materialize()
        response_content = input_artifacts[1].materialize()

        return image_content, response_content

    def execute(
        self,
        prepared_data: object,
    ) -> list[ArtifactReference]:
        """Parse the response and save the detections."""
        if not isinstance(prepared_data, tuple) or len(prepared_data) != 2:
            raise TypeError("Expected an ImageContent and a TextContent.")

        image_content, response_content = prepared_data

        if not isinstance(image_content, ImageContent) or not isinstance(
            response_content, TextContent
        ):
            raise TypeError("Expected an ImageContent and a TextContent.")

        height, width = image_content.data.shape[:2]

        # Parse everything before saving so no partial artifact is written.
        detections = self.parser.parse(response_content.data, width, height)

        DetectionContent(data=detections).dematerialize(self.output_reference)

        return [self.output_reference]
