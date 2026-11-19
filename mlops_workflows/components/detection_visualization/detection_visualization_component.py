"""Component for visualizing object detections."""

import cv2

from mlops_workflows.artifacts.detection.detection_content import DetectionContent
from mlops_workflows.artifacts.detection.detection_reference import DetectionReference
from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.artifacts.interface import ArtifactReference
from mlops_workflows.components.interface import Component


class DetectionVisualizationComponent(Component):
    """Draw object detections on an image."""

    def __init__(self, output_reference: ImageReference):
        self.output_reference = output_reference

    def prepare(
        self,
        input_artifacts: list[ArtifactReference],
    ) -> tuple[ImageContent, DetectionContent]:
        """Load the image and detection artifacts."""
        if (
            len(input_artifacts) != 2
            or not isinstance(input_artifacts[0], ImageReference)
            or not isinstance(input_artifacts[1], DetectionReference)
        ):
            raise ValueError("Expected an ImageReference and a DetectionReference.")

        image_content = input_artifacts[0].materialize()
        detection_content = input_artifacts[1].materialize()

        return image_content, detection_content

    def execute(
        self,
        prepared_data: object,
    ) -> list[ArtifactReference]:
        """Draw bounding boxes and save the annotated image."""
        if not isinstance(prepared_data, tuple) or len(prepared_data) != 2:
            raise TypeError("Expected an ImageContent and a DetectionContent.")

        image_content, detection_content = prepared_data

        if not isinstance(image_content, ImageContent) or not isinstance(
            detection_content, DetectionContent
        ):
            raise TypeError("Expected an ImageContent and a DetectionContent.")

        annotated_image = image_content.data.copy()

        for detection in detection_content.data:
            x1, y1, x2, y2 = map(int, detection.box)

            cv2.rectangle(
                annotated_image,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2,
            )

            if detection.conf is None:
                label = detection.cls
            else:
                label = f"{detection.cls} {detection.conf:.2f}"

            cv2.putText(
                annotated_image,
                label,
                (x1, max(20, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )

        content = ImageContent(data=annotated_image)
        content.dematerialize(self.output_reference)

        return [self.output_reference]
