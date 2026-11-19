"""Run object detection and save JSON and annotated image outputs."""

import argparse
from pathlib import Path

import cv2

from mlops_workflows.artifacts.detection.detection_reference import (
    DetectionReference,
)
from mlops_workflows.artifacts.image.image_content import ImageContent
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.components.object_detection.detectors.yolo_detector import (
    YoloDetector,
    YoloDetectorConfig,
)
from mlops_workflows.components.object_detection.object_detection_component import (
    ObjectDetectionComponent,
)


def main() -> None:
    """Run the object detection demonstration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_reference = ImageReference(
        name="input_image",
        location=args.image,
    )

    detection_reference = DetectionReference(
        name="detections",
        location=str(output_dir / "detections.json"),
    )

    detector = YoloDetector(YoloDetectorConfig(model_path=args.model))

    component = ObjectDetectionComponent(
        detector=detector,
        output_reference=detection_reference,
    )

    image = component.prepare([image_reference])
    component.execute(image)

    detections = detection_reference.materialize().data
    annotated = image.copy()

    colors = [
        (0, 0, 255),
        (0, 180, 0),
        (255, 0, 0),
        (0, 200, 200),
        (200, 0, 200),
    ]

    height, width = annotated.shape[:2]

    for detection in detections:
        x_min, y_min, x_max, y_max = [round(value) for value in detection.box]

        x_min = min(max(x_min, 0), width - 1)
        y_min = min(max(y_min, 0), height - 1)
        x_max = min(max(x_max, 0), width - 1)
        y_max = min(max(y_max, 0), height - 1)

        class_index = detector.class_names.index(detection.cls)
        color = colors[class_index % len(colors)]
        label = f"{detection.cls}: {detection.conf:.0%}"

        cv2.rectangle(
            annotated,
            (x_min, y_min),
            (x_max, y_max),
            color,
            2,
        )

        cv2.putText(
            annotated,
            label,
            (x_min, max(y_min - 8, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )

    annotated_reference = ImageReference(
        name="annotated_image",
        location=str(output_dir / "annotated.png"),
    )

    ImageContent(data=annotated).dematerialize(annotated_reference)

    print(f"Detections: {len(detections)}")
    print(f"JSON: {detection_reference.location}")
    print(f"Annotated image: {annotated_reference.location}")


if __name__ == "__main__":
    main()
