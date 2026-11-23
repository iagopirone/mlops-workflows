"""Count detections by class from any detector's output.

Two input modes, both ending in a DetectionReference:

- ``--detections <json>``: an existing detections file written by any source
  (YOLO, the text detection parser, Florence-2 or Qwen3-VL adapters);
- ``--model <onnx> --image <image>``: run ObjectDetectionComponent with the
  YOLO ONNX detector first, then count its saved detections.

``--classes`` omitted counts every class; ``--classes`` with names counts only
those; ``--classes`` with no names counts nothing.
"""

import argparse
from pathlib import Path

from mlops_workflows.artifacts.class_count.class_count_reference import (
    ClassCountReference,
)
from mlops_workflows.artifacts.detection.detection_reference import (
    DetectionReference,
)
from mlops_workflows.artifacts.image.image_reference import ImageReference
from mlops_workflows.components.class_counting.class_counting_component import (
    ClassCountingComponent,
)


def detect_with_yolo(
    model_path: str,
    image_path: str,
    output_dir: Path,
) -> DetectionReference:
    """Run YOLO detection and return the saved detections reference."""
    # Imported here so counting an existing file does not need ONNX Runtime.
    from mlops_workflows.components.object_detection.detectors.yolo_detector import (
        YoloDetector,
        YoloDetectorConfig,
    )
    from mlops_workflows.components.object_detection.object_detection_component import (
        ObjectDetectionComponent,
    )

    detection_reference = DetectionReference(
        name="detections",
        location=str(output_dir / "detections.json"),
    )
    component = ObjectDetectionComponent(
        detector=YoloDetector(YoloDetectorConfig(model_path=model_path)),
        output_reference=detection_reference,
    )
    outputs = component.execute(
        component.prepare([ImageReference(name="input_image", location=image_path)])
    )

    return outputs[0]


def main() -> None:
    """Run the class counting demonstration."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--detections")
    source.add_argument("--model")
    parser.add_argument("--image")
    parser.add_argument("--classes", nargs="*")
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()

    if args.model and not args.image:
        parser.error("--model requires --image.")

    output_dir = Path(args.output_dir)

    if args.detections:
        detection_reference = DetectionReference(
            name="detections",
            location=args.detections,
        )
    else:
        detection_reference = detect_with_yolo(args.model, args.image, output_dir)

    count_reference = ClassCountReference(
        name="class_counts",
        location=str(output_dir / "class_counts.json"),
    )
    component = ClassCountingComponent(
        classes=args.classes,
        output_reference=count_reference,
    )
    component.execute(component.prepare([detection_reference]))

    print(Path(count_reference.location).read_text(encoding="utf-8"), end="")


if __name__ == "__main__":
    main()
